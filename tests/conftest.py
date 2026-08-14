"""테스트 공통 설정."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def ds_s1() -> dict:
    """DS-S1 통합 데모 응답. 수직 슬라이스가 실제로 쓰는 픽스처다."""
    path = ROOT / "contracts" / "fixtures" / "demo" / "DS-S1.assess_response.json"
    return json.loads(path.read_text(encoding="utf-8"))
