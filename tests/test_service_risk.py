"""서비스 위험 등급 판정 (C-23).

여기서 지키는 것은 셋이다.

1. 네 등급의 판정 기준이 문서와 같은가.
2. **등급과 행동을 1:1 로 잇지 않았는가** — 같은 등급에 여러 행동이 온다는 사실이
   코드에서도 성립해야 한다.
3. `DATA_UNAVAILABLE` 이 등급 축에 새어 들어오지 않았는가.
"""

from __future__ import annotations

import itertools

import pytest

from services.decision.enums import AiRiskLevel, Basis, HazardSign, ServiceRiskLevel, UserContext
from services.decision.service_risk import (
    EXPIRED_SEC,
    MAX_REASONS,
    OBSERVED_RATE_MIN,
    OPEN_ADDITIONAL_SIGNALS,
    RAIN_60M_MM,
    STALE_SEC,
    RiskSignals,
    classify,
)

#: 데이터가 전부 정상인 기준 입력. 각 테스트는 여기서 한 축만 바꾼다.
CLEAN = RiskSignals(
    context=UserContext.OUTDOOR,
    ai_risk_level=AiRiskLevel.LOW,
    official_present=True,
    observed_rate=1.0,
    rain_available=True,
    rain_past_60m_mm=0.0,
    data_age_sec=0,
)


# --- SAFE --------------------------------------------------------------------


def test_직접신호_없고_AI_LOW_이고_데이터_정상이면_SAFE():
    assert classify(CLEAN).level is ServiceRiskLevel.SAFE


def test_SAFE_는_데이터가_하나라도_비정상이면_나오지_않는다():
    """'판단할 근거가 없다'를 '안전하다'로 말하지 않는다."""
    degraded = [
        {"ai_risk_level": None},
        {"data_age_sec": STALE_SEC + 1},
        {"observed_rate": OBSERVED_RATE_MIN - 0.01},
        {"rain_available": False},
        {"in_service_area": False},
    ]
    for change in degraded:
        result = classify(RiskSignals(**{**vars(CLEAN), **change}))
        assert result.level is ServiceRiskLevel.CAUTION, change
        assert result.data_state.degraded, change


# --- CAUTION -----------------------------------------------------------------


def test_AI_HIGH_단독이면_CAUTION():
    """추가 위험신호가 없으면 DANGER 로 올리지 않는다."""
    result = classify(RiskSignals(**{**vars(CLEAN), "ai_risk_level": AiRiskLevel.HIGH}))
    assert result.level is ServiceRiskLevel.CAUTION


def test_AI_LOW_인데_강우가_기준을_넘으면_CAUTION():
    """복합 위험은 아니지만 안전이라고 말하지도 않는다.

    같은 신호가 행동 우선순위 9 에서 `WAIT` 을 만든다. 행동은 대기인데 등급은
    안전이라고 적히면 화면의 두 줄이 서로를 부정한다.
    """
    result = classify(RiskSignals(**{**vars(CLEAN), "rain_past_60m_mm": RAIN_60M_MM}))
    assert result.level is ServiceRiskLevel.CAUTION


# --- DANGER ------------------------------------------------------------------


def test_AI_HIGH_에_강우가_겹치면_DANGER():
    result = classify(
        RiskSignals(
            **{
                **vars(CLEAN),
                "ai_risk_level": AiRiskLevel.HIGH,
                "rain_past_60m_mm": RAIN_60M_MM,
            }
        )
    )
    assert result.level is ServiceRiskLevel.DANGER
    assert {r.code for r in result.reasons} >= {"AI_AREA_HIGH", "RAIN_60M_OVER_TH02"}


def test_DANGER_판정에는_미확정_사유가_함께_실린다():
    """O-15. 추가 위험신호 집합이 아직 확정 전이라는 사실을 숨기지 않는다."""
    result = classify(RiskSignals(**{**vars(CLEAN), "ai_risk_level": AiRiskLevel.HIGH}))
    assert set(result.open_policy) == set(OPEN_ADDITIONAL_SIGNALS.values())
    assert all(text.startswith("OPEN(O-15)") for text in result.open_policy)


def test_강우_기준값은_설계서_9_2_의_확정값을_그대로_쓴다():
    """새 수를 만들지 않았는지 본다(CLAUDE.md 9절)."""
    assert RAIN_60M_MM == 40.0     # TH-02
    assert STALE_SEC == 600        # DQ-01
    assert OBSERVED_RATE_MIN == 0.70  # DQ-03


# --- SEVERE ------------------------------------------------------------------


@pytest.mark.parametrize(
    "change,expected_code",
    [
        ({"trapped": True}, "TRAPPED_REPORTED"),
        (
            {
                "context": UserContext.UNDERGROUND,
                "hazard_signs": (HazardSign.WATER_INFLOW,),
            },
            "UNDERGROUND_HAZARD_SIGN",
        ),
        ({"evacuation_order": True}, "OFFICIAL_EVACUATION_ORDER"),
    ],
    ids=["고립", "지하+징후", "공식대피지시"],
)
def test_직접_안전신호_셋이_각각_SEVERE_를_만든다(change, expected_code):
    result = classify(RiskSignals(**{**vars(CLEAN), **change}))
    assert result.level is ServiceRiskLevel.SEVERE
    assert expected_code in {r.code for r in result.reasons}


