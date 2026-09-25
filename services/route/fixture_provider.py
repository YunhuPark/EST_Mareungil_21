"""STUB 경로 공급자.

**후보를 비교하지 않는다.** 픽스처에 이미 들어 있는 `route` 블록을 그대로
돌려주는 자리표시자이며, 실제 경로 엔진이 붙으면 통째로 대체된다.

이 클래스가 존재하는 이유는 API 와 UI 가 경로 엔진 없이도 끝까지 돌아가게
하기 위해서다. 반환값에는 `_stub` 표시가 남아 있어 화면에서 mock 임을 알 수 있다.

왜 등록부와 provider 를 나누는가
--------------------------------
예전에는 `solve(self, request, scenario)` 하나였다. `RouteProvider` 프로토콜은
`solve(self, request)` 인데 인자 개수가 달랐고, **아무 테스트도 빨개지지 않았다**
(`REPOSITORY_AUDIT.md` 10.3). 호출부는 그 차이를 함수 안에서 클래스를 정의해
메웠다 — `api/main.py` 의 `_BoundFixtureProvider` 였다.

시나리오를 **생성 시점에** 묶으면 그 어긋남이 사라진다. 등록부
(`FixtureRouteProvider`)는 시나리오 -> 경로를 들고 있고, `for_scenario()` 가
프로토콜을 그대로 만족하는 provider 하나를 돌려준다.
`tests/test_route_provider_protocol.py` 가 두 provider 의 시그니처를 대조한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.route.interface import RouteRequest, target_for


@dataclass(frozen=True)
class BoundFixtureRouteProvider:
    """시나리오 하나에 묶인 픽스처 provider. `RouteProvider` 를 그대로 만족한다.

    Attributes:
        route: 그 시나리오 픽스처의 `SafeRoute` 블록.
        scenario: 오류 문구에 쓸 시나리오 id.
    """

    route: dict[str, Any]
    scenario: str

    def solve(self, request: RouteRequest) -> dict[str, Any]:
        """묶인 시나리오의 경로 블록을 돌려준다.

        Raises:
            ValueError: 픽스처의 도달 대상이 요청한 1차 행동과 어긋날 때(RT-12).
        """
        route = dict(self.route)
        route.setdefault("_stub", "services/route 미구현. 후보 비교 결과가 아니다.")

        # 도달 대상만은 요청한 1차 행동과 어긋나지 않게 확인한다(RT-12).
        expected = target_for(request.primary_action)
        actual = route.get("route_target")
        if expected is not None and actual != expected.value:
            raise ValueError(
                f"픽스처 {self.scenario} 의 route_target={actual} 이 "
                f"{request.primary_action} 의 도달 대상 {expected.value} 과 다르다 (RT-12)"
            )
        return route


class FixtureRouteProvider:
    """시나리오 -> 경로 블록 등록부.

    **이 객체 자체는 `RouteProvider` 가 아니다.** 시나리오를 알아야 답할 수 있기
    때문이다. `for_scenario()` 로 묶은 뒤에야 `solve(request)` 하나가 된다.

    Args:
        routes: 시나리오 id -> `SafeRoute` dict.
    """

    def __init__(self, routes: dict[str, dict[str, Any]]) -> None:
        self._routes = routes

    def for_scenario(self, scenario: str) -> BoundFixtureRouteProvider:
        """시나리오 하나에 묶인 provider.

        Raises:
            KeyError: 해당 시나리오 픽스처가 없을 때. **묶는 시점에** 터진다 —
                경로를 푸는 도중이 아니라 배선할 때 알아야 고치기 쉽다.
        """
        return BoundFixtureRouteProvider(route=self._routes[scenario], scenario=scenario)
