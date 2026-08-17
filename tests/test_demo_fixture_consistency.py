"""데모 픽스처의 STUB 값이 실제 판정 코드와 어긋나지 않는지 확인한다 (C-28).

왜 이 파일이 생겼나
-------------------
`DS-S1`·`DS-S6` 이 `service_risk_level: "SAFE"` 를 싣고 있었는데 같은 입력으로
`classify()` 를 돌리면 `CAUTION` 이 나왔다. `observed_rate` 가 임계 아래라
`quality_low` 가 켜졌기 때문이다(O-16 → C-28).

**어떤 검사도 이것을 잡지 못했다.** 계약 검증은 스키마 모양만 보고, `test_service_risk.py`
는 손으로 만든 입력으로 `classify()` 를 부른다. 픽스처가 그 함수를 통과한 값인지
**아무도 대조하지 않았다.** 픽스처의 `decision` 블록은 판단 엔진 구현 전에 손으로 채운
STUB 이고(`_stub` 필드에 그렇게 적혀 있다), 그래서 조용히 어긋날 수 있는 자리였다.

`CLAUDE.md` 8절 — "새로 만드는 보장에는 이것을 깨뜨리면 무엇이 빨개지는가를 답한다".
이 파일이 그 답이다. 저장소에서 같은 종류의 사고가 세 번 있었고(C-12·C-21·enum 사본)
이번이 네 번째다.

무엇을 검사하고 무엇을 검사하지 않나
------------------------------------
검사한다 — **등급 축**(`service_risk_level`)이 `classify()` 의 출력과 같은가.

검사하지 않는다 — **행동 축**(`action`). 행동 판정 본체가 아직 없다(DQ-01~05 미구현,
`REPOSITORY_AUDIT.md` 6절). 없는 것을 있다고 검사할 수는 없으므로, 구현되면 여기에
같은 모양으로 더한다. 그때까지 `action` 은 STUB 로 남는다.

원본 데이터(7.5GB)를 필요로 하지 않는다. 픽스처만 읽는다 — 그래야 팀원 전원이 돌릴 수 있다.
"""

from __future__ import annotations

import json

import pytest

from services.decision.enums import AiRiskLevel, HazardSign, ServiceRiskLevel, UserContext
from services.decision.service_risk import RiskSignals, classify

#: 등급 축을 검사할 통합 응답 픽스처. 새 DS-* 를 만들면 여기 더한다.
DEMO_FIXTURES = ["DS-S1", "DS-S6", "DS-S7", "DS-S8"]


def load(root, name: str) -> dict:
    path = root / "contracts" / "fixtures" / "demo" / f"{name}.assess_response.json"
    return json.loads(path.read_text(encoding="utf-8"))


def signals_from(payload: dict) -> RiskSignals:
    """`AssessResponse` 를 `classify()` 입력으로 옮긴다.

    출처는 `service_risk.RiskSignals` 문서화 표와 같다. **여기서 값을 정제하지 않는다** —
    정제하면 "픽스처를 그대로 받는다"가 아니라 "정제하면 통과한다"를 증명하게 된다(C-21).
    """
    decision = payload["decision"]
    user_state = decision["user_state"]
    official = payload.get("official") or {}
    risk = payload["risk"]
    drivers = {d["feature"]: d["value"] for d in risk.get("drivers", [])}
    ai_level = risk["area_risk"].get("ai_risk_level")

    return RiskSignals(
        context=UserContext(user_state["context"]),
        trapped=user_state.get("trapped", False),
        hazard_signs=tuple(HazardSign(h) for h in user_state.get("hazard_signs") or ()),
        official_present=bool(official),
        evacuation_order=any(
            a.get("kind") == "EVACUATION_ORDER" for a in official.get("alerts", [])
        ),
        closure_count=len(official.get("closures", [])),
        ai_risk_level=AiRiskLevel(ai_level) if ai_level is not None else None,
        data_age_sec=payload["clock"].get("data_age_sec") or 0,
        observed_rate=risk["data_quality"]["observed_rate"],
        rain_available=risk["data_quality"]["rain_available"],
        rain_past_60m_mm=drivers.get("rain_past_60m_mm"),
        in_service_area=payload["location"].get("in_service_area", True),
    )


@pytest.mark.parametrize("name", DEMO_FIXTURES)
def test_데모_픽스처의_등급이_classify_출력과_같다(root, name):
    """STUB 으로 손으로 적은 등급이 실제 판정 코드와 어긋나지 않아야 한다.

    깨뜨리는 법: 픽스처의 `service_risk_level` 이나 `data_quality.observed_rate` 를
    바꾸면 여기가 빨개진다. 실제로 C-28 이전에는 `DS-S1`·`DS-S6` 이 이 검사에 걸렸다.
    """
    payload = load(root, name)
    expected = payload["decision"]["service_risk_level"]
    actual = classify(signals_from(payload)).level

    assert actual is ServiceRiskLevel(expected), (
        f"{name}: 픽스처는 {expected} 인데 classify() 는 {actual.value} 를 낸다. "
        f"observed_rate={payload['risk']['data_quality']['observed_rate']} · "
        f"ai_risk_level={payload['risk']['area_risk'].get('ai_risk_level')}"
    )


@pytest.mark.parametrize("name", DEMO_FIXTURES)
def test_데모_픽스처는_품질_저하_상태가_아니다(root, name):
    """DQ-03 을 포함한 데이터 상태가 전부 정상이어야 한다 (C-28).

    이것이 따로 있는 이유: 위 검사만 있으면 등급이 우연히 맞는 경우를 통과시킨다.
    `DS-S7`·`DS-S8` 은 `quality_low` 가 켜져도 `DANGER` 라서 등급만으로는 안 갈린다.
    실제로 C-28 이전에 두 픽스처는 등급이 맞으면서 `DATA_QUALITY_LOW` 사유가 빠져
    있었다 — 화면이 품질 저하 사실을 숨기는 상태였다.
    """
    state = classify(signals_from(load(root, name))).data_state
    assert not state.degraded, f"{name}: 데이터 상태가 정상이 아니다 — {state}"


@pytest.mark.parametrize("name", DEMO_FIXTURES)
def test_데모_픽스처의_관측률이_DQ_03_임계_위에_있다(root, name):
    """C-28 이 고친 바로 그 값. 임계 자체는 `test_service_risk.py` 가 고정한다."""
    from services.decision.service_risk import OBSERVED_RATE_MIN

    rate = load(root, name)["risk"]["data_quality"]["observed_rate"]
    assert rate >= OBSERVED_RATE_MIN, (
        f"{name}: observed_rate={rate} 가 DQ-03 임계 {OBSERVED_RATE_MIN} 아래다. "
        "픽스처를 다시 만들려면 scripts/refresh_observed_rate.py 를 쓴다."
    )