def test_AI_는_SEVERE_를_만들_수_없다():
    """F-02. 확률이 아무리 높아도, 강우가 겹쳐도 SEVERE 가 되지 않는다."""
    result = classify(
        RiskSignals(
            **{
                **vars(CLEAN),
                "ai_risk_level": AiRiskLevel.HIGH,
                "rain_past_60m_mm": 999.0,
            }
        )
    )
    assert result.level is ServiceRiskLevel.DANGER


def test_지하여도_징후가_없으면_SEVERE_가_아니다():
    result = classify(RiskSignals(**{**vars(CLEAN), "context": UserContext.UNDERGROUND}))
    assert result.level is ServiceRiskLevel.SAFE


def test_징후가_있어도_지하가_아니면_SEVERE_가_아니다():
    """hazard_signs 는 context=UNDERGROUND 일 때만 의미가 있다(계약 description)."""
    result = classify(
        RiskSignals(
            **{
                **vars(CLEAN),
                "context": UserContext.INDOOR,
                "hazard_signs": (HazardSign.SEWER_BACKFLOW,),
            }
        )
    )
    assert result.level is ServiceRiskLevel.SAFE


def test_직접신호는_AI_가_없어도_그대로_적용된다():
    """DATA_UNAVAILABLE 이 공식 대피 지시·고립을 덮지 않는다."""
    for change in [{"trapped": True}, {"evacuation_order": True}]:
        result = classify(
            RiskSignals(
                **{
                    **vars(CLEAN),
                    "ai_risk_level": None,
                    "rain_available": False,
                    "in_service_area": False,
                    **change,
                }
            )
        )
        assert result.level is ServiceRiskLevel.SEVERE, change


# --- 공식정보가 등급을 낮추지 못한다 -----------------------------------------


def test_경보_해제만으로_등급이_내려가지_않는다():
    """F-14. 공식 해제는 AI 위험을 낮추는 근거가 아니다."""
    high = RiskSignals(**{**vars(CLEAN), "ai_risk_level": AiRiskLevel.HIGH})
    cleared = RiskSignals(**{**vars(high), "alerts_all_cleared": True})
    assert classify(cleared).level is classify(high).level


def test_도로_통제는_등급을_올리지_않는다():
    """RT-11. 통제는 경로 후보에서 구간을 빼는 데만 쓴다."""
    with_closures = RiskSignals(**{**vars(CLEAN), "closure_count": 5})
    assert classify(with_closures).level is classify(CLEAN).level


def test_공식정보_부재는_등급을_올리지_않는다():
    """의도한 선택이다. 빠뜨린 것이 아니다.

    '공식 대피 지시가 없다'와 '공식정보를 못 받았다'는 다른 상태지만, 후자를
    주의 신호로 올리려면 그렇게 정한 근거가 있어야 한다. 지금은 없다(CLAUDE.md 9절).
    """
    absent = RiskSignals(**{**vars(CLEAN), "official_present": False})
    assert classify(absent).level is ServiceRiskLevel.SAFE
    assert not classify(absent).data_state.degraded


# --- 두 축이 1:1 이 아니다 ---------------------------------------------------


def test_같은_등급에_실내_실외_지하가_모두_올_수_있다():
    """등급은 사용자 위치를 보지 않는다.

    이것이 성립해야 "같은 DANGER 라도 실내면 WAIT, 실외면 EVACUATE" 가 성립한다.
    등급이 위치를 흡수해버리면 행동을 따로 낼 이유가 없어진다.
    """
    for context in UserContext:
        result = classify(
            RiskSignals(
                **{
                    **vars(CLEAN),
                    "context": context,
                    "ai_risk_level": AiRiskLevel.HIGH,
                    "rain_past_60m_mm": RAIN_60M_MM,
                }
            )
        )
        assert result.level is ServiceRiskLevel.DANGER, context


def test_등급은_목적지나_경로_상태를_입력으로_받지_않는다():
    """RiskSignals 에 경로 축이 새어 들어오면 두 축이 다시 붙는다."""
    banned = {"route", "destination", "action", "safe_point"}
    fields = set(vars(CLEAN))
    assert not any(any(b in f for b in banned) for f in fields), fields


# --- 계약과의 접점 -----------------------------------------------------------


