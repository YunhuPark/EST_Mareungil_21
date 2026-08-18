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
from dataclasses import dataclass
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

#: 재생 한 스텝의 길이(분).
STEP_MINUTES = 10

#: O-08. `HIGH` -> `LOW` 로 내려갈 때만 요구하는 연속 확인 횟수. **비대칭이다.**
#: 올라갈 때는 0 이며 즉시 전환한다 — 위험 진입을 늦추지 않는다.
#:
#: 3 스텝 = 30분. 2022-08-08~09 구간(288스텝)을 정답 라벨로 돌려 고른 값이다.
#: 억제 없이는 등급이 13번 뒤집히고 그중 3번이 30분 안에 되돌아갔다(하나는 10분).
#: 이 규칙을 넣으면 전환 7번, 30분 이내 되돌아감 0번이 된다.
#: **검증값이 아니라 팀 합의값이다**(TEAM_AGREED). 근거는 docs/DECISIONS.md 3.3.
EXIT_DWELL_STEPS = 3

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


def annotate(sensors: list[dict], scope: dict | None = None) -> list[dict]:
    """각 센서에 범위·임계 판정을 찍어 **새 목록**을 낸다. 순수 함수다.

    `compute()` 가 비율을 낼 때 이미 내리는 판정을 그대로 꺼내 놓을 뿐이며,
    여기서 무엇도 새로 정하지 않는다 — `in_scope()` 와 `SENSOR_THRESHOLD` 를
    그대로 쓴다. 화면이 임계를 다시 적용하지 않게 하려는 것이다(CLAUDE.md 10절).
    지도에 찍히는 점의 개수와 `area_risk.basis` 의 "n/m" 은 **같은 판정**에서
    나와야 하고, 그것이 이 함수가 존재하는 유일한 이유다.

    두 필드의 뜻:

    - `in_area_scope`: 경로 범위 안인가. **좌표가 없으면 False 다** —
      `in_scope()` 와 같은 규칙이며, 위치를 모르는 센서는 지도에 찍을 자리가
      없다(`23-0007` 이 이 경우다).
    - `exceeds_sensor_threshold`: t+`HORIZON_MIN` 고수위 확률이 TH-03 이상인가.
      확률이 없으면 `None` 이다. **False 로 채우지 않는다** — "임계 미만"과
      "판단할 값이 없다"는 다른 상태이고, `compute()` 도 후자를 분모에서 뺀다.

    그래서 다음이 성립한다. `tests/test_area_risk.py` 가 이걸 지킨다:

        분모 = in_area_scope 이고 exceeds_sensor_threshold 가 None 이 아닌 센서 수
        분자 = in_area_scope 이고 exceeds_sensor_threshold 가 True 인 센서 수

    두 조건을 **함께** 봐야 하는 이유는 범위 안에 있으면서 확률이 없는 센서가
    가능하기 때문이다. 그런 센서를 `in_area_scope` 만 보고 "안전"으로 그리면
    없는 판단을 지어내게 된다 — 화면은 그것을 판단 불가로 구분해 표시한다.

    입력 dict 를 건드리지 않고 사본을 낸다. 같은 입력이면 같은 출력이다(N-04).
    """
    scope = scope or load_scope()
    key = str(HORIZON_MIN)

    marked: list[dict] = []
    for sensor in sensors:
        prob = (sensor.get("horizons") or {}).get(key, {}).get("high_level_p")
        copy = dict(sensor)
        copy["in_area_scope"] = in_scope(sensor, scope)
        copy["exceeds_sensor_threshold"] = (
            None if prob is None else float(prob) >= SENSOR_THRESHOLD
        )
        marked.append(copy)
    return marked


@dataclass(frozen=True)
class DwellState:
    """진동 억제의 상태. **이전 시각의 결과를 명시적으로 들고 다닌다.**

    히스테리시스는 이전 상태에 의존하므로 언뜻 N-04(재현성)와 충돌해 보이지만,
    이전 상태를 *입력으로 받으면* 같은 입력에 항상 같은 출력이라 순수 함수다.
    전역 변수나 파일에 상태를 두지 않는다.

    Attributes:
        level: 지금 화면이 보는 등급. `None` 은 판단 불가다.
        pending_exit: `HIGH` 에서 내려가려고 기다린 연속 스텝 수.
        last_known: 마지막으로 **판단이 된** 등급. `level` 과 따로 두는 이유는
            결측 구간 때문이다. 결측 동안 `level` 은 `None` 이지만 "직전에
            위험했다"는 사실은 남아 있어야, 데이터가 돌아왔을 때 해제 대기를
            처음부터 다시 세지 않고 이어서 센다. 이걸 합쳐 두면 결측 한 번에
            대기가 통째로 사라져 등급이 즉시 떨어진다.
    """

    level: str | None = None
    pending_exit: int = 0
    last_known: str | None = None


def step(raw_level: str | None, state: DwellState | None = None) -> DwellState:
    """한 스텝 진행한다. **순수 함수다.**

    비대칭 규칙:

    - `LOW` -> `HIGH` 는 **즉시**. 위험 진입을 늦추지 않는다.
    - `HIGH` -> `LOW` 는 `EXIT_DWELL_STEPS` 만큼 연속으로 `LOW` 여야 한다.
    - 판단 불가(`None`)는 **그대로 통과**시키고 대기 카운터를 건드리지 않는다.
      "모른다"를 "안전하다"로 바꾸지 않기 위해서다. 데이터가 끊긴 동안 해제
      카운트가 쌓여 복구되자마자 `LOW` 로 떨어지는 일도 막는다.

    Args:
        raw_level: 집계가 그대로 낸 등급 (`compute()` 의 `ai_risk_level`).
        state: 직전 스텝의 결과. 첫 스텝이면 `None`.

    Returns:
        이번 스텝의 `DwellState`. 화면에 쓸 값은 `.level` 이다.
    """
    state = state or DwellState()

    if raw_level is None:
        # 판단 불가. 화면에는 그대로 "모름"을 내보내되, 직전에 위험했다는 사실과
        # 해제 대기 횟수는 유지한다. 결측이 해제를 앞당기면 안 된다.
        return DwellState(
            level=None,
            pending_exit=state.pending_exit,
            last_known=state.last_known,
        )

    if raw_level == "HIGH":
        return DwellState(level="HIGH", pending_exit=0, last_known="HIGH")

    # raw_level == "LOW". 판단됐던 마지막 등급을 기준으로 본다 - state.level 을
    # 보면 결측 직후에 대기가 초기화돼 즉시 LOW 로 떨어진다.
    if state.last_known != "HIGH":
        return DwellState(level="LOW", pending_exit=0, last_known="LOW")

    pending = state.pending_exit + 1
    if pending >= EXIT_DWELL_STEPS:
        return DwellState(level="LOW", pending_exit=0, last_known="LOW")
    return DwellState(level="HIGH", pending_exit=pending, last_known="HIGH")


def stabilize(raw_levels: list[str | None]) -> list[str | None]:
    """등급 수열 전체에 진동 억제를 적용한다.

    재생 시각이 고정된 알려진 수열이므로, 어떤 시점의 등급이든 처음부터
    훑으면 결정된다. DB 없이(D-03) 재현 가능하다.

    **인접한 스텝이 `STEP_MINUTES` 간격일 때만 의미가 있다.** 몇 시간씩 떨어진
    스냅샷에 적용하면 대기 시간이 이미 다 지나버려 아무것도 바뀌지 않는다.
    """
    out: list[str | None] = []
    state = DwellState()
    for raw in raw_levels:
        state = step(raw, state)
        out.append(state.level)
    return out
