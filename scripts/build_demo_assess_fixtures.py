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

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mareungil import area_risk  # stdlib 만 쓴다. pandas 를 끌고 오지 않는다.

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "contracts" / "fixtures"
OUT_DIR = FIXTURES / "demo"

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

        # C-21. 손으로 4개 키만 골라 적지 않고 공식정보 픽스처를 **그대로** 싣는다.
        # 예전에는 여기서 evacuation_order·alerts·closures·source 만 옮겨 적었고,
        # 그래서 asof·verification·confirmed_flooding 을 계약이 받지 못한다는 사실이
        # 어떤 픽스처에서도 드러나지 않았다. 실제 파일을 통과시켜야 계약이 검사된다.
        "official": load(FIXTURES / "official" / "official_0808.json"),

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
        "official": load(FIXTURES / "official" / "official_0808.json"),
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


# DS-S2 ~ DS-S6 는 T+6:00~8:00 구간 작업이다. 여기 자리만 남겨둔다.
BUILDERS = {
    "DS-S1": build_ds_s1,
    # M-32 의 시설 상태 흐름. 시설 값은 합성이고 risk 블록만 실제 모델 출력이다.
    "DS-S7": build_ds_s7,
    "DS-S8": build_ds_s8,
}

PENDING = {
    "DS-S2": "강우·위험 상승 -> WAIT",
    "DS-S3": "공식 대피 지시 또는 AI HIGH + 실외 -> EVACUATE + SAFE_POINT",
    "DS-S4": "trapped=true -> EMERGENCY",
    "DS-S5": "MOVE + 모든 후보 제외 -> NO_SAFE_ROUTE, 최종 WAIT",
    "DS-S6": "MOVE + 목적지가 공식 통제 구간 -> DESTINATION_BLOCKED",
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
