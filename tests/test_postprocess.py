"""경로 결과 후처리 정책 테스트.

여기서 지키는 것은 **미확정 정책을 확정하지 않는다**는 원칙이다.
확정된 전이는 하나뿐이고, 나머지는 1차 행동을 그대로 두어야 한다.
"""

from __future__ import annotations

import pytest

from services.decision import Action, ContractViolation, RouteStatus, apply
from services.decision.postprocess import CONFIRMED_TRANSITIONS, OPEN_TRANSITIONS


def test_MOVE와_NO_SAFE_ROUTE는_WAIT로_바뀐다():
    """F-10 / RT-10. 현재 확정된 유일한 후처리."""
    result = apply(Action.MOVE, RouteStatus.NO_SAFE_ROUTE)
    assert result.action is Action.WAIT
    assert result.applied is True
    assert result.reason is not None


def test_확정된_전이는_하나뿐이다():
    """C-31. 규칙을 늘리려면 먼저 docs/DECISIONS.md 의 OPEN 항목을 닫아야 한다."""
    assert CONFIRMED_TRANSITIONS == {(Action.MOVE, RouteStatus.NO_SAFE_ROUTE): Action.WAIT}


@pytest.mark.parametrize(
    "status",
    [RouteStatus.NO_SAFE_POINT, RouteStatus.NO_SAFE_ROUTE, RouteStatus.DATA_UNAVAILABLE],
)
def test_EVACUATE_경로실패는_EMERGENCY로_자동전환되지_않는다(status):
    """C-31. 안전정책 합의 전에 대피 실패를 구조 요청으로 바꾸지 않는다."""
    result = apply(Action.EVACUATE, status)
    assert result.action is Action.EVACUATE
    assert result.applied is False
    assert result.open_policy is not None


@pytest.mark.parametrize(
    "status", [RouteStatus.DESTINATION_BLOCKED, RouteStatus.DATA_UNAVAILABLE]
)
def test_MOVE의_미확정_실패는_행동을_바꾸지_않는다(status):
    result = apply(Action.MOVE, status)
    assert result.action is Action.MOVE
    assert result.applied is False
    assert result.open_policy is not None


def test_OPEN_조합은_확정_조합과_겹치지_않는다():
    assert not (set(OPEN_TRANSITIONS) & set(CONFIRMED_TRANSITIONS))


def test_정상_경로는_행동을_유지한다():
    for status in (RouteStatus.FALLBACK_CANDIDATE, RouteStatus.VERIFIED_ROUTE):
        assert apply(Action.MOVE, status).action is Action.MOVE
        assert apply(Action.EVACUATE, status).action is Action.EVACUATE


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
