"""경로 결과 후처리 정책 테스트.

여기서 지키는 것은 두 가지다.

1. **행동을 바꾸는 규칙은 하나뿐이다** — `MOVE + NO_SAFE_ROUTE → WAIT`(C-01).
2. **나머지 실패 조합은 1차 행동을 유지한다** — 미정이라 그런 것이 아니라
   2026-08-16 회의(M-15·M-16)가 유지하기로 확정했기 때문이다.

둘의 차이가 이 파일의 핵심이다. 예전에는 "OPEN 이라 못 바꾼다"였고 지금은
"바꾸지 않기로 정했다"다. 그래서 유지 조합도 **사유를 반드시 갖는다** —
사유가 없으면 화면이 "왜 그대로인지"를 설명하지 못한다.
"""

from __future__ import annotations

import pytest

from services.decision import Action, ContractViolation, RouteStatus, apply
from services.decision.enums import Basis
from services.decision.postprocess import (
    CONFIRMED_HOLDS,
    CONFIRMED_TRANSITIONS,
    EMPHASIZE_EMERGENCY_CALL,
    SUSPEND_ROUTE_GUIDANCE,
    final_reasons,
    representative_code,
)
from services.decision.service_risk import MAX_REASONS, Reason


def test_MOVE와_NO_SAFE_ROUTE는_WAIT로_바뀐다():
    """F-10 / RT-10 / M-16. 행동이 바뀌는 유일한 후처리."""
    result = apply(Action.MOVE, RouteStatus.NO_SAFE_ROUTE)
    assert result.action is Action.WAIT
    assert result.applied is True
    assert result.reason is not None


def test_행동이_바뀌는_전이는_하나뿐이다():
    """C-01. 늘리려면 먼저 docs/DECISIONS.md 에 근거를 남겨야 한다."""
    assert CONFIRMED_TRANSITIONS == {(Action.MOVE, RouteStatus.NO_SAFE_ROUTE): Action.WAIT}


@pytest.mark.parametrize(
    "status",
    [RouteStatus.NO_SAFE_POINT, RouteStatus.NO_SAFE_ROUTE, RouteStatus.DATA_UNAVAILABLE],
)
def test_EVACUATE_경로실패는_EVACUATE를_유지한다(status):
    """M-15. EMERGENCY 로도 WAIT 으로도 바꾸지 않고 실패 사유만 붙인다."""
    result = apply(Action.EVACUATE, status)
    assert result.action is Action.EVACUATE
    assert result.applied is False
    assert result.reason is not None


@pytest.mark.parametrize(
    "status",
    [RouteStatus.NO_SAFE_POINT, RouteStatus.NO_SAFE_ROUTE, RouteStatus.DATA_UNAVAILABLE],
)
def test_EVACUATE_경로실패는_119를_강조한다(status):
    """M-15. 다만 EMERGENCY 레이아웃으로 승격하지는 않는다."""
    result = apply(Action.EVACUATE, status)
    assert result.emphasize_emergency_call is True
    assert result.action is not Action.EMERGENCY


@pytest.mark.parametrize(
    "status", [RouteStatus.DESTINATION_BLOCKED, RouteStatus.DATA_UNAVAILABLE]
)
def test_MOVE_경로실패는_MOVE를_유지하되_경로안내를_중단한다(status):
    """M-16. MOVE 유지가 '기존 목적지로 계속 가라'는 뜻이 아니다."""
    result = apply(Action.MOVE, status)
    assert result.action is Action.MOVE
    assert result.applied is False
    assert result.reason is not None
    assert result.suspend_route_guidance is True


def test_목적지_차단은_재선택을_안내한다():
    """M-16. 문구를 회의 확정문 그대로 싣는다."""
    result = apply(Action.MOVE, RouteStatus.DESTINATION_BLOCKED)
    code, text, _basis = result.reason
    assert code == "ROUTE_DESTINATION_BLOCKED"
    assert "다른 목적지를 선택" in text


def test_유지_조합과_전이_조합은_겹치지_않는다():
    assert not (set(CONFIRMED_HOLDS) & set(CONFIRMED_TRANSITIONS))


def test_모든_경로실패_조합이_확정_표에_있다():
    """실패 조합을 하나라도 빠뜨리면 사유 없이 조용히 행동만 유지된다.

    이 테스트가 없으면 새 경로 상태가 생겼을 때 아무것도 빨개지지 않는다.
    """
    failures = {
        (Action.MOVE, RouteStatus.NO_SAFE_ROUTE),
        (Action.MOVE, RouteStatus.DESTINATION_BLOCKED),
        (Action.MOVE, RouteStatus.DATA_UNAVAILABLE),
        (Action.EVACUATE, RouteStatus.NO_SAFE_POINT),
        (Action.EVACUATE, RouteStatus.NO_SAFE_ROUTE),
        (Action.EVACUATE, RouteStatus.DATA_UNAVAILABLE),
    }
    covered = set(CONFIRMED_TRANSITIONS) | set(CONFIRMED_HOLDS)
    assert failures <= covered, f"사유가 없는 실패 조합: {failures - covered}"

    for key in failures:
        assert apply(*key).reason is not None


