"""픽스처/계약 payload -> RiskSignals 변환 어댑터.

`tests/conftest.py`와 `api/main.py`가 함께 쓴다 - 앱 코드가 테스트 모듈을
import하지 않기 위해 여기 둔다(CLAUDE.md 10절과 같은 원칙: 앱·테스트는
서로의 전용 모듈을 import하지 않는다).
"""

from __future__ import annotations

from services.decision.enums import AiRiskLevel, HazardSign, UserContext
from services.decision.service_risk import RiskSignals


def _driver_value(risk: dict, feature: str) -> float | None:
    """`risk.drivers[]`에서 `feature` 이름으로 값을 찾는다. 없으면 None."""
    for driver in risk.get("drivers", []):
        if driver.get("feature") == feature:
            return driver.get("value")
    return None


def signals_from(payload: dict) -> RiskSignals:
    """AssessResponse 통합 응답을 `RiskSignals`로 그대로 옮긴다.

    픽스처를 정제하지 않고 계약 필드에서 그대로 읽는다. `test_fixture_engine_agreement.py`
    가 이 함수로 데모 픽스처 4개를 검증하고, `api/main.py`가 실제 API 응답 조립에도
    같은 함수를 쓴다 - 어댑터가 두 곳에서 갈라지지 않게 한다.

    `official` 블록은 AssessResponse 최상위 required 목록에 없어 비어 있을 수
    있다 - 그때는 대피 지시 없음·통제 없음으로 취급한다.
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
