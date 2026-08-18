"""경로 결과 후처리 — 1차 행동과 경로 상태로 최종 행동을 정한다.

**행동을 바꾸는 규칙은 하나뿐이다.**

    MOVE + NO_SAFE_ROUTE -> WAIT

나머지 경로 실패 조합은 **1차 행동을 그대로 유지하고 실패 사유만 붙인다.**
2026-08-16 최종 회의(M-15·M-16, `docs/DECISIONS.md` 2.3)가 전원 합의로 확정한
내용이며, 그 전까지 `OPEN` 이던 다섯 조합이 여기서 닫혔다.

유지가 왜 확정 규칙인가
-----------------------
"아직 안 정해서 그대로 둔다"와 "그대로 두기로 정했다"는 다르다. 후자는

- `EVACUATE` 를 경로 사유로 `WAIT` 이나 `EMERGENCY` 로 **바꾸지 않겠다**는 약속이고,
- 서비스가 아는 것("대피해야 한다")과 모르는 것("어디로")을 **분리해 말하겠다**는 뜻이다.

`EMERGENCY` 자동 전환은 여전히 금지다(C-31·M-15). 실제 고립 신고만 `EMERGENCY` 로 간다.

순수 함수만 둔다. I/O·HTTP·파일 읽기를 하지 않는다(N-04 재현성).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from services.decision.enums import Action, Basis, RouteStatus, STATUS_ALLOWED_FOR
from services.decision.service_risk import MAX_REASONS, Reason

#: 확정된 전이. (1차 행동, 경로 상태) -> 최종 행동.
#: **행동이 바뀌는 유일한 규칙**이며 여기 늘어나면 C-01 이 깨진다.
CONFIRMED_TRANSITIONS: dict[tuple[Action, RouteStatus], Action] = {
    (Action.MOVE, RouteStatus.NO_SAFE_ROUTE): Action.WAIT,
}

#: 확정된 유지. (1차 행동, 경로 상태) -> 사유 (code, text, basis).
#: 행동은 1차 행동 그대로이고 실패 사유만 표시한다(M-15·M-16).
#: 문구는 회의 확정문을 그대로 옮긴 것이며 임의로 바꾸지 않는다.
CONFIRMED_HOLDS: dict[tuple[Action, RouteStatus], tuple[str, str, Basis]] = {
    (Action.MOVE, RouteStatus.DESTINATION_BLOCKED): (
        "ROUTE_DESTINATION_BLOCKED",
        "현재 목적지는 이용할 수 없습니다. 다른 목적지를 선택해 주세요.",
        # 차단 근거는 공식 통제·확인 침수뿐이다(M-16 / O-07). 좌표 거리로 추정하지 않는다.
        Basis.OFFICIAL_GUIDANCE,
    ),
    (Action.MOVE, RouteStatus.DATA_UNAVAILABLE): (
        "ROUTE_DATA_UNAVAILABLE",
        "경로를 판단할 자료가 없어 경로 안내를 제공하지 않습니다.",
        Basis.TEAM_RULE,
    ),
    (Action.EVACUATE, RouteStatus.NO_SAFE_POINT): (
        "ROUTE_NO_SAFE_POINT",
        "안내할 수 있는 안전거점이 없습니다.",
        Basis.TEAM_RULE,
    ),
    (Action.EVACUATE, RouteStatus.NO_SAFE_ROUTE): (
        "ROUTE_NO_SAFE_ROUTE_EVACUATE",
        "안전거점까지 허용 가능한 후보 경로가 없습니다.",
        Basis.TEAM_RULE,
    ),
    (Action.EVACUATE, RouteStatus.DATA_UNAVAILABLE): (
        "ROUTE_DATA_UNAVAILABLE",
        "데이터가 부족해 경로 존재 여부를 판단할 수 없습니다.",
        Basis.TEAM_RULE,
    ),
}

#: M-15. `EVACUATE` 인데 갈 곳·길·근거가 없는 상태. 119 를 강조한다.
#: **`EMERGENCY` 레이아웃으로 바꾸지 않는다** - 강조는 안내 문구 한 줄이다.
EMPHASIZE_EMERGENCY_CALL: frozenset[tuple[Action, RouteStatus]] = frozenset(
    {
        (Action.EVACUATE, RouteStatus.NO_SAFE_POINT),
        (Action.EVACUATE, RouteStatus.NO_SAFE_ROUTE),
        (Action.EVACUATE, RouteStatus.DATA_UNAVAILABLE),
    }
)

#: M-16. 행동은 유지하지만 **기존 경로안내를 중단**해야 하는 상태.
#: `MOVE` 를 유지하는 것이 "기존 목적지로 계속 가라"는 뜻이 아니라는 회의 문장이 근거다.
SUSPEND_ROUTE_GUIDANCE: frozenset[tuple[Action, RouteStatus]] = frozenset(
    {
        (Action.MOVE, RouteStatus.DESTINATION_BLOCKED),
        (Action.MOVE, RouteStatus.DATA_UNAVAILABLE),
    }
)


class ContractViolation(ValueError):
    """계약상 나올 수 없는 (행동, 경로 상태) 조합."""


@dataclass(frozen=True)
class PostprocessResult:
    """후처리 결과.

    Attributes:
        action: UI 에 표시할 최종 행동.
        applied: **행동이 실제로 바뀌었는지**(RT-10). 유지 규칙에서는 False 다 —
            확정 규칙을 적용했다는 것과 행동이 바뀌었다는 것은 다르다.
        reason: 붙일 사유. 전이든 유지든 실패 조합이면 항상 있다.
        emphasize_emergency_call: 119 를 강조할지(M-15). 레이아웃은 바꾸지 않는다.
        suspend_route_guidance: 기존 경로안내를 중단할지(M-16).
        open_policy: 아직 확정되지 않은 조합이면 그 사유. **지금은 항상 None 이며**
            새 경로 상태가 생겨 확정 표에 없을 때만 채워진다.
    """

    action: Action
    applied: bool
    open_policy: str | None = None
    reason: tuple[str, str, Basis] | None = None
    emphasize_emergency_call: bool = False
    suspend_route_guidance: bool = False


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
                "안전이 확인되지 않은 경로로 이동하지 마세요.",
                Basis.TEAM_RULE,
            ),
        )

    if key in CONFIRMED_HOLDS:
        return PostprocessResult(
            action=primary_action,
            applied=False,
            reason=CONFIRMED_HOLDS[key],
            emphasize_emergency_call=key in EMPHASIZE_EMERGENCY_CALL,
            suspend_route_guidance=key in SUSPEND_ROUTE_GUIDANCE,
        )

    return PostprocessResult(action=primary_action, applied=False)


def representative_code(primary_reasons: Sequence[Reason], post: PostprocessResult) -> str:
    """화면 상단·전환 배너에 찍히는 대표 사유 코드.

    경로 실패가 있으면 그것이 대표다 — 사용자가 지금 마주친 것이 그것이기 때문이다.
    실패가 없으면 행동을 만든 규칙의 사유가 대표다.

    **`api/main.py` 와 테스트가 같은 함수를 통과한다**(C-21). 예전에는 이 규칙이
    두 곳에 각각 적혀 있었고, 한쪽만 고치면 "픽스처와 맞다"가 조용히 거짓이 된다.
    """
    if post.reason is not None:
        return post.reason[0]
    return primary_reasons[0].code


def final_reasons(
    primary_reasons: Sequence[Reason], post: PostprocessResult
) -> tuple[Reason, ...]:
    """화면의 "판단 이유" 목록에 실릴 최종 사유들.

    `decide()` 의 사유 뒤에 **경로 실패 사유를 붙인다.** 붙이지 않으면 화면이
    자기 모순을 말한다 - `DS-S6` 에서 경로 카드는 "목적지 차단"을 띄우는데
    이유 목록은 "행동을 바꿀 조건이 확인되지 않았습니다"만 보여줬다. 대표 사유
    (`reason_code`)는 계약 필드일 뿐 화면에 렌더되지 않으므로(`ReasonList` 는
    `reasons` 만 읽는다) 실패 사유가 목록에 없으면 사용자에게 도달하지 않는다.

    순서는 픽스처 규약을 따른다 - 위험 사유가 먼저고 경로 실패가 뒤다
    (`DS-S6` 은 `[AI_AREA_LOW, ROUTE_DESTINATION_BLOCKED]`,
    `DS-S8` 은 `[AI_AREA_HIGH, ROUTE_NO_SAFE_POINT]`).

    상한은 `MAX_REASONS`(계약 `maxItems: 3`)다. **잘릴 때 살아남는 쪽은 경로
    실패 사유다** - 뒤에서 자르면 방금 붙인 사유가 먼저 사라져 모순이 되돌아온다.
    """
    if post.reason is None:
        return tuple(primary_reasons[:MAX_REASONS])

    code, text, basis = post.reason
    # 같은 코드를 decide() 가 이미 냈으면 두 번 싣지 않는다.
    kept = [r for r in primary_reasons if r.code != code][: MAX_REASONS - 1]
    return tuple([*kept, Reason(code, text, basis)])
