"""지역 위험 집계 (TH-04). **O-01 확정 규칙이며 단일 구현이다.**

    지역 위험 = 경로 범위 안 센서 중 t+30 고수위 확률이 TH-03(0.33) 이상인 **비율**
    그 비율이 AREA_THRESHOLD(0.5) 이상이면 ai_risk_level = HIGH

왜 이 규칙인가
--------------
이전 규칙("센서 t+30 확률 상위 25% 평균")은 **회복 국면을 따라가지 못했다.**
피크 0.9995 -> 회복 0.9637 로 낙폭이 0.036 뿐이었다. 같은 시점에 임계를 넘는
센서 비율은 0.968 -> 0.548 로 내려간다. 근거 수치는 docs/DECISIONS.md 3.2.1.

중앙값이 회복에 더 민감했지만(낙폭 0.494) 지역 임계를 새로 튜닝해야 하고
11시간 안에 근거를 만들 수 없었다. 비율 규칙은 **TH-03 을 그대로 재사용**하므로
새로 정할 값이 "지역 비율 임계" 하나로 줄어든다.

알려진 한계 — 숨기지 않는다
---------------------------
경로 범위(강남역 1km) 안에서 재생 시점에 실제로 존재하는 센서는 **5개뿐**이다
(docs/DECISIONS.md 3.0.2). 따라서 비율이 가질 수 있는 값은
0 / 0.2 / 0.4 / 0.6 / 0.8 / 1.0 의 **6단계**이고, AREA_THRESHOLD=0.5 는
실질적으로 "5개 중 3개 이상"을 뜻한다. 이 경계는 검증값이 아니라 **팀 합의값**이다.

여기 있는 값을 바꾸면 RF 픽스처를 전부 다시 만들어야 한다.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

#: TH-03. 센서 단위 고수위 임계. val 사건에서 오경보 예산 0.05 로 튜닝한 값이며
#: 이 모듈이 정한 것이 아니다. 근거 표기는 model.threshold_basis 가 들고 있다.
SENSOR_THRESHOLD = 0.33

#: TH-04. 지역 비율 임계. **팀 합의값(TEAM_AGREED)이며 검증된 값이 아니다.**
#: 이 경계가 실제로 가르는 것은 S2 상승(0.4 -> LOW)과 S4 회복(0.6 -> HIGH) 뿐이다.
#: 회복 국면을 성급히 안전하다고 말하지 않는 쪽을 골랐다.
AREA_THRESHOLD = 0.5

#: 집계에 쓰는 예측 지평(분). ActionDecision 이 보는 primary_horizon 과 같다.
HORIZON_MIN = 30

_DESTINATIONS = Path(__file__).resolve().parents[2] / "contracts" / "destinations.json"


def load_scope() -> dict:
    """경로 범위를 `contracts/destinations.json` 에서 읽는다.

    범위의 정본은 C(경로 담당)가 소유하는 그 파일 하나다. 여기에 좌표를 복사해
    두면 C 가 범위를 바꿨을 때 예측 쪽이 조용히 어긋난다.
    """
    scope = json.loads(_DESTINATIONS.read_text(encoding="utf-8"))["scope"]
    return {
        "label": scope["center_label"],
        "lat": float(scope["center_lat"]),
        "lon": float(scope["center_lon"]),
        "radius_m": float(scope["radius_m"]),
    }


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def in_scope(sensor: dict, scope: dict) -> bool:
    """좌표가 없는 센서는 범위 안이라고 말할 수 없으므로 False 다.

    `23-0007` 이 이 경우다(`quality: UNMATCHED`). 분모에서 빼고 그 사실을 센다 —
    조용히 포함시키면 위치를 모르는 센서가 지역 등급을 흔든다.
    """
    loc = sensor.get("location") or {}
    lat, lon = loc.get("lat"), loc.get("lon")
    if lat is None or lon is None:
        return False
    return haversine_m(scope["lat"], scope["lon"], float(lat), float(lon)) <= scope["radius_m"]


def compute(sensors: list[dict], scope: dict | None = None) -> dict:
    """`RiskAssessment.area_risk` 블록을 만든다. 순수 함수다.

    Returns:
        `district` · `score`(DEPRECATED 별칭) · `risk_probability` ·
        `ai_risk_level` · `basis` 를 담은 dict.

        범위 안에 확률을 가진 센서가 하나도 없으면 `risk_probability` 와
        `ai_risk_level` 은 `None` 이다. **0.0 으로 채우지 않는다** — "위험이 없다"와
        "판단할 근거가 없다"는 다른 상태다.
    """
    scope = scope or load_scope()
    key = str(HORIZON_MIN)

    inside, no_coord = [], 0
    for sensor in sensors:
        prob = (sensor.get("horizons") or {}).get(key, {}).get("high_level_p")
        if prob is None:
            continue
        loc = sensor.get("location") or {}
        if loc.get("lat") is None or loc.get("lon") is None:
            no_coord += 1
            continue
        if in_scope(sensor, scope):
            inside.append(float(prob))

    label = f"{scope['label']} 반경 {int(scope['radius_m'])}m"

    if not inside:
        return {
            "district": label,
            "score": None,
            "risk_probability": None,
            "ai_risk_level": None,
            "basis": (
                f"경로 범위({label}) 안에 확률을 가진 센서가 없어 지역 위험을 산출하지 않았다. "
                f"좌표 미상 센서 {no_coord}개는 분모에서 제외한다."
            ),
        }

    over = sum(1 for p in inside if p >= SENSOR_THRESHOLD)
    ratio = round(over / len(inside), 4)

    return {
        "district": label,
        # DEPRECATED. risk_probability 의 예전 이름이라 같은 값을 싣는다.
        "score": ratio,
        "risk_probability": ratio,
        "ai_risk_level": "HIGH" if ratio >= AREA_THRESHOLD else "LOW",
        "basis": (
            f"경로 범위({label}) 센서 {len(inside)}개 중 "
            f"t+{HORIZON_MIN}분 고수위 확률>={SENSOR_THRESHOLD} 인 비율 {over}/{len(inside)}. "
            f"지역 임계 {AREA_THRESHOLD} 이상이면 HIGH "
            f"(지역 임계 TEAM_AGREED, 센서 임계 val_events@fpr_0.05). "
            f"좌표 미상 {no_coord}개 제외. TH-04/O-01"
        ),
    }