def test_강조와_중단은_실패_조합에서만_켜진다():
    assert EMPHASIZE_EMERGENCY_CALL <= set(CONFIRMED_HOLDS)
    assert SUSPEND_ROUTE_GUIDANCE <= set(CONFIRMED_HOLDS)

    for status in (RouteStatus.FALLBACK_CANDIDATE, RouteStatus.VERIFIED_ROUTE):
        for action in (Action.MOVE, Action.EVACUATE):
            result = apply(action, status)
            assert result.emphasize_emergency_call is False
            assert result.suspend_route_guidance is False


def test_정상_경로는_행동을_유지하고_사유를_붙이지_않는다():
    for status in (RouteStatus.FALLBACK_CANDIDATE, RouteStatus.VERIFIED_ROUTE):
        for action in (Action.MOVE, Action.EVACUATE):
            result = apply(action, status)
            assert result.action is action
            assert result.reason is None


def test_MOVE에_NO_SAFE_POINT는_계약위반이다():
    """RT-13. 안전거점 탐색은 EVACUATE 에만 있다."""
    with pytest.raises(ContractViolation):
        apply(Action.MOVE, RouteStatus.NO_SAFE_POINT)


def test_EVACUATE에_DESTINATION_BLOCKED는_계약위반이다():
    """RT-13. 안전거점은 안전 조건을 통과한 후보만 고른다."""
    with pytest.raises(ContractViolation):
        apply(Action.EVACUATE, RouteStatus.DESTINATION_BLOCKED)


@pytest.mark.parametrize("action", [Action.WAIT, Action.EMERGENCY, Action.UNAVAILABLE])
def test_경로가_필요없는_행동은_NOT_REQUIRED만_받는다(action):
    assert apply(action, RouteStatus.NOT_REQUIRED).action is action
    with pytest.raises(ContractViolation):
        apply(action, RouteStatus.FALLBACK_CANDIDATE)


def test_후처리는_순수함수다():
    """N-04 재현성. 같은 입력이면 항상 같은 출력."""
    first = apply(Action.MOVE, RouteStatus.NO_SAFE_ROUTE)
    second = apply(Action.MOVE, RouteStatus.NO_SAFE_ROUTE)
    assert first == second


# --- 이유 목록 합성 (final_reasons) -------------------------------------------


def _reason(code: str) -> Reason:
    return Reason(code, f"{code} 문구", Basis.TEAM_RULE)


def test_경로_실패가_없으면_이유는_decide_출력_그대로다():
    primary = (_reason("A"), _reason("B"))
    post = apply(Action.MOVE, RouteStatus.FALLBACK_CANDIDATE)

    assert [r.code for r in final_reasons(primary, post)] == ["A", "B"]


def test_경로_실패_사유는_위험_사유_뒤에_붙는다():
    """순서는 픽스처 규약을 따른다 — `DS-S8` 은 `[AI_AREA_HIGH, ROUTE_NO_SAFE_POINT]`."""
    primary = (_reason("AI_AREA_HIGH"),)
    post = apply(Action.EVACUATE, RouteStatus.NO_SAFE_POINT)

    assert [r.code for r in final_reasons(primary, post)] == [
        "AI_AREA_HIGH",
        "ROUTE_NO_SAFE_POINT",
    ]


def test_상한을_넘으면_경로_사유가_살아남는다():
    """**뒤에서 자르면 방금 붙인 사유가 먼저 사라진다.**

    `decide()` 가 사유 3개를 냈는데 경로도 실패한 상황이다. 계약 상한은 3이므로
    하나는 버려야 하는데, 버릴 것은 위험 사유 쪽이다 — 경로 실패는 사용자가 지금
    마주친 것이고 화면 어디에도 다른 표시가 없다.
    """
    primary = (_reason("A"), _reason("B"), _reason("C"))
    post = apply(Action.EVACUATE, RouteStatus.NO_SAFE_POINT)
    codes = [r.code for r in final_reasons(primary, post)]

    assert len(codes) == MAX_REASONS
    assert codes == ["A", "B", "ROUTE_NO_SAFE_POINT"]


def test_같은_사유를_두_번_싣지_않는다():
    primary = (_reason("ROUTE_NO_SAFE_POINT"), _reason("A"))
    post = apply(Action.EVACUATE, RouteStatus.NO_SAFE_POINT)
    codes = [r.code for r in final_reasons(primary, post)]

    assert codes.count("ROUTE_NO_SAFE_POINT") == 1
    assert codes == ["A", "ROUTE_NO_SAFE_POINT"]


def test_대표_사유는_경로_실패가_있으면_그것이다():
    primary = (_reason("A"),)
    assert (
        representative_code(primary, apply(Action.EVACUATE, RouteStatus.NO_SAFE_POINT))
        == "ROUTE_NO_SAFE_POINT"
    )
    assert (
        representative_code(primary, apply(Action.MOVE, RouteStatus.FALLBACK_CANDIDATE))
        == "A"
    )
