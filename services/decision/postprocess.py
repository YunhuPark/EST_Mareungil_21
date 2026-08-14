"""경로 결과 후처리 — 1차 행동과 경로 상태로 최종 행동을 정한다.

여기 있는 것은 **현재 합의가 끝난 규칙 하나뿐**이다.

    MOVE + NO_SAFE_ROUTE -> WAIT

나머지 실패 조합은 `OPEN` 이며 **자동 전이시키지 않는다.** 특히 `EVACUATE` 경로
실패를 `EMERGENCY` 로 바꾸는 규칙은 합의에 포함되지 않았다(C-31). 안전정책이
정해지기 전에 여기에 규칙을 추가하지 않는다 — 추가하려면 먼저
`docs/DECISIONS.md` 의 해당 항목을 닫아야 한다.

순수 함수만 둔다. I/O·HTTP·파일 읽기를 하지 않는다(N-04 재현성).
"""

from __future__ import annotations

from dataclasses import dataclass

from services.decision.enums import Action, Basis, RouteStatus, STATUS_ALLOWED_FOR

#: 확정된 전이. (1차 행동, 경로 상태) -> 최종 행동
CONFIRMED_TRANSITIONS: dict[tuple[Action, RouteStatus], Action] = {
    (Action.MOVE, RouteStatus.NO_SAFE_ROUTE): Action.WAIT,
}

#: OPEN. 최종 행동을 아직 정하지 않은 조합. G2 안전정책 확정 대상이다.
#: 값은 "왜 아직 못 정했는가"이며, 확정되기 전까지 1차 행동을 그대로 둔다.
OPEN_TRANSITIONS: dict[tuple[Action, RouteStatus], str] = {
    (Action.MOVE, RouteStatus.DESTINATION_BLOCKED):
        "OPEN: 목적지 변경 안내 외에 행동을 바꿀지 미정. 안전정책 필요(F-10).",
    (Action.MOVE, RouteStatus.DATA_UNAVAILABLE):
        "OPEN: 경로 판단 불가일 때 MOVE 를 유지할지 미정. 안전정책 필요(F-10).",
    (Action.EVACUATE, RouteStatus.NO_SAFE_POINT):
        "OPEN: 안전거점이 없을 때의 최종 행동 미정. EMERGENCY 로 자동 전환하지 않는다(C-31).",
    (Action.EVACUATE, RouteStatus.NO_SAFE_ROUTE):
        "OPEN: 안전거점까지 경로가 없을 때의 최종 행동 미정. EMERGENCY 로 자동 전환하지 않는다(C-31).",
    (Action.EVACUATE, RouteStatus.DATA_UNAVAILABLE):
        "OPEN: 경로 판단 불가일 때의 최종 행동 미정. 안전정책 필요(C-31).",
}


class ContractViolation(ValueError):
    """계약상 나올 수 없는 (행동, 경로 상태) 조합."""


@dataclass(frozen=True)
class PostprocessResult:
    """후처리 결과.

    Attributes:
        action: UI 에 표시할 최종 행동.
        applied: 확정 전이가 실제로 일어났는지(RT-10).
        open_policy: 이 조합이 아직 OPEN 이면 그 사유, 아니면 None.
            화면과 발표에서 "미결정"으로 표시할 근거가 된다.
        reason: 전이가 일어났을 때 붙일 사유. 없으면 None.
    """

    action: Action
    applied: bool
    open_policy: str | None = None
    reason: tuple[str, str, Basis] | None = None


def apply(primary_action: Action, route_status: RouteStatus) -> PostprocessResult:
    """1차 행동과 경로 상태로 최종 행동을 정한다.

    **정확히 한 번만 호출한다.** 경로 엔진을 재호출하지 않는다(RT-10).

    Raises:
        ContractViolation: `MOVE` + `NO_SAFE_POINT` 처럼 계약상 불가능한 조합.
    """
    allowed = STATUS_ALLOWED_FOR[route_status]
    if primary_action not in allowed:
        raise ContractViolation(
            f"{primary_action} 응답에 {route_status} 가 올 수 없다. "
            f"이 상태가 허용되는 행동: {sorted(a.value for a in allowed)} (RT-13)"
        )

    key = (primary_action, route_status)

    if key in CONFIRMED_TRANSITIONS:
        return PostprocessResult(
            action=CONFIRMED_TRANSITIONS[key],
            applied=True,
            reason=(
                "ROUTE_NO_SAFE_ROUTE",
                "목적지까지 비교한 후보 경로가 모두 제외돼 대기로 바꿨습니다.",
                Basis.TEAM_RULE,
            ),
        )

    return PostprocessResult(
        action=primary_action,
        applied=False,
        open_policy=OPEN_TRANSITIONS.get(key),
    )
