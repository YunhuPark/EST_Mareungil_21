"""테스트 공통 설정."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.decision.decide import decide as _decide
from services.decision.enums import AiRiskLevel, HazardSign, UserContext
from services.decision.service_risk import RiskSignals

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def ds_s1() -> dict:
    """DS-S1 통합 데모 응답. 수직 슬라이스가 실제로 쓰는 픽스처다."""
    path = ROOT / "contracts" / "fixtures" / "demo" / "DS-S1.assess_response.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def decide():
    """`decide()` 함수 자체를 픽스처로 노출한다.

    `test_decide.py`가 이 픽스처를 파라미터로 받아서 쓴다. 상태 없는 순수
    함수라 세션 스코프로 캐싱할 필요는 없다.
    """
    return _decide


def load(root: Path, name: str) -> dict:
    """데모 통합 응답 픽스처를 이름으로 읽는다.

    예: `load(root, "DS-S7")` -> `contracts/fixtures/demo/DS-S7.assess_response.json`.
    """
    path = root / "contracts" / "fixtures" / "demo" / f"{name}.assess_response.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _driver_value(risk: dict, feature: str) -> float | None:
    """`risk.drivers[]`에서 `feature` 이름으로 값을 찾는다. 없으면 None."""
    for driver in risk.get("drivers", []):
        if driver.get("feature") == feature:
            return driver.get("value")
    return None


def signals_from(payload: dict) -> RiskSignals:
    """AssessResponse 통합 픽스처를 `RiskSignals` 로 그대로 옮긴다.

    픽스처를 정제하지 않고 계약 필드에서 그대로 읽는다 - `decide()` 를
    실제 데모 픽스처로 검증하는 `test_fixture_engine_agreement.py` 의
    핵심 어댑터다.

    `official` 블록은 AssessResponse 최상위 required 목록에 없어 비어 있을
    수 있다 - 그때는 대피 지시 없음·통제 없음으로 취급한다.
    """
    clock = payload["clock"]
    location = payload["location"]
    risk = payload["risk"]
    user_state = payload["decision"]["user_state"]
    official = payload.get("official", {})

    ai_level = risk["area_risk"].get("ai_risk_level")
    data_quality = risk["data_quality"]
    alerts = official.get("alerts", [])

    return RiskSignals(
        context=UserContext(user_state["context"]),
        trapped=user_state["trapped"],
        hazard_signs=tuple(HazardSign(sign) for sign in user_state["hazard_signs"]),
        official_present="official" in payload,
        evacuation_order=official.get("evacuation_order", False),
        closure_count=len(official.get("closures", [])),
        alerts_all_cleared=bool(alerts) and all(a.get("cleared_at") is not None for a in alerts),
        ai_risk_level=AiRiskLevel(ai_level) if ai_level is not None else None,
        data_age_sec=clock["data_age_sec"],
        observed_rate=data_quality.get("observed_rate"),
        rain_available=data_quality.get("rain_available", True),
        rain_past_60m_mm=_driver_value(risk, "rain_past_60m_mm"),
        rain_past_10m_mm=_driver_value(risk, "rain_past_10m_mm"),
        in_service_area=location["in_service_area"],
    )
