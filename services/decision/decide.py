"""행동 판정 — 설계서 9장 우선순위 1~10, 첫 일치가 이긴다 (P0-3).

`classify()` 는 "지금 얼마나 위험한가"를 정하고, 이 모듈은 "지금 무엇을
해야 하는가"를 정한다. 두 축은 1:1 이 아니다 - 같은 입력에서 등급 `SAFE`
와 행동 `WAIT` 이 함께 나올 수 있다(TH-01 이 그 자리다).

    1. trapped=true                                  -> EMERGENCY
    2. UNDERGROUND + hazard_signs >= 1               -> EVACUATE
    3. 범위 밖                                        -> UNAVAILABLE
    4. 공식 대피 지시                                  -> EVACUATE
    5. ai_risk_level=None AND rain_available=False    -> UNAVAILABLE
    6. ai_risk_level=HIGH + OUTDOOR                  -> EVACUATE
    7. ai_risk_level=HIGH + INDOOR                   -> WAIT
    8. ai_risk_level=HIGH + UNDERGROUND + 징후 없음    -> WAIT
    9. TH-01 또는 TH-02 또는 DQ-03 또는 DQ-02         -> WAIT
    10. 그 외                                         -> MOVE

규칙 6~8 은 자료가 30분(EXPIRED_SEC)을 넘겨도 그대로 발화한다 - `classify()`
는 낡은 자료를 등급 축에서 빼지만 행동 축은 다르게 간다. DQ-02(30분 초과)는
규칙 9 뒤의 별도 분기다.

사유 코드는 대부분 `service_risk.py` 가 이미 쓰는 코드를 그대로 재사용한다.
이 모듈에서 새로 만드는 코드는 둘이다.

- `RAIN_10M_OVER_TH01` - TH-01 은 등급 축에 없고 행동 축에만 있다(O-15).
- `NO_TRIGGER` - 규칙 10 기본값. `classify()` 의 SAFE 기본 사유(`NO_DIRECT_SIGNAL`)
  와 의미가 달라 같은 코드를 쓰지 않는다 - `decide()` 는 "걸리는 조건이 없다",
  `classify()` 는 "직접 신호가 없고 AI 도 낮다"이다.

규칙
----
- 순수 함수만 둔다. `datetime.now()` 를 쓰지 않는다. 시각은 입력으로 받는다(N-04).
- `services/route` 를 import 하지 않는다.
- 새 기준값을 만들지 않는다. `RAIN_10M_MM` 은 설계서 9.2 확정값이다.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.decision.enums import NEEDS_ROUTE, Action, AiRiskLevel, Basis, UserContext
from services.decision.service_risk import (
    MAX_REASONS,
    Reason,
    RiskSignals,
    _additional_signals,
    _data_state,
    _direct_signals,
    _quality_reasons,
)

#: TH-01. 최근 10분 강우 기준값(mm). 설계서 9.2 확정값 - 여기서 고른 수가 아니다.
RAIN_10M_MM = 5.0

_AI_AREA_HIGH = Reason(
    "AI_AREA_HIGH",
    "30분 뒤 지역 고수위 위험이 높게 예측됐습니다.",
    Basis.AI_PREDICTION,
)

_NO_TRIGGER = Reason(
    "NO_TRIGGER",
    "행동을 바꿀 조건이 확인되지 않았습니다.",
    Basis.TEAM_RULE,
)


def _th01_reason(signals: RiskSignals) -> Reason:
    return Reason(
        "RAIN_10M_OVER_TH01",
        "최근 10분 누적 강우가 팀 기준값을 넘었습니다.",
        Basis.TEAM_RULE,
        value=signals.rain_past_10m_mm,
        threshold=RAIN_10M_MM,
    )


@dataclass(frozen=True)
class ActionResult:
    """`decide()` 의 결과.

    Attributes:
        action: 1차 행동.
        rule: 1~10, 첫 일치로 이긴 규칙 번호.
        reasons: 이 행동이 나온 이유. 상한은 `MAX_REASONS`.
    """

    action: Action
    rule: int
    reasons: tuple[Reason, ...]

    @property
    def needs_route(self) -> bool:
        """`enums.NEEDS_ROUTE` 에서 파생한다. 손으로 정하지 않는다."""
        return self.action in NEEDS_ROUTE


def decide(signals: RiskSignals) -> ActionResult:
    """설계서 9장 우선순위 1~10. 첫 일치가 이긴다."""
    state = _data_state(signals)
    direct = tuple(_direct_signals(signals)[:MAX_REASONS])

    # 1. 고립 신고 - 다른 모든 신호보다 우선한다.
    if signals.trapped:
        return ActionResult(Action.EMERGENCY, 1, direct)

    # 2. 지하 + 현장 위험징후 - 데이터 단절보다 먼저 판단한다.
    if signals.context is UserContext.UNDERGROUND and signals.hazard_signs:
        return ActionResult(Action.EVACUATE, 2, direct)

    # 3. 서비스 범위 밖.
    if not signals.in_service_area:
        quality = tuple(_quality_reasons(state)[:MAX_REASONS])
        return ActionResult(Action.UNAVAILABLE, 3, quality)

    # 4. 공식 대피 지시 - 내부 데이터와 독립이다.
    if signals.evacuation_order:
        return ActionResult(Action.EVACUATE, 4, direct)

    # 5. AI 와 강우가 동시에 결측 - AND 다. 하나만 없으면 규칙 10 으로 떨어진다.
    if state.ai_unavailable and state.rain_unavailable:
        quality = tuple(_quality_reasons(state)[:MAX_REASONS])
        return ActionResult(Action.UNAVAILABLE, 5, quality)

    # 6~8. AI HIGH - 자료가 30분을 넘겨도 그대로 발화한다(등급 축과 다름).
    if signals.ai_risk_level is AiRiskLevel.HIGH:
        reasons = (_AI_AREA_HIGH,)
        if signals.context is UserContext.OUTDOOR:
            return ActionResult(Action.EVACUATE, 6, reasons)
        if signals.context is UserContext.INDOOR:
            return ActionResult(Action.WAIT, 7, reasons)
        # UNDERGROUND. 현장 징후가 있었다면 규칙 2 에서 이미 걸렸을 것이다.
        return ActionResult(Action.WAIT, 8, reasons)

    # 9. TH-01 OR TH-02 OR DQ-03(관측률) OR DQ-02(30분 초과 지연).
    th01 = (
        signals.rain_past_10m_mm is not None
        and signals.rain_past_10m_mm >= RAIN_10M_MM
    )
    th02 = tuple(_additional_signals(signals))
    quality = _quality_reasons(state)
    quality_low = next((r for r in quality if r.code == "DATA_QUALITY_LOW"), None)
    expired = next((r for r in quality if r.code == "DATA_EXPIRED"), None)

    if th01 or th02 or quality_low or expired:
        reasons: list[Reason] = []
        if th01:
            reasons.append(_th01_reason(signals))
        reasons.extend(th02)
        if quality_low:
            reasons.append(quality_low)
        if expired:
            reasons.append(expired)
        return ActionResult(Action.WAIT, 9, tuple(reasons[:MAX_REASONS]))

    # 10. 그 외 - DQ-01(10분 초과만인 지연)도 여기로 떨어진다. 행동을 바꾸지 않는다.
    return ActionResult(Action.MOVE, 10, (_NO_TRIGGER,))
