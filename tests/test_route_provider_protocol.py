"""경로 provider 가 `RouteProvider` 프로토콜을 실제로 지키는가 (감사 10.3).

왜 이 파일이 필요한가
---------------------
`interface.py` 의 `RouteProvider.solve(self, request)` 와
`fixture_provider.py` 의 `solve(self, request, scenario)` 는 **인자 개수가 달랐다.**
Python 은 Protocol 을 런타임에 강제하지 않고 저장소에 정적 타입 검사도 없어서
**어떤 테스트도 빨개지지 않았다.** 호출부는 그 차이를 함수 안에서 클래스를 정의해
메웠다 — `api/main.py` 의 `_BoundFixtureProvider` 였다.

깨뜨리면 무엇이 빨개지는가(CLAUDE.md 8절)
-----------------------------------------
provider 중 하나의 `solve()` 에 인자를 더하거나 이름을 바꾸면 이 파일이 실패한다.
`api/main.py` 가 새 시나리오를 픽스처 쪽으로 보내면서 배선을 틀리게 해도
마지막 테스트가 잡는다 — 실제 `provider_for()` 를 시나리오 전부에 통과시킨다.

`isinstance` 를 쓰지 않는 이유는 `runtime_checkable` 이 **메서드 존재만** 보고
시그니처는 보지 않기 때문이다. 여기서 어긋났던 것이 바로 시그니처다.
"""

from __future__ import annotations

import inspect

import pytest

from api.main import _scenarios, provider_for, route_source_of
from services.route.fixture_provider import BoundFixtureRouteProvider, FixtureRouteProvider
from services.route.interface import RouteProvider
from services.route.provider import DesignatedPointRouteProvider

#: 프로토콜이 요구하는 `solve()` 인자 이름. `self` 는 뺀다.
PROTOCOL_PARAMS = [
    name for name in inspect.signature(RouteProvider.solve).parameters if name != "self"
]

ROUTE_BLOCK = {
    "status": "NOT_REQUIRED",
    "route_verified": False,
    "route_target": None,
    "target": None,
    "route_attempted": False,
    "no_safe_route": None,
    "limit": "경로 탐색이 필요하지 않은 행동입니다.",
}


def solve_params(provider: object) -> list[str]:
    return list(inspect.signature(provider.solve).parameters)  # type: ignore[attr-defined]


def test_프로토콜이_인자_하나를_요구한다():
    """이 목록이 비면 아래 대조가 전부 무의미해진다."""
    assert PROTOCOL_PARAMS == ["request"]


@pytest.mark.parametrize(
    "provider",
    [
        DesignatedPointRouteProvider(safe_points=[], sensors=[]),
        FixtureRouteProvider(routes={"DS-S1": ROUTE_BLOCK}).for_scenario("DS-S1"),
    ],
    ids=["designated", "fixture"],
)
def test_두_provider_가_같은_시그니처를_가진다(provider):
    assert solve_params(provider) == PROTOCOL_PARAMS


def test_등록부는_provider_가_아니다():
    """시나리오를 모르면 답할 수 없으므로 등록부 자신은 `solve()` 를 갖지 않는다.

    이것을 확인해 두는 이유는, 등록부에 `solve()` 를 도로 붙이면 '시나리오 인자가
    하나 더 필요한 provider' 가 다시 생기기 때문이다.
    """
    assert not hasattr(FixtureRouteProvider(routes={}), "solve")


def test_없는_시나리오는_묶는_시점에_터진다():
    with pytest.raises(KeyError):
        FixtureRouteProvider(routes={}).for_scenario("DS-S9")


def test_실제_배선이_모든_시나리오에서_프로토콜을_지킨다():
    """`api/main.py` 가 고르는 provider 를 시나리오 전부에 대해 확인한다.

    LIVE 와 픽스처 양쪽이 모두 나와야 대조가 의미를 갖는다.
    """
    sources = set()

    for scenario, body in _scenarios.items():
        provider = provider_for(body)
        assert solve_params(provider) == PROTOCOL_PARAMS, f"{scenario} 의 provider"
        sources.add(route_source_of(body.get("_scenario")))

    assert sources == {"LIVE_PIPELINE", "FIXTURE"}


def test_픽스처_provider_는_묶인_경로를_그대로_돌려준다():
    bound = FixtureRouteProvider(routes={"DS-S1": ROUTE_BLOCK}).for_scenario("DS-S1")
    assert isinstance(bound, BoundFixtureRouteProvider)

    # `NOT_REQUIRED` 는 도달 대상이 없으므로 어떤 요청이든 RT-12 검사를 통과한다.
    from services.decision.enums import Action
    from services.route.interface import DestinationPoint, RoutePoint, RouteRequest

    request = RouteRequest(
        primary_action=Action.WAIT,
        origin=RoutePoint(lat=37.4979, lon=127.0276),
        destination=DestinationPoint(id="", label="", lat=37.4979, lon=127.0276),
        asof="2022-08-08T21:40:00+09:00",
    )

    result = bound.solve(request)
    assert result["status"] == "NOT_REQUIRED"
    # STUB 임을 응답에 남긴다 — 화면이 mock 을 실제 결과로 보이지 않게 하는 표시다.
    assert "_stub" in result
