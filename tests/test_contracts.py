"""계약 검증.

`contracts/validate.py` 와 같은 것을 본다. 여기 있는 이유는 `pytest` 한 번으로
계약까지 확인되게 하기 위해서다 — 검증 명령을 두 번 기억하게 만들지 않는다.
"""

from __future__ import annotations

import json

import pytest

from contracts.validate import Case, SCHEMA_DIR, discover, errors_for, load_schemas

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
