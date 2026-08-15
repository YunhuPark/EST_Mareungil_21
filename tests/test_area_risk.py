"""지역 위험 집계 (TH-04 / O-01).

이 파일이 지키는 것은 두 가지다.

1. **픽스처와 규칙이 어긋나지 않는다.** 픽스처의 `area_risk` 는 그 픽스처 자신의
   센서 확률로 규칙을 다시 돌린 결과와 같아야 한다. 어긋나면 누군가 손으로
   고쳤거나 생성기와 픽스처가 갈라진 것이다.
2. **규칙 자체의 성질.** 회복 국면을 따라가는지, 범위 밖 센서를 세지 않는지 등.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mareungil import area_risk  # noqa: E402

FIXTURES = ROOT / "contracts" / "fixtures"
RISK_FILES = sorted(FIXTURES.glob("risk_*.json"))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", RISK_FILES, ids=lambda p: p.name)
def test_픽스처의_area_risk가_규칙과_일치한다(path: Path):
    """손으로 고치거나 생성기가 갈라지면 여기서 잡힌다."""
    body = load(path)
    assert body["area_risk"] == area_risk.compute(body["sensors"]), (
        f"{path.name} 의 area_risk 가 규칙과 다르다. "
        "python scripts/refresh_area_risk.py --write 로 다시 계산한다."
    )


def test_DS픽스처의_risk블록도_같은_규칙을_따른다():
    for path in sorted((FIXTURES / "demo").glob("*.json")):
        risk = load(path)["risk"]
        assert risk["area_risk"] == area_risk.compute(risk["sensors"]), path.name


def test_경로_범위_밖_센서는_세지_않는다():
    """강남역에서 멀리 떨어진 센서가 1.0 이어도 지역 위험을 올리지 못한다."""
    scope = area_risk.load_scope()
    far = {
        "id": "FAR-001",
        "horizons": {"30": {"high_level_p": 1.0}},
        # 강남역에서 한참 떨어진 좌표
        "location": {"lat": 37.6000, "lon": 127.1500, "quality": "TEST"},
    }
    assert area_risk.in_scope(far, scope) is False
    assert area_risk.compute([far], scope)["risk_probability"] is None


def test_좌표가_없으면_분모에서_빠진다():
    """`23-0007` 처럼 UNMATCHED 인 센서는 범위 안이라고 말할 수 없다."""
    scope = area_risk.load_scope()
    near = {"id": "N", "horizons": {"30": {"high_level_p": 0.9}},
            "location": {"lat": 37.4980, "lon": 127.0277, "quality": "T"}}
    unknown = {"id": "U", "horizons": {"30": {"high_level_p": 0.9}},
               "location": {"lat": None, "lon": None, "quality": "UNMATCHED"}}

    out = area_risk.compute([near, unknown], scope)
    assert out["risk_probability"] == 1.0, "분모가 1이어야 한다 (좌표 미상 제외)"
    assert "좌표 미상 1개 제외" in out["basis"]


def test_센서가_없으면_0이_아니라_None이다():
    """"위험이 없다"와 "판단할 근거가 없다"를 같은 값으로 표현하지 않는다."""
    out = area_risk.compute([], area_risk.load_scope())
    assert out["risk_probability"] is None
    assert out["ai_risk_level"] is None
    assert out["score"] is None


def test_회복_국면을_따라간다():
    """O-01 을 고른 이유 자체를 테스트로 고정한다.

    예전 규칙(상위 25% 평균)은 피크 0.9995 -> 회복 0.9637 로 0.036 밖에 안 내려갔다.
    새 규칙은 피크와 회복이 확실히 갈려야 한다.
    """
    peak = load(FIXTURES / "risk_S3_peak.json")["area_risk"]["risk_probability"]
    recovery = load(FIXTURES / "risk_S4_recovery.json")["area_risk"]["risk_probability"]
    assert peak - recovery >= 0.2, (
        f"피크 {peak} 회복 {recovery}. 낙폭이 0.2 미만이면 회복 국면을 못 따라가는 것이다."
    )


def test_평온_국면은_LOW다():
    calm = load(FIXTURES / "risk_S1_calm.json")["area_risk"]
    assert calm["ai_risk_level"] == "LOW"
    assert calm["risk_probability"] == 0.0


def test_AI는_SEVERE를_만들_수_없다():
    """ai_risk_level 은 LOW/HIGH 두 값뿐이다 (C-06 / F-02)."""
    for path in RISK_FILES:
        level = load(path)["area_risk"]["ai_risk_level"]
        assert level in ("LOW", "HIGH", None), f"{path.name}: {level}"


def test_지역_임계가_문서와_같다():
    """DECISIONS 3.2.1 에 적힌 값과 코드가 어긋나면 실패한다."""
    assert area_risk.SENSOR_THRESHOLD == 0.33
    assert area_risk.AREA_THRESHOLD == 0.5


def test_경로_범위는_destinations_json에서_온다():
    """범위의 정본은 C 가 소유하는 파일 하나다. 좌표를 복사해두지 않는다."""
    scope = area_risk.load_scope()
    declared = json.loads((ROOT / "contracts" / "destinations.json").read_text(encoding="utf-8"))
    assert scope["lat"] == declared["scope"]["center_lat"]
    assert scope["lon"] == declared["scope"]["center_lon"]
    assert scope["radius_m"] == declared["scope"]["radius_m"]
