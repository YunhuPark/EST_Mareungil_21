"""픽스처를 API 에 통과시키면 **자기 자신이 나오는가.**

무엇을 지키나
-------------
`contracts/fixtures/demo/DS-*.assess_response.json` 은
`scripts/build_demo_assess_fixtures.py` 가 `services/pipeline.apply_engine()` 으로
만든 파일이고, `api/main.py` 도 응답을 조립할 때 같은 함수를 부른다. 그러면
**픽스처를 그대로 파이프라인에 넣었을 때 한 글자도 바뀌지 않아야 한다.**

바뀐다면 셋 중 하나다.

1. 픽스처를 손으로 고쳤다 (생성기를 다시 돌리지 않았다)
2. 엔진을 고치고 픽스처를 다시 만들지 않았다
3. API 와 생성기가 서로 다른 입력을 준다 (안전거점 목록·픽스처 경로 등)

셋 다 같은 결과를 낳는다 — **픽스처를 읽는 사람과 화면을 보는 사람이 다른 값을
본다.** 저장소가 실제로 그 상태였다. `DS-S1` 픽스처에는 근거 3줄과 후보 목록이
실려 있었지만 API 는 그것을 통째로 덮어쓰고 근거 1줄을 내보냈고, 프론트 테스트는
픽스처를 직접 렌더링하고 있어서 **API 가 내보내지 않는 형태**를 검증하고 있었다.

`test_fixture_engine_agreement.py` 와 무엇이 다른가
---------------------------------------------------
그 파일은 `decision` 의 **행동 축**이 엔진과 맞는지 필드별로 확인한다. 이 파일은
`decision` 도 `route` 도 `source_kind` 도 가리지 않고 **응답 전체**를 대조한다.
필드를 하나 더해도 이쪽은 자동으로 덮는다.

깨뜨리면 무엇이 빨개지는가(CLAUDE.md 8절)
-----------------------------------------
픽스처의 `action` 을 손으로 한 글자 고치면 이 파일이 실패한다. 고친 값이 계약을
통과하는 값이어도 실패한다 — 계약 검증이 잡는 것은 형식이고, 이 검사가 잡는 것은
**출처**다.
"""

from __future__ import annotations

import json

import pytest

from api.main import _engine, _scenarios


def copy_of(body: dict) -> dict:
    """파이프라인이 원본을 건드리지 않는지까지 보려면 사본을 넘겨야 한다."""
    return json.loads(json.dumps(body))


@pytest.mark.parametrize("scenario", sorted(_scenarios))
def test_픽스처는_파이프라인의_고정점이다(scenario: str):
    body = _scenarios[scenario]
    out = _engine(copy_of(body), [])

    assert out == body, (
        f"{scenario} 픽스처가 엔진 출력과 다르다. "
        f"`.\\make.ps1 fixtures` 로 다시 만들었는지 확인한다."
    )


@pytest.mark.parametrize("scenario", sorted(_scenarios))
def test_두_번_돌려도_같다(scenario: str):
    """조립이 멱등인가. 같은 입력에 두 번 다른 답을 내면 재현성이 없다(N-04)."""
    once = _engine(copy_of(_scenarios[scenario]), [])
    twice = _engine(copy_of(once), [])

    assert once == twice


@pytest.mark.parametrize("scenario", sorted(_scenarios))
def test_파이프라인은_원본을_건드리지_않는다(scenario: str):
    """`_scenarios` 는 프로세스 수명 내내 재사용되는 dict 다.

    조립이 원본을 제자리에서 고치면 두 번째 요청이 첫 번째 응답 위에 쌓인다 —
    사용자가 목적지를 바꿀 때마다 앞의 판정이 남는 종류의 버그다.
    """
    before = copy_of(_scenarios[scenario])
    _engine(_scenarios[scenario], [])

    assert _scenarios[scenario] == before


def test_두_갈래가_모두_있다():
    """LIVE 와 픽스처 양쪽이 실제로 있어야 위 대조가 두 경로를 다 덮는다."""
    kinds = {_engine(copy_of(body), [])["source_kind"] for body in _scenarios.values()}

    assert kinds == {"LIVE_PIPELINE", "FIXTURE"}