def test_사유는_계약_상한을_넘지_않는다():
    """F-03. 모든 조합에서 reasons 가 3개를 넘지 않고 1개 이상이다."""
    axes = itertools.product(
        UserContext,
        [None, AiRiskLevel.LOW, AiRiskLevel.HIGH],
        [True, False],   # trapped
        [True, False],   # evacuation_order
        [0.0, RAIN_60M_MM],
        [True, False],   # in_service_area
    )
    for context, ai, trapped, order, rain, in_area in axes:
        result = classify(
            RiskSignals(
                context=context,
                ai_risk_level=ai,
                trapped=trapped,
                hazard_signs=(HazardSign.STAIR_INFLOW,),
                evacuation_order=order,
                official_present=True,
                observed_rate=0.5,
                rain_available=False,
                rain_past_60m_mm=rain,
                data_age_sec=STALE_SEC + 1,
                in_service_area=in_area,
            )
        )
        assert 1 <= len(result.reasons) <= MAX_REASONS
        assert all(isinstance(r.basis, Basis) for r in result.reasons)


def test_계약_JSON_의_맨_문자열도_그대로_받는다():
    """hazard_signs 는 API 에서 `["WATER_INFLOW"]` 형태로 온다.

    HazardSign 이 StrEnum 이라 비교는 통과하지만 `.value` 를 부르면 깨진다.
    호출부가 매번 enum 으로 변환하게 만들지 않는다.
    """
    result = classify(
        RiskSignals(
            **{
                **vars(CLEAN),
                "context": UserContext.UNDERGROUND,
                "hazard_signs": ("WATER_INFLOW", "STAIR_INFLOW"),
            }
        )
    )
    assert result.level is ServiceRiskLevel.SEVERE
    assert result.reasons[0].value == "WATER_INFLOW, STAIR_INFLOW"


# --- M-08. 30분 초과 자료 제외 ------------------------------------------------
#
# "제외한다"가 "안전해졌다"로 새지 않는지가 이 묶음의 전부다.


def test_30분_초과는_지연이면서_제외다():
    """두 단계는 포함 관계다. 30분을 넘겼는데 지연이 아닐 수는 없다."""
    result = classify(RiskSignals(**{**vars(CLEAN), "data_age_sec": EXPIRED_SEC + 1}))
    assert result.data_state.delayed is True
    assert result.data_state.expired is True
    assert EXPIRED_SEC > STALE_SEC


def test_10분과_30분_사이는_제외가_아니다():
    """M-08 이 20분 단계를 삭제했으므로 그 사이에는 아무 일도 일어나지 않는다."""
    result = classify(RiskSignals(**{**vars(CLEAN), "data_age_sec": 1200}))
    assert result.data_state.delayed is True
    assert result.data_state.expired is False
    assert [r.code for r in result.reasons] == ["DATA_DELAYED"]


def test_제외해도_SAFE로_내려가지_않는다():
    """자료를 뺐다는 것이 '위험이 없다'는 뜻이 되면 안 된다."""
    result = classify(RiskSignals(**{**vars(CLEAN), "data_age_sec": EXPIRED_SEC + 1}))
    assert result.level is ServiceRiskLevel.CAUTION
    assert "DATA_EXPIRED" in [r.code for r in result.reasons]


def test_제외되면_DANGER를_만들지_않는다():
    """30분 지난 자료로 '복합 위험이 지금 있다'고 말하지 않는다.

    같은 입력에서 경과시간만 0 이면 DANGER 다 — 아래 두 줄이 그것을 함께 보인다.
    """
    hot = {
        **vars(CLEAN),
        "ai_risk_level": AiRiskLevel.HIGH,
        "rain_past_60m_mm": RAIN_60M_MM + 10,
    }
    assert classify(RiskSignals(**hot)).level is ServiceRiskLevel.DANGER
    stale = classify(RiskSignals(**{**hot, "data_age_sec": EXPIRED_SEC + 1}))
    assert stale.level is ServiceRiskLevel.CAUTION


@pytest.mark.parametrize(
    "overrides",
    [
        {"trapped": True},
        {"context": UserContext.UNDERGROUND, "hazard_signs": (HazardSign.WATER_INFLOW,)},
        {"evacuation_order": True},
    ],
    ids=["고립신고", "지하+현장징후", "공식대피지시"],
)
def test_자료가_낡아도_직접신호는_그대로_SEVERE다(overrides):
    """낡은 것은 내부 관측 자료이지 자기신고나 공식 지시가 아니다."""
    result = classify(
        RiskSignals(**{**vars(CLEAN), "data_age_sec": EXPIRED_SEC + 1, **overrides})
    )
    assert result.level is ServiceRiskLevel.SEVERE


def test_지연과_제외_사유를_동시에_싣지_않는다():
    """F-03. 3줄 상한 안에서 같은 축을 두 번 쓰면 다른 사유가 밀려난다."""
    codes = [
        r.code
        for r in classify(
            RiskSignals(**{**vars(CLEAN), "data_age_sec": EXPIRED_SEC + 1})
        ).reasons
    ]
    assert "DATA_EXPIRED" in codes
    assert "DATA_DELAYED" not in codes


def test_판정은_순수하다():
    """N-04. 같은 입력이면 항상 같은 출력이다."""
    signals = RiskSignals(**{**vars(CLEAN), "ai_risk_level": AiRiskLevel.HIGH})
    assert classify(signals) == classify(signals)
