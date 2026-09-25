"""테스트 공통 설정."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from services.decision.adapters import signals_from  # noqa: F401 - test_fixture_engine_agreement.py 가 여기서 import
from services.decision.decide import decide as _decide

# 빈도 제한을 끈 채로 나머지 테스트를 돌린다.
#
# `TestClient` 의 요청은 전부 같은 상대 주소("testclient")에서 오므로 한 버킷에
# 쌓인다. `test_api.py` 하나가 60번을 훌쩍 넘기니 기본 한도(60회/60초)에서는
# 뒤쪽 테스트가 429 로 떨어진다 — 기능이 깨져서가 아니라 테스트가 한 사람처럼
# 보여서다.
#
# **`api.main` 을 import 하기 전에 세워야 한다.** 설정을 모듈 로드 시점에 읽는다.
# conftest 는 테스트 모듈보다 먼저 로드되므로 여기가 그 자리다.
#
# 빈도 제한 자체는 `test_ratelimit.py` 가 자기 앱과 자기 한도로 따로 검증한다.
os.environ.setdefault("MAREUNGIL_RATE_LIMIT", "0")

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def ds_s1() -> dict:
    """DS-S1 통합 데모 응답. 수직 슬라이스가 실제로 쓰는 픽스처다."""
    path = ROOT / "contracts" / "fixtures" / "demo" / "DS-S1.assess_response.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def decide():
    """`decide()` 함수 자체를 픽스처로 노출한다.

    `test_decide.py`가 이 픽스처를 파라미터로 받아서 쓴다. 상태 없는 순수
    함수라 세션 스코프로 캐싱할 필요는 없다.
    """
    return _decide


def load(root: Path, name: str) -> dict:
    """데모 통합 응답 픽스처를 이름으로 읽는다.

    예: `load(root, "DS-S7")` -> `contracts/fixtures/demo/DS-S7.assess_response.json`.
    """
    path = root / "contracts" / "fixtures" / "demo" / f"{name}.assess_response.json"
    return json.loads(path.read_text(encoding="utf-8"))
