"""경로 엔진 경계.

경로 엔진을 누가 어떻게 구현하든 API 는 이 프로토콜만 안다. G1 에서 그래프
조회를 채택하든(RT-08) 공식 후보 비교를 유지하든 이 경계는 바뀌지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from services.decision.enums import Action, Profile, RouteStatus, RouteTarget


@dataclass(frozen=True)
class DestinationPoint:
    """RT-14. 경로 범위 내 지정 지점 목록에서 고른 1개.

    목록의 정본은 `contracts/destinations.json` 이다. `EVACUATE` 의 도달 대상인
    안전거점은 다른 목록(`contracts/safe_points.json`)에서 오며 섞지 않는다.
    """

    id: str
    label: str
    lat: float
    lon: float


@dataclass(frozen=True)
class RoutePoint:
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteRequest:
    """경로 엔진 입력.

    Attributes:
        primary_action: 1차 행동. 도달 대상은 이 값으로 정해진다 -
            `MOVE` 는 사용자 목적지, `EVACUATE` 는 서비스가 고른 안전거점.
        destination: F-19. **필수 입력**이다. `MOVE` 의 도달 대상이며
            `EVACUATE` 의 안전거점 선택에는 관여하지 않는다.
        profiles: 안전 후보 내 순서만 바꾼다. 안전 임계값을 낮추지 않는다.
        official: 공식 통제·확인된 침수. 후보 비교 **전에** 구간을 제외하는 데 쓴다.
        asof: 재생 시각. 목적지 차단 여부는 시각마다 다시 판정한다(RT-17).
    """

    primary_action: Action
    origin: RoutePoint
    destination: DestinationPoint
    asof: str
    profiles: tuple[Profile, ...] = ()
    official: dict[str, Any] = field(default_factory=dict)
    in_service_area: bool = True


def target_for(action: Action) -> RouteTarget | None:
    """RT-12. 행동별 도달 대상. 교차하지 않는다.

    `SAFE_POINT` 의 후보는 `contracts/safe_points.json` 의 7곳으로 닫혀 있다
    (C-32). **닫힌 것은 후보 집합뿐이다** — 그중 어느 곳을 고를지, 후보를 어떤
    순서로 놓을지는 정해지지 않았으므로 여기서 정하지 않는다.
    """
    if action is Action.MOVE:
        return RouteTarget.USER_DESTINATION
    if action is Action.EVACUATE:
        return RouteTarget.SAFE_POINT
    return None


def not_required(limit: str) -> dict[str, Any]:
    """경로가 필요 없는 행동(`WAIT`·`EMERGENCY`·`UNAVAILABLE`)의 `SafeRoute`.

    ③을 호출하지 않고 이 값으로 채운다.
    """
    return {
        "status": RouteStatus.NOT_REQUIRED.value,
        "route_verified": False,
        "route_target": None,
        "target": None,
        "route_attempted": False,
        "no_safe_route": None,
        "limit": limit,
    }


class RouteProvider(Protocol):
    """경로 엔진이 구현할 것.

    반환값은 `contracts/schema/safe_route.schema.json` 을 통과해야 한다.
    """

    def solve(self, request: RouteRequest) -> dict[str, Any]:
        """도달 대상을 확정하고 후보를 비교해 `SafeRoute` 를 만든다.

        대상 단계에서 실패하면 경로 탐색에 들어가지 않으므로
        `route_attempted=False`, `no_safe_route=None` 으로 돌려준다.
        """
        ...
