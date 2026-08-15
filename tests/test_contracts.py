"""계약 검증.

`contracts/validate.py` 와 같은 것을 본다. 여기 있는 이유는 `pytest` 한 번으로
계약까지 확인되게 하기 위해서다 — 검증 명령을 두 번 기억하게 만들지 않는다.
"""

from __future__ import annotations

import json

import pytest

from contracts.validate import (
    COMPOSED_BLOCKS,
    Case,
    FIXTURE_DIR,
    SCHEMA_DIR,
    discover,
    errors_for,
    load_schemas,
)

REQUIRED_CONTRACTS = ["risk_assessment", "action_decision", "safe_route", "assess_response"]


@pytest.fixture(scope="module")
def validators():
    return load_schemas()


def test_네_계약_스키마가_존재한다(validators):
    """CT-01~CT-04. 4대 계약이 전부 있어야 G0 를 통과한다."""
    for name in REQUIRED_CONTRACTS:
        assert name in validators, f"{name}.schema.json 이 없다"


def test_모든_스키마가_draft_2020_12다(validators):
    for path in SCHEMA_DIR.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema", path.name


@pytest.mark.parametrize("case", [c for c in discover() if c.expect_valid], ids=lambda c: c.rel)
def test_유효_픽스처가_통과한다(validators, case: Case):
    assert errors_for(validators, case) == []


@pytest.mark.parametrize("case", [c for c in discover() if not c.expect_valid], ids=lambda c: c.rel)
def test_잘못된_조합이_거부된다(validators, case: Case):
    """계약이 무엇을 막는지는 거부 예제가 증명한다.

    통과해버리면 스키마가 그 조합을 막지 못한다는 뜻이므로 실패다.
    """
    assert errors_for(validators, case), f"거부되어야 하는데 통과했다 — {case.note}"


def test_거부_예제가_요구된_조합을_모두_덮는다():
    """작업 지시에 명시된 다섯 조합이 빠지지 않았는지 본다."""
    covered = {c.path.stem for c in discover() if not c.expect_valid}
    for name in [
        "move_with_no_safe_point",          # MOVE + NO_SAFE_POINT
        "evacuate_with_destination_blocked",  # EVACUATE + DESTINATION_BLOCKED
        "no_safe_route_without_attempt",    # no_safe_route=true & route_attempted=false
        "destination_null",                 # 목적지 null
        "ambiguous_risk_level",             # 모호한 risk_level
    ]:
        assert name in covered, f"거부 예제 {name} 이 없다"


def test_어느_계약에도_이름만_risk_level인_필드가_없다():
    """AI-10 / 설계서 6.1. 두 위험 축은 항상 필드명으로 구분한다."""
    for path in SCHEMA_DIR.glob("*.schema.json"):
        text = path.read_text(encoding="utf-8")
        schema = json.loads(text)

        def walk(node, where=""):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "properties" and isinstance(value, dict):
                        assert "risk_level" not in value, (
                            f"{path.name} {where} 에 이름만 risk_level 인 필드가 있다. "
                            "ai_risk_level 또는 service_risk_level 을 쓴다."
                        )
                    walk(value, f"{where}/{key}")
            elif isinstance(node, list):
                for item in node:
                    walk(item, where)

        walk(schema)


def test_경로_상태에_행동_UNAVAILABLE을_쓰지_않는다():
    """RT-09 / C-08. 경로 데이터 단절은 DATA_UNAVAILABLE 이다."""
    schema = json.loads((SCHEMA_DIR / "safe_route.schema.json").read_text(encoding="utf-8"))
    statuses = schema["$defs"]["route_status"]["enum"]
    assert "UNAVAILABLE" not in statuses
    assert "DATA_UNAVAILABLE" in statuses


def test_MVP_제외_프로필이_계약에_없다():
    """C-14. WHEELCHAIR·WITH_PET 은 계약 enum 에도 넣지 않는다."""
    for path in SCHEMA_DIR.glob("*.schema.json"):
        text = path.read_text(encoding="utf-8")
        for banned in ('"WHEELCHAIR"', '"WITH_PET"'):
            assert banned not in text, f"{path.name} 에 {banned} 가 남아 있다"


