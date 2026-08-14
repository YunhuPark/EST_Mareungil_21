"""STUB 경로 공급자.

**후보를 비교하지 않는다.** 픽스처에 이미 들어 있는 `route` 블록을 그대로
돌려주는 자리표시자이며, 실제 경로 엔진이 붙으면 통째로 대체된다.

이 클래스가 존재하는 이유는 API 와 UI 가 경로 엔진 없이도 끝까지 돌아가게
하기 위해서다. 반환값에는 `_stub` 표시가 남아 있어 화면에서 mock 임을 알 수 있다.
"""

from __future__ import annotations

from typing import Any

from services.route.interface import RouteRequest, target_for


class FixtureRouteProvider:
    """픽스처의 경로 블록을 그대로 반환한다.

    Args:
        routes: 시나리오 id -> `SafeRoute` dict.
    """

    def __init__(self, routes: dict[str, dict[str, Any]]) -> None:
        self._routes = routes

    def solve(self, request: RouteRequest, scenario: str) -> dict[str, Any]:
        """`scenario` 픽스처의 경로 블록을 돌려준다.

        Raises:
            KeyError: 해당 시나리오 픽스처가 없을 때.
        """
        route = dict(self._routes[scenario])
        route.setdefault("_stub", "services/route 미구현. 후보 비교 결과가 아니다.")

        # 도달 대상만은 요청한 1차 행동과 어긋나지 않게 확인한다(RT-12).
        expected = target_for(request.primary_action)
        actual = route.get("route_target")
        if expected is not None and actual != expected.value:
            raise ValueError(
                f"픽스처 {scenario} 의 route_target={actual} 이 "
                f"{request.primary_action} 의 도달 대상 {expected.value} 과 다르다 (RT-12)"
            )
        return route
