"""통합 데모(DS-*) AssessResponse 픽스처 생성.

    python scripts/build_demo_assess_fixtures.py

무엇을 하는가
-------------
기존 RF-* 위험 픽스처(**실제 모델 출력**)를 `risk` 블록으로 그대로 싣고, 그 위에
`decision` / `route` 블록을 얹어 UI 가 받는 `AssessResponse` 를 만든다.

무엇을 하지 않는가
------------------
`decision` 과 `route` 는 **아직 STUB 이다.** 판단 엔진(services/decision)과 경로
엔진(services/route)이 붙기 전까지 손으로 적은 값이며, 응답의
`source_kind: "FIXTURE"` 와 각 블록의 `_stub` 필드가 그 사실을 표시한다.
확률·센서 값만 실제 모델 출력이고 행동·경로는 아직 모델이 만든 것이 아니다.

의존성: 표준 라이브러리만 쓴다(앱 .venv 에서 바로 돌아간다).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

from mareungil import area_risk  # stdlib 만 쓴다. pandas 를 끌고 오지 않는다.

# CLAUDE.md 10절이 허용하는 방향이다 - scripts/ 가 services/ 를 **읽기 전용**으로
# 쓴다. M-36 필터를 여기서 다시 구현하면 두 구현이 조용히 어긋난다.
from services.decision import visible_at
from services.decision.enums import Action, RouteStatus
from services.decision.postprocess import CONFIRMED_HOLDS

FIXTURES = ROOT / "contracts" / "fixtures"
OUT_DIR = FIXTURES / "demo"

OFFICIAL_0808 = FIXTURES / "official" / "official_0808.json"
OFFICIAL_DEMO_BLOCKED = FIXTURES / "official" / "official_demo_destination_blocked.json"

DISCLAIMER = "교육·시연용입니다. 공식 재난안전 판단 도구가 아닙니다."
ROUTE_LIMIT = "공식 대피경로 기준 · 상대적으로 위험이 낮은 후보"
EMERGENCY_NOTE = "누르면 전화 앱이 열립니다. 서비스가 대신 신고하거나 위치를 보내지 않습니다."

POLICY_VERSION = "policy-0.1.0-draft"
CONTRACT_VERSION = "v1"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


#: M-08. 신선도 단계는 둘뿐이다. 20분 단계는 회의에서 삭제했다.
STALE_SEC = 600
EXPIRED_SEC = 1800


def replay_label(event_time: datetime) -> str:
    """화면에 그대로 찍히는 재생 시각 문구.

    **손으로 적지 않는다.** 예전에 라벨과 `event_time` 이 어긋나도 계약이 잡지 못했다 —
    둘 다 그냥 문자열이기 때문이다. 한 곳에서 만들면 어긋날 수가 없다.
    """
    return f"{event_time:%Y-%m-%d %H:%M} 재생"


def build_clock(risk: dict, data_age_sec: int = 0) -> dict:
    """M-08 의 네 시각과 경과시간을 만든다.

    재생에서는 **관측시각과 예측 생성시각이 같다.** 모델이 `asof` 까지의 관측으로
    그 시각에 예측을 만들기 때문이다. 두 값을 다르게 보이려고 시각을 지어내지
    않는다 — 실시간 전환 때 어댑터가 실제 값으로 채운다.

    `stale`·`expired` 는 `data_age_sec` 에서 파생되며 손으로 넣지 않는다.
    두 값을 따로 적으면 픽스처마다 어긋날 수 있다.
    """
    asof = risk["asof"]
    issued = datetime.fromisoformat(asof)
    target = issued + timedelta(minutes=risk["primary_horizon"])
    event = issued + timedelta(seconds=data_age_sec)

    return {
        "mode": "REPLAY",
        "event_time": event.isoformat(),
        "observed_at": asof,
        "forecast_issued_at": asof,
        "forecast_target_at": target.isoformat(),
        "last_update_at": asof,
        "data_age_sec": data_age_sec,
        "stale": data_age_sec > STALE_SEC,
        "expired": data_age_sec > EXPIRED_SEC,
        "label": replay_label(event),
    }


def official_at(event_time: str, path: Path = OFFICIAL_0808) -> dict:
    """M-36. 재생 시각에 **이미 공개돼 있던** 공식정보만 남긴 블록을 만든다.

    예전에는 `official_0808.json` 을 필터 없이 통째로 실었다. 파일이 비어 있는
    동안에는 아무 일도 없었지만, O-11 로 실제 값이 들어오는 순간 **11:00 화면이
    22:01 에 보도된 통제를 아는** 상태가 된다. 그러면 서비스가 당시 사용자가 알
    수 없었던 것을 안 것처럼 보이고, 그 상태로 만든 판단은 실제 상황에서 재현되지
    않는다 - M-36 이 막으려던 것이 정확히 그것이다.

    필터 구현은 `services/decision/official.py` 하나뿐이다. 여기서 다시 구현하지
    않는다(CLAUDE.md 10절이 허용하는 읽기 전용 방향).

    `_` 로 시작하는 원본의 개발 주석은 옮기지 않는다. 계약 필드는 하나도 골라
    담지 않으므로 C-21 이 지키려던 것("소비자가 실제 파일을 그대로 받는다")은
    그대로다 - `test_공식정보_블록은_재생시각_필터를_거친_결과다` 가 이것을 고정한다.
    """
    doc = load(path)
    result = visible_at(doc, event_time)

    block = {k: v for k, v in result.official.items() if not k.startswith("_")}
    block["asof"] = event_time
    block["_source_file"] = path.relative_to(ROOT).as_posix()
    block["_visibility"] = {
        "_note": (
            "M-36. 재생 시각에 available_time 이 지나지 않은 항목과 공개시각을 확인하지 "
            "못한(null) 항목을 뺀 결과다. 아래 수는 '이 시각에는 아직 알 수 없었다'를 "
            "말하기 위한 것이며 계약 필드가 아니다."
        ),
        "replay_time": event_time,
        "hidden": result.hidden,
        "undated": result.undated,
    }
    return block


def apply_area_risk(risk: dict) -> dict:
    """`area_risk` 블록을 TH-04(O-01) 단일 구현으로 다시 계산한다.

    예전에는 여기서 두 가지를 틀렸다. 폐기된 `area_risk.score`("상위 25% 평균")를
    그대로 옮겼고, 그 값을 **센서** 임계 TH-03(0.33)과 비교해 등급을 매겼다.
    지역 임계는 `AREA_THRESHOLD`(0.5)이고 0.33 으로 재면 `S2`(0.4)가 `HIGH` 로
    뒤집힌다. 집계는 `mareungil/area_risk.py` 의 `compute()` 하나만 쓴다 —
    `refresh_area_risk.py` 와 같은 함수라 두 경로가 어긋나지 않는다.
    """
    risk["area_risk"] = area_risk.compute(risk["sensors"])
    risk["model"]["threshold_version"] = (
        f"sensor-{risk['model']['threshold']}+area-{area_risk.AREA_THRESHOLD}"
    )
    return risk["area_risk"]


def build_ds_s1() -> dict:
    """DS-S1 — 평온, 데이터 정상 -> MOVE + USER_DESTINATION.

    risk 블록은 RF-S1(2022-08-08 11:00, 실제 모델 출력)을 그대로 쓴다.
    """
    risk = load(FIXTURES / "risk_S1_calm.json")
    area = apply_area_risk(risk)
    prob = area["risk_probability"]

    destinations = load(ROOT / "contracts" / "destinations.json")
    destination = next(p for p in destinations["points"] if p["id"] == "GN-003")
    dest = {k: destination[k] for k in ("id", "label", "lat", "lon")}

    return {
        "_scenario": "DS-S1",
        "_why_this_moment": "평온, 데이터 정상. 행동 우선순위 1~9 에 걸리는 조건이 없어 기본값 MOVE 로 떨어진다.",
        "_risk_source": "contracts/fixtures/risk_S1_calm.json (RF-S1) — 실제 모델 출력",
        "_stub": "decision·route 블록은 STUB 이다. 판단 엔진·경로 엔진 미구현 구간을 손으로 채운 값이며 모델이 만든 값이 아니다.",

        "contract_version": CONTRACT_VERSION,
        "source_kind": "FIXTURE",

        "clock": build_clock(risk),

        "location": {
            "label": "강남역 일대",
            "in_service_area": True,
            "lat": 37.4979,
            "lon": 127.0276,
        },

        "risk": risk,

        "decision": {
            "_stub": "우선순위 10(그 외) 기본값. services/decision 구현 전 손으로 적은 값이다.",
            "primary_action": "MOVE",
            "action": "MOVE",
            "route_postprocess_applied": False,
            "service_risk_level": "SAFE",
            "needs_route": True,
            "next_check_at": "2022-08-08T11:30:00+09:00",
            "reason_code": "NO_TRIGGER",
            "user_state": {
                "context": "OUTDOOR",
                "trapped": False,
                "hazard_signs": [],
                "profiles": [],
                "destination": dest,
            },
            "reasons": [
                {
                    "code": "AI_AREA_LOW",
                    "text": f"30분 뒤 지역 고수위 위험이 낮게 예측됐습니다 (지역값 {prob}).",
                    "value": prob,
                    # 지역 임계(TH-04)와 비교한 값이다. model.threshold(0.33)는
                    # 센서 단위 임계라 여기 쓰면 축이 어긋난다.
                    "threshold": area_risk.AREA_THRESHOLD,
                    "basis": "AI_PREDICTION",
                },
                {
                    "code": "RAIN_BELOW_THRESHOLD",
                    "text": "10분 강우와 60분 누적 강우가 모두 팀 기준값 아래입니다.",
                    "value": 0.0,
                    "threshold": "10분 5mm 또는 60분 40mm",
                    "basis": "TEAM_RULE",
                },
                {
                    "code": "NO_OFFICIAL_ORDER",
                    "text": "이 시각 기준 공식 대피 지시가 없습니다.",
                    "value": None,
                    "threshold": None,
                    "basis": "OFFICIAL_GUIDANCE",
                },
            ],
            "policy_version": POLICY_VERSION,
        },

        "route": {
            "_stub": "services/route 미구현. 후보 비교 결과가 아니라 형식을 보여주는 자리표시자다.",
            "status": "FALLBACK_CANDIDATE",
            "route_verified": False,
            "route_target": "USER_DESTINATION",
            "target": {
                "kind": "DESTINATION_POINT",
                "id": dest["id"],
                "label": dest["label"],
                "lat": dest["lat"],
                "lon": dest["lon"],
                "reason": "사용자가 고른 목적지",
                "data_asof": risk["asof"],
            },
            "route_attempted": True,
            "no_safe_route": False,
            "distance_m": 840,
            "eta_sec": 720,
            "detour_ratio": 1.0,
            "candidates": [
                {
                    "route_id": "OFR-07",
                    "label": "테헤란로 북측 보도",
                    "rank": 1,
                    "relative_risk": 0.08,
                    "distance_m": 840,
                    "excluded": False,
                    "excluded_by": None,
                },
                {
                    "route_id": "OFR-12",
                    "label": "역삼로 방면",
                    "rank": 2,
                    "relative_risk": 0.14,
                    "distance_m": 910,
                    "excluded": False,
                    "excluded_by": None,
                },
            ],
            "hazards": [],
            "profile_applied": [],
            "limit": ROUTE_LIMIT,
            "source": "fixture:official_routes_30",
        },

        # C-21 + M-36. 계약 필드는 하나도 골라 담지 않되(그래야 asof·verification·
        # confirmed_flooding 을 소비자가 받는지 픽스처에서 드러난다), 이 재생 시각에
        # 아직 공개되지 않았던 항목은 뺀다. 두 규칙이 함께 필요하다.
        "official": official_at(build_clock(risk)["event_time"]),

        # data_quality 는 최상위에 복사하지 않는다. 정본은 risk.data_quality 하나다.
        # 두 곳에 두면 DQ-03(관측률<70% -> WAIT)이 어느 값을 읽는지 모호해진다.

        "notice": {
            "disclaimer": DISCLAIMER,
            "route_limit": ROUTE_LIMIT,
            "emergency_note": EMERGENCY_NOTE,
        },

        "versions": {
            "model": f"{risk['model']['name']}-{risk['model']['version']}",
            "policy": POLICY_VERSION,
            "data": "processed/v2",
            "contract": CONTRACT_VERSION,
        },
    }


# --- M-32. 시설 상태로 후보가 줄어드는 흐름 ---------------------------------
#
# 회의는 이 흐름을 **고정 픽스처로 시연**하기로 정했다. 실시간 시설상태 연동이
# 아니며, 저장소에 대피시설 원자료가 없으므로 아래 시설 값은 **전부 합성값**이다.
# 라벨에 그 사실을 적고 응답의 source_kind=FIXTURE 가 함께 표시한다(M-24).
#
#     DS-S7  1순위 만석 -> 2순위로 전환, EVACUATE 유지
#     DS-S8  후보 0개   -> NO_SAFE_POINT, EVACUATE 유지 + 119 강조
#
# 두 픽스처의 risk 블록은 RF-S3(피크, 실제 모델 출력)이다. 시설 상태만 합성이다.

#: 합성 대피시설. 실제 수해대피소 107개 원자료가 저장소에 없어 형식만 보인다.
#: 좌표는 강남역 주변의 임의 지점이며 실제 시설 위치가 아니다.
DEMO_SHELTERS = [
    {"id": "DEMO-SH-001", "label": "합성 대피시설 1순위 — 실제 시설 아님", "lat": 37.4995, "lon": 127.0301},
    {"id": "DEMO-SH-002", "label": "합성 대피시설 2순위 — 실제 시설 아님", "lat": 37.5011, "lon": 127.0288},
    {"id": "DEMO-SH-003", "label": "합성 대피시설 3순위 — 실제 시설 아님", "lat": 37.4962, "lon": 127.0334},
]

#: M-24. 이 값이 합성이라는 표시. '개방·안전 확인 필요'(M-23)는 화면 쪽 상수이며
#: 여기서 다시 적지 않는다 - 두 곳에 두면 문구를 고칠 때 한쪽만 바뀐다.
SHELTER_NOTE = "(합성값 DEMO_FIXTURE — 실제 시설 상태가 아닙니다)"


def _evacuate_base() -> tuple[dict, dict]:
    """DS-S7·S8 이 공유하는 몸통. (응답, risk) 를 돌려준다.

    AI HIGH + 실외이므로 행동 우선순위 6 에서 EVACUATE 다. 경로 결과와 무관하게
    이 값은 유지된다(M-15) - 두 픽스처가 보여주려는 것이 정확히 그것이다.
    """
    risk = load(FIXTURES / "risk_S3_peak.json")
    area = apply_area_risk(risk)
    prob = area["risk_probability"]

    destinations = load(ROOT / "contracts" / "destinations.json")
    destination = next(p for p in destinations["points"] if p["id"] == "GN-003")
    dest = {k: destination[k] for k in ("id", "label", "lat", "lon")}

    rain = next(
        (d["value"] for d in risk.get("drivers", []) if d["feature"] == "rain_past_60m_mm"),
        None,
    )

    response = {
        "contract_version": CONTRACT_VERSION,
        "source_kind": "FIXTURE",
        "clock": build_clock(risk),
        "location": {
            "label": "강남역 일대",
            "in_service_area": True,
            "lat": 37.4979,
            "lon": 127.0276,
        },
        "risk": risk,
        "decision": {
            "_stub": "우선순위 6(AI HIGH + 실외). services/decision 구현 전 손으로 적은 값이다.",
            "primary_action": "EVACUATE",
            "action": "EVACUATE",
            "route_postprocess_applied": False,
            "service_risk_level": "DANGER" if rain and rain >= 40.0 else "CAUTION",
            "needs_route": True,
            "next_check_at": None,
            "reason_code": "AI_AREA_HIGH",
            "user_state": {
                "context": "OUTDOOR",
                "trapped": False,
                "hazard_signs": [],
                "profiles": [],
                "destination": dest,
            },
            "reasons": [
                {
                    "code": "AI_AREA_HIGH",
                    "text": f"30분 뒤 지역 고수위 위험이 높게 예측됐습니다 (지역값 {prob}).",
                    "value": prob,
                    "threshold": area_risk.AREA_THRESHOLD,
                    "basis": "AI_PREDICTION",
                },
                {
                    "code": "RAIN_60M_OVER_TH02",
                    "text": "60분 누적 강우가 팀 기준값을 넘었습니다.",
                    "value": rain,
                    "threshold": 40.0,
                    "basis": "TEAM_RULE",
                },
            ],
            "policy_version": POLICY_VERSION,
        },
        "official": official_at(build_clock(risk)["event_time"]),
        "notice": {
            "disclaimer": DISCLAIMER,
            "route_limit": ROUTE_LIMIT,
            "emergency_note": EMERGENCY_NOTE,
        },
        "versions": {
            "model": f"{risk['model']['name']}-{risk['model']['version']}",
            "policy": POLICY_VERSION,
            "data": "processed/v2",
            "contract": CONTRACT_VERSION,
        },
    }
    return response, risk


def build_ds_s7() -> dict:
    """DS-S7 — 1순위 만석 확인 -> 2순위로 전환. EVACUATE 유지."""
    response, risk = _evacuate_base()
    chosen = DEMO_SHELTERS[1]

    response["_scenario"] = "DS-S7"
    response["_why_this_moment"] = (
        "M-32. 1순위 시설이 만석으로 확인돼 후보에서 빠지고 2순위로 넘어간다. "
        "행동은 EVACUATE 그대로이고 바뀌는 것은 도달 대상뿐이다. "
        "DS-S8 과 **같은 재생 시각의 두 갈래**다 - 시설 상태 시계열이 없으므로 "
        "시간 흐름이 아니라 상태 차이로 보여준다."
    )
    response["_risk_source"] = "contracts/fixtures/risk_S3_peak.json (RF-S3) — 실제 모델 출력"
    response["_stub"] = (
        "decision·route 블록은 STUB 이고 시설 상태는 합성값이다(M-24 DEMO_FIXTURE). "
        "시설상태 연동이 아니며 저장소에 대피시설 원자료가 없다."
    )
    response["route"] = {
        "_stub": "services/route 미구현. 시설 상태는 합성값이다.",
        "status": "FALLBACK_CANDIDATE",
        "route_verified": False,
        "route_target": "SAFE_POINT",
        "target": {
            "kind": "SHELTER",
            **chosen,
            "reason": f"1순위 시설이 만석으로 확인돼 다음 후보로 전환했습니다. {SHELTER_NOTE}",
            "data_asof": risk["asof"],
        },
        "route_attempted": True,
        "no_safe_route": False,
        "distance_m": 1120,
        "eta_sec": 960,
        "detour_ratio": 1.12,
        "candidates": [
            {
                "route_id": "DEMO-OFR-21",
                "label": "합성 후보 1 — 1순위 시설 방면",
                "rank": 1,
                "relative_risk": 0.11,
                "distance_m": 640,
                "excluded": True,
                "excluded_by": "SHELTER_FULL",
            },
            {
                "route_id": "DEMO-OFR-22",
                "label": "합성 후보 2 — 2순위 시설 방면",
                "rank": 2,
                "relative_risk": 0.19,
                "distance_m": 1120,
                "excluded": False,
                "excluded_by": None,
            },
        ],
        "hazards": [],
        "profile_applied": [],
        "limit": ROUTE_LIMIT,
        "source": "fixture:demo_shelter_flow (합성값)",
    }
    return response


def build_ds_s8() -> dict:
    """DS-S8 — 후보 0개 -> NO_SAFE_POINT. EVACUATE 유지 + 119 강조."""
    response, _risk = _evacuate_base()

    response["_scenario"] = "DS-S8"
    response["_why_this_moment"] = (
        "M-32. 세 후보가 모두 시설 상태로 빠져 남은 후보가 없다. 무한 재검색이나 "
        "임의 목적지 생성을 하지 않고 NO_SAFE_POINT 를 돌려주며, M-15 에 따라 "
        "행동은 EVACUATE 를 유지하고 119 를 강조한다. EMERGENCY 로 바꾸지 않는다. "
        "DS-S7 과 같은 재생 시각의 두 갈래이며 시간 흐름이 아니다."
    )
    response["_risk_source"] = "contracts/fixtures/risk_S3_peak.json (RF-S3) — 실제 모델 출력"
    response["_stub"] = (
        "decision·route 블록은 STUB 이고 시설 상태는 합성값이다(M-24 DEMO_FIXTURE)."
    )
    response["decision"]["reason_code"] = "ROUTE_NO_SAFE_POINT"
    response["decision"]["reasons"] = [
        response["decision"]["reasons"][0],
        {
            "code": "ROUTE_NO_SAFE_POINT",
            "text": "안내할 수 있는 안전거점이 없습니다.",
            "value": None,
            "threshold": None,
            "basis": "TEAM_RULE",
        },
    ]
    response["notice"]["route_limit"] = (
        "안내할 수 있는 안전거점이 없습니다. 119 에 연락해 상황을 알리세요."
    )
    response["route"] = {
        "_stub": "services/route 미구현. 시설 상태는 합성값이다.",
        "status": "NO_SAFE_POINT",
        "route_verified": False,
        "route_target": "SAFE_POINT",
        "target": None,
        "route_attempted": False,
        "no_safe_route": None,
        "distance_m": None,
        "eta_sec": None,
        "detour_ratio": None,
        "candidates": [
            {
                "route_id": "DEMO-OFR-21",
                "label": "합성 후보 1 — 1순위 시설 방면",
                "rank": 1,
                "relative_risk": 0.11,
                "distance_m": 640,
                "excluded": True,
                "excluded_by": "SHELTER_FULL",
            },
            {
                "route_id": "DEMO-OFR-22",
                "label": "합성 후보 2 — 2순위 시설 방면",
                "rank": 2,
                "relative_risk": 0.19,
                "distance_m": 1120,
                "excluded": True,
                "excluded_by": "SHELTER_CLOSED",
            },
            {
                "route_id": "DEMO-OFR-23",
                "label": "합성 후보 3 — 3순위 시설 방면",
                "rank": 3,
                "relative_risk": 0.24,
                "distance_m": 1480,
                "excluded": True,
                "excluded_by": "SHELTER_INACCESSIBLE",
            },
        ],
        "hazards": [],
        "profile_applied": [],
        "limit": ROUTE_LIMIT,
        "source": "fixture:demo_shelter_flow (합성값)",
    }
    return response


# --- M-16. 목적지가 막혔을 때 --------------------------------------------------


def build_ds_s6() -> dict:
    """DS-S6 — MOVE + 목적지가 공식 통제 구간 -> DESTINATION_BLOCKED. MOVE 유지.

    **공식정보만 시연용 파일을 쓴다.** 실제로 확인된 2022-08-08 통제 중에는 이
    화면을 만들 수 있는 것이 없다 - 강남 도로 통제 보도가 전부 22:01 이후 송고라
    21:40 에는 공개돼 있지 않았고(M-36), 강남역 반경 1km 안의 통제 하나는 차량
    통제라 보행 목적지를 막지 못한다(RT-11). 지어낸 값과 확인된 값을 한 파일에
    섞지 않으려고 파일을 나눴고, 화면은 DEMO_FIXTURE 배지를 그대로 띄운다(M-24).

    risk 블록은 RF-S2(12:10, 상승 국면, 실제 모델 출력)다. 지역값 0.4 로 아직
    `LOW` 이므로 1차 행동이 `MOVE` 다 - 목적지가 막혔다고 해서 이동 자체가
    위험해지지는 않는다는 것이 이 시나리오가 보여주려는 것이다.
    """
    risk = load(FIXTURES / "risk_S2_rising.json")
    area = apply_area_risk(risk)
    prob = area["risk_probability"]
    clock = build_clock(risk)

    official = official_at(clock["event_time"], OFFICIAL_DEMO_BLOCKED)
    blocked_ids = {
        did for c in official["closures"] for did in c.get("blocks_destination_ids", [])
    }

    destinations = load(ROOT / "contracts" / "destinations.json")
    destination = next(p for p in destinations["points"] if p["id"] in blocked_ids)
    dest = {k: destination[k] for k in ("id", "label", "lat", "lon")}

    # 문구를 손으로 옮겨 적지 않는다. 확정 규칙의 단일 출처는 postprocess 다 —
    # 두 곳에 적으면 회의 확정문을 고칠 때 한쪽만 바뀐다.
    code, text, basis = CONFIRMED_HOLDS[(Action.MOVE, RouteStatus.DESTINATION_BLOCKED)]

    return {
        "_scenario": "DS-S6",
        "_why_this_moment": (
            "M-16. 사용자가 고른 목적지가 이 시각에 공식 통제 구간에 들어 있다. "
            "행동은 MOVE 그대로이고 바뀌는 것은 경로안내뿐이다 — 막힌 것은 목적지이지 "
            "이동 자체가 아니며, 그 동네가 위험한지는 우선순위 6~9 에서 이미 판정됐다. "
            "차단 근거는 blocks_destination_ids 명시 지정 하나뿐이고 좌표 거리로 "
            "추정하지 않는다(O-07)."
        ),
        "_risk_source": "contracts/fixtures/risk_S2_rising.json (RF-S2) — 실제 모델 출력",
        "_stub": (
            "decision·route 블록은 STUB 이고 공식정보는 시연용 합성값이다"
            "(M-24 DEMO_FIXTURE). 실제 확인된 통제로는 이 화면이 만들어지지 않는다."
        ),

        "contract_version": CONTRACT_VERSION,
        "source_kind": "FIXTURE",

        "clock": clock,

        "location": {
            "label": "강남역 일대",
            "in_service_area": True,
            "lat": 37.4979,
            "lon": 127.0276,
        },

        "risk": risk,

        "decision": {
            "_stub": "우선순위 10(그 외) 기본값 + M-16 유지. services/decision 구현 전 손으로 적은 값이다.",
            "primary_action": "MOVE",
            "action": "MOVE",
            # 유지는 '적용했다'가 아니다. 행동이 바뀌지 않았으므로 False 다(RT-10).
            "route_postprocess_applied": False,
            "service_risk_level": "SAFE",
            "needs_route": True,
            "next_check_at": "2022-08-08T12:40:00+09:00",
            "reason_code": code,
            "user_state": {
                "context": "OUTDOOR",
                "trapped": False,
                "hazard_signs": [],
                "profiles": [],
                "destination": dest,
            },
            "reasons": [
                {
                    "code": "AI_AREA_LOW",
                    "text": f"30분 뒤 지역 고수위 위험이 낮게 예측됐습니다 (지역값 {prob}).",
                    "value": prob,
                    "threshold": area_risk.AREA_THRESHOLD,
                    "basis": "AI_PREDICTION",
                },
                {
                    "code": code,
                    "text": text,
                    "value": None,
                    "threshold": None,
                    "basis": basis.value,
                },
            ],
            "policy_version": POLICY_VERSION,
        },

        "route": {
            "_stub": "services/route 미구현. 통제 값은 시연용 합성값이다.",
            "status": "DESTINATION_BLOCKED",
            "route_verified": False,
            "route_target": "USER_DESTINATION",
            # M-16. 경로안내를 중단한다. 목적지가 막힌 채로 후보를 그리면
            # 화면이 '그래도 이쪽으로 가라'로 읽힌다.
            "target": None,
            "route_attempted": False,
            "no_safe_route": None,
            "distance_m": None,
            "eta_sec": None,
            "detour_ratio": None,
            "candidates": [],
            "hazards": [],
            "profile_applied": [],
            "limit": ROUTE_LIMIT,
            "source": "fixture:demo_destination_blocked (합성값)",
        },

        "official": official,

        "notice": {
            "disclaimer": DISCLAIMER,
            "route_limit": text,
            "emergency_note": EMERGENCY_NOTE,
        },

        "versions": {
            "model": f"{risk['model']['name']}-{risk['model']['version']}",
            "policy": POLICY_VERSION,
            "data": "processed/v2",
            "contract": CONTRACT_VERSION,
        },
    }


# --- P1-1. 고립 신고 -> EMERGENCY ------------------------------------------
#
# 행동 우선순위 1 이다. **다른 어떤 신호보다 먼저 이긴다** — AI 가 LOW 여도, 자료가
# 30분을 넘겨도, 경로가 어떻든 EMERGENCY 다. 계약도 같은 것을 강제한다
# (`assess_response` allOf: trapped=true -> primary_action=action=EMERGENCY).
#
# 경로 엔진을 타지 않는 유일한 LIVE 시나리오다. `EMERGENCY` 는 `not_required()`
# 로 끝나므로 센서도 안전거점도 필요 없다 - 그래서 가장 싸게 붙는다.


def build_ds_s4() -> dict:
    """DS-S4 — 지하 고립 신고 -> EMERGENCY + NOT_REQUIRED.

    risk 블록은 RF-S3(피크, 실제 모델 출력)다. 고립은 피크 국면에서 벌어진다.
    **risk 는 EMERGENCY 를 만든 근거가 아니다** - 우선순위 1 은 자기신고 하나로
    결정되며 AI 값과 독립이다(F-14). 피크를 고른 것은 서사일 뿐이다.

    `_stub` 을 달지 않는다. 앞선 네 픽스처의 `_stub` 은 "엔진 구현 전에 손으로
    적었다"는 뜻인데, 이 파일은 두 엔진이 **이미 있는 상태에서** 그 출력에 맞춰
    쓴 것이라 같은 말을 붙이면 거짓이 된다.
    """
    risk = load(FIXTURES / "risk_S3_peak.json")
    apply_area_risk(risk)

    destinations = load(ROOT / "contracts" / "destinations.json")
    destination = next(p for p in destinations["points"] if p["id"] == "GN-001")
    dest = {k: destination[k] for k in ("id", "label", "lat", "lon")}

    hazard_signs = ["WATER_INFLOW"]

    return {
        "_scenario": "DS-S4",
        "_why_this_moment": (
            "지하공간에서 고립을 신고했다. 우선순위 1 이 나머지 아홉 규칙을 모두 "
            "제치고 EMERGENCY 를 만든다. 경로는 탐색하지 않는다."
        ),
        "_risk_source": "contracts/fixtures/risk_S3_peak.json (RF-S3) — 실제 모델 출력",
        "_engine": (
            "decision·route 는 손으로 지어낸 값이 아니라 decide()/apply()/"
            "DesignatedPointRouteProvider 가 이 입력에서 내는 값을 옮긴 것이다."
        ),

        "contract_version": CONTRACT_VERSION,
        "source_kind": "FIXTURE",

        "clock": build_clock(risk),

        "location": {
            "label": "강남역 일대",
            "in_service_area": True,
            "lat": 37.4979,
            "lon": 127.0276,
        },

        "risk": risk,

        "decision": {
            "primary_action": "EMERGENCY",
            "action": "EMERGENCY",
            "route_postprocess_applied": False,
            # C-23 / F-02. 고립 신고는 SEVERE 를 만들 수 있는 직접 신호 셋 중 하나다.
            # AI 확률로는 SEVERE 에 닿지 못한다.
            "service_risk_level": "SEVERE",
            # EMERGENCY 는 NEEDS_ROUTE 밖이다. 손으로 정한 값이 아니라 파생값이다.
            "needs_route": False,
            # 재확인 시각을 두지 않는다. 이 화면에서 할 일은 119 이지 재판단이 아니다.
            "next_check_at": None,
            "reason_code": "TRAPPED_REPORTED",
            "user_state": {
                "context": "UNDERGROUND",
                "trapped": True,
                "hazard_signs": hazard_signs,
                "profiles": [],
                # F-19. EMERGENCY 가 쓰지 않아도 목적지는 필수 필드다.
                "destination": dest,
            },
            "reasons": [
                {
                    "code": "TRAPPED_REPORTED",
                    "text": "고립 상태로 신고됐습니다.",
                    "value": None,
                    "threshold": None,
                    "basis": "TEAM_RULE",
                },
                {
                    "code": "UNDERGROUND_HAZARD_SIGN",
                    "text": "지하공간에서 현장 위험 징후가 신고됐습니다.",
                    "value": ", ".join(hazard_signs),
                    "threshold": None,
                    "basis": "TEAM_RULE",
                },
            ],
            "policy_version": POLICY_VERSION,
        },

        # 계약 allOf — 경로가 필요 없는 행동은 ③을 호출하지 않는다.
        # 형태를 손으로 짓지 않고 services/route/interface.not_required() 가
        # 만드는 것과 같게 둔다. 두 곳이 갈라지면 배선 뒤 route 블록이 바뀐다.
        "route": {
            "status": "NOT_REQUIRED",
            "route_verified": False,
            "route_target": None,
            "target": None,
            "route_attempted": False,
            "no_safe_route": None,
            "limit": "경로 탐색이 필요하지 않은 행동입니다.",
        },

        "official": official_at(build_clock(risk)["event_time"]),

        "notice": {
            "disclaimer": DISCLAIMER,
            "route_limit": ROUTE_LIMIT,
            "emergency_note": EMERGENCY_NOTE,
        },

        "versions": {
            "model": f"{risk['model']['name']}-{risk['model']['version']}",
            "policy": POLICY_VERSION,
            "data": "processed/v2",
            "contract": CONTRACT_VERSION,
        },
    }


# --- 반드시 거부되어야 하는 조합 -------------------------------------------
#
# 계약이 "무엇을 막는가"는 통과 예제가 아니라 거부 예제가 증명한다. 아래 파일이
# 하나라도 **통과하면** 검증이 실패한다(contracts/validate.py).


def _compact_response() -> dict:
    """거부 예제용 축약 응답.

    DS-S1 에서 risk 블록만 무데이터 픽스처(RF-E1)로 바꿔 파일 크기를 줄인다.
    RF-E1 은 그 자체로 스키마를 통과하므로, 남는 위반은 각 예제가 의도한 하나뿐이다.
    """
    base = build_ds_s1()
    for key in ("_scenario", "_why_this_moment", "_risk_source", "_stub"):
        base.pop(key, None)
    base["risk"] = load(FIXTURES / "risk_E1_no_data.json")
    return base


def _invalid_cases() -> dict[str, dict]:
    cases: dict[str, dict] = {}

    # RT-13. 안전거점 탐색은 EVACUATE 에만 있으므로 MOVE 는 NO_SAFE_POINT 를 낼 수 없다.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "RT-13 / F-10",
        "why": "MOVE 응답에 NO_SAFE_POINT 가 실렸다",
    }
    r["route"].update(
        status="NO_SAFE_POINT", route_target="SAFE_POINT", target=None,
        route_attempted=False, no_safe_route=None,
    )
    cases["move_with_no_safe_point"] = r

    # RT-13. 안전거점은 안전 조건을 통과한 후보만 고르므로 EVACUATE 에 목적지 차단이 없다.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "RT-13 / F-10",
        "why": "EVACUATE 응답에 DESTINATION_BLOCKED 가 실렸다",
    }
    r["decision"].update(primary_action="EVACUATE", action="EVACUATE")
    r["route"].update(
        status="DESTINATION_BLOCKED", route_target="USER_DESTINATION",
        route_attempted=False, no_safe_route=None,
    )
    cases["evacuate_with_destination_blocked"] = r

    # R13 / F-19. 목적지는 필수 입력이다.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "R13 / F-19",
        "why": "user_state.destination 이 null 이다",
    }
    r["decision"]["user_state"]["destination"] = None
    cases["destination_null"] = r

    # AI-10 / C-17. 이름만 risk_level 인 필드는 어느 계약에도 두지 않는다.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "AI-10 / 설계서 6.1",
        "why": "두 위험 축을 구분하지 않는 모호한 risk_level 필드가 들어왔다",
    }
    r["decision"]["risk_level"] = "HIGH"
    cases["ambiguous_risk_level"] = r

    # X1 / C-14. 검증 데이터 부족으로 MVP 에서 제외한 프로필.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "X1 / C-14",
        "why": "MVP 제외 프로필 WHEELCHAIR 가 들어왔다",
    }
    r["decision"]["user_state"]["profiles"] = ["WHEELCHAIR"]
    cases["profile_wheelchair"] = r

    # M-15 / C-31. EVACUATE 후 경로가 실패해도 EMERGENCY 로 자동 전환하지 않는다.
    # 예전에는 이 조합이 OPEN 이라 계약이 아무것도 막지 못했다. 2026-08-16 회의가
    # '유지'를 확정했으므로 이제 유지에서 벗어나는 것이 위반이다.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "M-15 / C-31",
        "why": "EVACUATE 인데 안전거점이 없다는 이유로 EMERGENCY 로 자동 전환했다. 고립 신고가 없으므로 EVACUATE 를 유지해야 한다",
    }
    r["decision"].update(
        primary_action="EVACUATE", action="EMERGENCY", route_postprocess_applied=True
    )
    r["route"].update(
        status="NO_SAFE_POINT", route_target="SAFE_POINT", target=None,
        route_attempted=False, no_safe_route=None,
    )
    cases["evacuate_route_failure_escalated"] = r

    # M-16. 목적지 차단과 안전경로 없음은 다른 상태다. 둘을 같이 WAIT 으로 만들면
    # 화면이 '다른 목적지를 고르라'와 '움직이지 말라'를 구분하지 못한다.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "M-16",
        "why": "목적지 차단을 안전경로 없음과 같이 취급해 WAIT 으로 바꿨다. DESTINATION_BLOCKED 는 MOVE 를 유지하고 목적지 재선택을 안내한다",
    }
    r["decision"].update(action="WAIT", route_postprocess_applied=True)
    r["route"].update(
        status="DESTINATION_BLOCKED", route_target="USER_DESTINATION", target=None,
        route_attempted=False, no_safe_route=None,
    )
    cases["move_destination_blocked_switched_to_wait"] = r

    # M-08. 신선도 두 단계는 포함 관계다. 30분을 넘겼는데 '지연 아님'일 수 없다.
    r = _compact_response()
    r["_expect_invalid"] = {
        "schema": "assess_response",
        "rule": "M-08",
        "why": "expired=true 인데 stale=false 다. 화면이 '지연 아님'과 '근거 제외'를 동시에 말하게 된다",
    }
    r["clock"].update(data_age_sec=2400, stale=False, expired=True)
    cases["expired_without_stale"] = r

    # M-36. observed_at 을 nullable 로 바꿨다고 필드를 빼도 되는 것은 아니다.
    # null 은 '관측 시각을 확인하지 못했다'이고, 키가 없는 것은 '그런 항목을 아예
    # 생각하지 않았다'다. 둘을 같게 두면 확인 안 한 것이 조용히 사라진다.
    cases["flooding_without_observed_at"] = {
        "_expect_invalid": {
            "schema": "official_info",
            "rule": "M-36",
            "why": (
                "confirmed_flooding 항목에 observed_at 키가 아예 없다. "
                "관측 시각 미확인은 null 로 적고 필드를 빼지 않는다"
            ),
        },
        "source": "fixture:reject_probe",
        "asof": "2022-08-08T21:40:00+09:00",
        "verification": "DEMO_FIXTURE",
        "evacuation_order": False,
        "alerts": [],
        "closures": [],
        "confirmed_flooding": [
            {"geom_ref": "PROBE-F-001", "available_time": None},
        ],
    }

    # RT-09b. 탐색하지 않은 상태에서 '안전한 경로가 없다'고 단정할 수 없다.
    cases["no_safe_route_without_attempt"] = {
        "_expect_invalid": {
            "schema": "safe_route",
            "rule": "RT-09b",
            "why": "route_attempted=false 인데 no_safe_route=true 다",
        },
        "status": "NO_SAFE_ROUTE",
        "route_verified": False,
        "route_target": "USER_DESTINATION",
        "target": None,
        "route_attempted": False,
        "no_safe_route": True,
        "limit": ROUTE_LIMIT,
    }

    return cases


BUILDERS = {
    "DS-S1": build_ds_s1,
    # M-16 의 목적지 차단. 공식정보만 시연용 파일을 쓴다.
    "DS-S6": build_ds_s6,
    # M-32 의 시설 상태 흐름. 시설 값은 합성이고 risk 블록만 실제 모델 출력이다.
    "DS-S7": build_ds_s7,
    "DS-S8": build_ds_s8,
    # P1-1. 우선순위 1(고립 신고). 경로를 타지 않는 유일한 LIVE 시나리오다.
    "DS-S4": build_ds_s4,
}

PENDING = {
    "DS-S2": "강우·위험 상승 -> WAIT",
    "DS-S3": "공식 대피 지시 또는 AI HIGH + 실외 -> EVACUATE + SAFE_POINT",
    "DS-S5": "MOVE + 모든 후보 제외 -> NO_SAFE_ROUTE, 최종 WAIT",
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, build in BUILDERS.items():
        path = OUT_DIR / f"{name}.assess_response.json"
        path.write_text(json.dumps(build(), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> {path.relative_to(ROOT).as_posix()}")

    invalid_dir = FIXTURES / "invalid"
    invalid_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in _invalid_cases().items():
        path = invalid_dir / f"{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> {path.relative_to(ROOT).as_posix()}  (거부되어야 함)")

    print("\n미작성 (T+6:00~8:00 구간, 담당: 백엔드/정책):")
    for name, desc in PENDING.items():
        print(f"  {name}  {desc}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
