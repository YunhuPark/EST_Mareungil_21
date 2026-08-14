"""경로 엔진 ③ — 공식 후보 경로 비교 인터페이스.

## 지금 구현된 것

- `interface.py` — `RouteProvider` 프로토콜과 요청 타입. 계약 경계만 고정한다.
- `fixture_provider.py` — **STUB.** 픽스처에 든 경로 블록을 그대로 돌려준다.
  후보를 비교하지 않는다.

## 아직 구현되지 않은 것 (T+6:00~8:00 구간)

공식 대피경로 30개 후보의 상대 비교가 없다. 지금 나오는 `candidates` 는
형식을 보여주는 자리표시자다.

## 이 모듈이 지켜야 할 것

- **대상 단계 -> 경로 단계** 순으로 진행한다. 대상 단계에서 끝나면
  `route_attempted=false`, `no_safe_route=null` 이다. 탐색하지 않은 상태에서
  "안전한 경로가 없다"고 단정하지 않는다(RT-09b).
- `NO_SAFE_POINT` 는 `EVACUATE` 에서만, `DESTINATION_BLOCKED` 은 `MOVE` 에서만 나온다.
- 기본 결과는 `FALLBACK_CANDIDATE` 이고 `route_verified=false` 다.
  "안전 경로"·"최적 경로"·"검증된 경로"를 반환하지 않는다(RT-02·RT-03).
- **공식 통제 구간은 후보 비교 전에 제외한다.** 통제 자체로 행동을 바꾸지 않는다(RT-11).
- **목적지 차단 근거는 공식 통제와 확인된 침수뿐이다.** AI 예측 확률만으로
  목적지를 차단하지 않는다(RT-17).
- 펌프장 61개는 대피시설 후보가 아니다(RT-07).
- 프로필은 이미 안전하다고 판정된 후보의 **순서만** 바꾼다. 안전 임계값을 낮추지 않는다.
- `services/decision` 을 import 하지 않는다.
"""

from services.route.fixture_provider import FixtureRouteProvider
from services.route.interface import RouteProvider, RouteRequest, not_required

__all__ = ["FixtureRouteProvider", "RouteProvider", "RouteRequest", "not_required"]
