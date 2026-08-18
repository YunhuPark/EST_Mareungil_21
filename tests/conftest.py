"""테스트 공통 설정."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.decision.adapters import signals_from  # noqa: F401 - test_fixture_engine_agreement.py 가 여기서 import
from services.decision.decide import decide as _decide

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
