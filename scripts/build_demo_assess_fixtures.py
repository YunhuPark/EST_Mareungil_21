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
from pathlib import Path

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


def area_ai_level(risk: dict) -> tuple[float | None, str | None, str]:
    """지역 확률과 이진 등급을 만든다.

    OPEN(TH-04): 센서 확률 -> 지역 확률 집계 규칙은 아직 검증되지 않았다. 기존
    픽스처의 `area_risk.score`("상위 25% 평균")를 그대로 옮기고, 지역 임계는
    센서 단위 임계 TH-03(0.33)을 임시로 쓴다. G2 확정 대상이다.
    """
    prob = risk["area_risk"].get("risk_probability", risk["area_risk"].get("score"))
    threshold = risk["model"]["threshold"]
    if prob is None:
        return None, None, "활성 센서가 없어 지역 위험을 산출할 수 없다."
    level = "HIGH" if prob >= threshold else "LOW"
    margin = abs(prob - threshold)
    note = (
        f"OPEN(TH-04): 지역 집계 규칙과 지역 임계는 미확정이다. 지금은 센서 단위 "
        f"임계 {threshold}(TH-03)를 임시로 적용했다. 현재 확률 {prob} 는 임계와 "
        f"{margin:.4f} 떨어져 있다."
    )
    return prob, level, note


def build_ds_s1() -> dict:
    """DS-S1 — 평온, 데이터 정상 -> MOVE + USER_DESTINATION.

    risk 블록은 RF-S1(2022-08-08 11:00, 실제 모델 출력)을 그대로 쓴다.
    """
    risk = load(FIXTURES / "risk_S1_calm.json")
    prob, ai_level, open_note = area_ai_level(risk)

    # 계약이 요구하는 새 필드를 채운다. 원본 score 는 호환을 위해 남긴다.
    risk["area_risk"]["risk_probability"] = prob
    risk["area_risk"]["ai_risk_level"] = ai_level
    risk["area_risk"]["_open_th04"] = open_note
    risk["model"]["threshold_version"] = "th-0.1.0-draft"

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

        "clock": {
            "mode": "REPLAY",
            "event_time": risk["asof"],
            "data_age_sec": 0,
            "stale": False,
            "label": "2022-08-08 11:00 재생",
        },

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
                    "text": f"30분 뒤 지역 고수위 위험이 낮게 예측됐습니다 (확률 {prob}).",
                    "value": prob,
                    "threshold": risk["model"]["threshold"],
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

        "official": {
            "evacuation_order": False,
            "alerts": [],
            "closures": [],
            "source": "fixture:official_0808",
        },

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