def test_모든_계약이_적어도_하나의_픽스처로_검증된다():
    """죽은 스키마를 만들지 않는다.

    4대 계약 중 하나라도 검사하는 픽스처가 없으면, 그 계약은 있는 척만 하는
    문서가 된다. 실제로 `action_decision` 이 그런 상태였다 - 스키마는 있는데
    어떤 픽스처도 그것으로 검증되지 않았고, 그래서 `official` 블록이
    `official_info` 픽스처를 받지 못하는 것을 아무도 눈치채지 못했다.
    """
    direct = {case.schema for case in discover() if case.expect_valid}

    # 합성 검증으로 덮이는 것도 실제로 검사되고 있다 - errors_for() 가 assess_response
    # 픽스처의 .risk/.route 를 각 스키마로 다시 돌린다. safe_route 가 이 경우다.
    composed = set(COMPOSED_BLOCKS.values()) if "assess_response" in direct else set()

    covered = direct | composed
    missing = [name for name in REQUIRED_CONTRACTS if name not in covered]
    assert not missing, (
        f"검증하는 픽스처가 없는 계약: {missing}. "
        "contracts/fixtures/ 아래에 픽스처를 넣고 validate.discover() 에 규칙을 추가하거나, "
        "AssessResponse 안의 블록이면 COMPOSED_BLOCKS 에 넣는다."
    )


def test_공식정보_픽스처가_ActionDecision_official_에_그대로_들어간다(validators):
    """O-07 회귀 방지.

    `official_0808.json` 의 통제·침수 항목은 `blocks_destination_ids` 로 목적지를
    막는다(O-07). `ActionDecision.official` 이 그 필드를 모르면 김윤후가 값을 채우는
    순간 유진희가 못 받는다. 두 스키마의 `additionalProperties: false` 가 서로를
    거부하지 않는지 **모양이 채워진 상태로** 확인한다.

    여기 쓰는 값은 계약 모양을 확인하려고 지어낸 합성값이며 2022-08-08 의 사실이
    아니다. 실제 값은 `official_0808.json` 에만 들어가고 원출처 확인 전까지 비어 있다.
    """
    shaped = {
        "evacuation_order": True,
        "source": "fixture:shape_probe",
        "alerts": [
            {
                "type": "SYNTHETIC_ALERT",
                "issued_at": "2022-08-08T20:00:00+09:00",
                "cleared_at": None,
                "region": "합성값",
                "source": "합성값 - 원출처 아님",
            }
        ],
        "closures": [
            {
                "kind": "ROAD",
                "geom_ref": "SYNTHETIC-R-001",
                "label": "합성값 - 실제 통제 구간 아님",
                "mode": "BOTH",
                "since": "2022-08-08T20:00:00+09:00",
                "until": None,
                "blocks_destination_ids": ["GN-001"],
            }
        ],
        "confirmed_flooding": [
            {
                "geom_ref": "SYNTHETIC-F-001",
                "label": "합성값 - 실제 침수 지점 아님",
                "observed_at": "2022-08-08T20:10:00+09:00",
                "source": "합성값 - 원출처 아님",
                "blocks_destination_ids": ["GN-002"],
            }
        ],
    }

    official_errors = list(validators["official_info"].iter_errors({
        **shaped, "asof": "2022-08-08T20:00:00+09:00", "verification": "DRAFT_UNVERIFIED",
    }))
    assert official_errors == [], f"official_info 가 자기 모양을 거부한다: {official_errors}"

    base = json.loads(
        (FIXTURE_DIR / "decision" / "DS-S1.action_decision.json").read_text(encoding="utf-8")
    )
    errors = list(validators["action_decision"].iter_errors({**base, "official": shaped}))
    assert errors == [], (
        "official_info 픽스처를 ActionDecision.official 에 넣을 수 없다: "
        + "; ".join(f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors)
    )
