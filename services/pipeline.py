"""판단 엔진과 경로 엔진을 하나의 `AssessResponse` 로 합치는 자리.

왜 새 모듈인가
--------------
**API 와 픽스처 생성기가 정확히 같은 조립을 해야 한다.** 다르면 픽스처가 화면과
다른 말을 하게 되고, 실제로 그랬다 — `contracts/fixtures/demo/DS-S1` 은 근거 3줄과
후보 목록이 실린 `decision`·`route` 를 들고 있었지만, `api/main.py` 는 그것을
통째로 덮어쓰고 근거 1줄짜리 응답을 내보냈다. 아무도 눈치채지 못한 이유는 픽스처를
읽는 사람과 응답을 받는 화면이 서로 다른 값을 보고 있었기 때문이다.

그런데 조립을 둘 곳이 마땅치 않았다(CLAUDE.md 10절).

- `services/decision/` 은 `services/route` 를 import 할 수 없다
- `scripts/` 는 `api/` 를 import 할 수 없다

두 규칙을 모두 지키면서 조립을 한 곳에 두려면 **둘 위에 있는 모듈**이 필요하다.
그것이 이 파일이다.

    services/pipeline  ->  services/decision  +  services/route

이 모듈은 정책을 만들지 않는다. `classify()`·`decide()`·`apply()` 와 경로
provider 가 낸 값을 순서대로 꽂을 뿐이며, 판정 규칙은 전부 그쪽에 있다.
"""

from __future__ import annotations

import json
from typing import Any

from services.decision.adapters import signals_from
from services.decision.decide import decide
from services.decision.enums import RouteStatus
from services.decision.postprocess import apply, final_reasons, representative_code
from services.decision.service_risk import classify
from services.route.fixture_provider import FixtureRouteProvider
from services.route.interface import RouteProvider
from services.route.provider import provider_for as designated_provider_for
from services.route.provider import route_request_from

#: 실제 경로 엔진으로 재현 가능한 시나리오. `DS-S7`·`DS-S8` 은 시설 만석 서사가
#: 진짜 엔진으로 재현되지 않아 픽스처 STUB 에 남는다(M-32 — 시설 상태 연동은
#: MVP 범위 밖이고 저장소에 대피시설 원자료가 없다).
#:
#: `DS-S4`(고립 신고)는 **경로 엔진을 타지만 후보 비교를 하지 않는다** — `EMERGENCY`
#: 는 `not_required()` 로 끝나므로 센서도 안전거점도 필요 없다. 그래서 가장 싸게
#: LIVE 가 된다.
LIVE_ROUTE_SCENARIOS = frozenset({"DS-S1", "DS-S4", "DS-S6"})

#: 엔진이 채우는 `decision` 키. 여기 있는 값을 **손으로 적지 않는다.**
#: 나머지(`user_state`·`next_check_at`·`policy_version`)는 입력이거나 메타데이터다.
ENGINE_DECISION_KEYS = (
    "primary_action",
    "action",
    "route_postprocess_applied",
    "service_risk_level",
    "needs_route",
    "reason_code",
    "reasons",
)


def route_source_of(scenario: str | None) -> str:
    """그 시나리오의 경로가 실제 엔진에서 오는가 픽스처에서 오는가.

    **한 곳에서만 정한다.** provider 를 고르는 일과 `source_kind` 를 적는 일이
    각자 판단하면, 엔진을 태우면서 화면에는 `FIXTURE` 라고 적는 상태가 조용히
    생긴다 — 응답이 자기 출처를 잘못 말하는 것이 가장 나쁜 실패다.
    """
    return "LIVE_PIPELINE" if scenario in LIVE_ROUTE_SCENARIOS else "FIXTURE"


def provider_for(
    body: dict,
    safe_points: list[dict[str, Any]],
    fixture_routes: dict[str, dict[str, Any]],
) -> RouteProvider:
    """시나리오별로 실제 경로 엔진과 픽스처 STUB 을 가른다.

    두 갈래 모두 `solve(request)` 하나로 호출된다 — 시그니처 어긋남은 감사 10.3
    에서 닫았고 `tests/test_route_provider_protocol.py` 가 지킨다.

    Args:
        body: 조립할 `AssessResponse` payload. `_scenario` 로 갈래를 정한다.
        safe_points: `contracts/safe_points.json` 의 7곳(C-32).
        fixture_routes: 시나리오 id -> 손으로 쓴 `SafeRoute`. LIVE 시나리오에는
            쓰이지 않으므로 비어 있어도 된다.
    """
    scenario = body.get("_scenario")
    if route_source_of(scenario) == "LIVE_PIPELINE":
        return designated_provider_for(body, safe_points)

    return FixtureRouteProvider(routes=fixture_routes).for_scenario(scenario)


def apply_engine(body: dict, profiles: list[str], provider: RouteProvider) -> dict:
    """RF 위험 -> `classify()` -> `decide()` -> 경로 엔진 -> `apply()` 로
    `decision`·`route` 블록을 채운다.

    원본 payload 를 건드리지 않고 새 dict 를 돌려준다.

    `risk` 블록은 이미 실제 모델 출력이므로 손대지 않는다. `route` 도
    LIVE 시나리오에서는 실제 경로 엔진이 계산하며, 후처리 규칙
    (`CONFIRMED_TRANSITIONS`·`CONFIRMED_HOLDS`)은 그 결과의 `status` 를 그대로 받는다.

    `needs_route` 는 계약(`assess_response.schema.json` 의 allOf)이 **1차 행동
    (`primary_action`) 기준**으로 강제한다 — 경로 후처리로 최종 행동이 바뀌어도
    그대로다. 그래서 `post.action` 이 아니라 `primary.needs_route`
    (= `primary_action` 에서 파생된 값)를 쓴다.
    """
    signals = signals_from(body)
    risk_result = classify(signals)
    primary = decide(signals)

    route = provider.solve(route_request_from(body, primary.action, profiles))
    post = apply(primary.action, RouteStatus(route["status"]))

    # 대표 사유와 이유 목록은 같은 후처리 결과에서 나온다. 따로 만들면 배너와
    # 목록이 서로 다른 말을 하게 된다 — `DS-S6` 가 실제로 그랬다.
    reason_code = representative_code(primary.reasons, post)
    reasons = final_reasons(primary.reasons, post)

    out = json.loads(json.dumps(body))  # 원본 payload 를 건드리지 않는다
    out["route"] = route
    out["decision"].pop("_stub", None)
    out["decision"].update(
        primary_action=primary.action.value,
        action=post.action.value,
        route_postprocess_applied=post.applied,
        service_risk_level=risk_result.level.value,
        needs_route=primary.needs_route,
        reason_code=reason_code,
        reasons=[r.as_dict() for r in reasons],
    )
    out["source_kind"] = route_source_of(body.get("_scenario"))
    return out
