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


# ---------------------------------------------------------------------------
# O-08. 경계 근처 진동 억제 (비대칭 확인)
# ---------------------------------------------------------------------------


def test_위험_진입은_즉시다():
    """이게 이 규칙에서 가장 중요한 성질이다. 대피 경보를 늦추지 않는다."""
    state = area_risk.step("LOW")
    assert state.level == "LOW"
    assert area_risk.step("HIGH", state).level == "HIGH", "HIGH 진입에 지연이 있으면 안 된다"


def test_해제는_연속_확인을_요구한다():
    seq = ["HIGH"] + ["LOW"] * area_risk.EXIT_DWELL_STEPS
    out = area_risk.stabilize(seq)
    assert out[0] == "HIGH"
    # 마지막 한 번을 채우기 전까지는 HIGH 를 유지한다.
    assert out[1:-1] == ["HIGH"] * (area_risk.EXIT_DWELL_STEPS - 1)
    assert out[-1] == "LOW"


def test_짧은_깜빡임이_사라진다():
    """실측에서 문제가 됐던 모양 — 10분만에 LOW 로 갔다가 되돌아온 구간."""
    raw = ["HIGH", "LOW", "HIGH"]
    assert area_risk.stabilize(raw) == ["HIGH", "HIGH", "HIGH"]


def test_해제_도중_HIGH가_오면_카운터가_초기화된다():
    raw = ["HIGH", "LOW", "LOW", "HIGH", "LOW", "LOW"]
    out = area_risk.stabilize(raw)
    assert out == ["HIGH", "HIGH", "HIGH", "HIGH", "HIGH", "HIGH"], (
        "중간에 HIGH 가 한 번 오면 해제 카운트를 다시 세야 한다"
    )


def test_충분히_길게_LOW면_결국_해제된다():
    """끈적하기만 하고 안 내려가면 그것도 고장이다."""
    raw = ["HIGH"] + ["LOW"] * 10
    out = area_risk.stabilize(raw)
    assert out[-1] == "LOW"
    assert out.count("LOW") == 10 - area_risk.EXIT_DWELL_STEPS + 1


def test_판단_불가는_그대로_통과한다():
    """"모른다"를 "안전하다"로 바꾸지 않는다."""
    out = area_risk.stabilize(["HIGH", None, None])
    assert out == ["HIGH", None, None]


def test_판단_불가_동안_해제_카운트가_쌓이지_않는다():
    """데이터가 끊긴 시간을 "LOW 였다"로 세면 복구 즉시 등급이 떨어진다."""
    after_gap = area_risk.stabilize(["HIGH", None, None, None, "LOW"])
    assert after_gap[-1] == "HIGH", "결측 구간이 해제를 앞당기면 안 된다"


def test_첫_스텝은_이전_상태가_없어도_동작한다():
    assert area_risk.step("HIGH").level == "HIGH"
    assert area_risk.step("LOW").level == "LOW"
    assert area_risk.step(None).level is None


def test_같은_입력이면_같은_출력이다():
    """N-04. 전역 상태를 두지 않았는지 본다."""
    raw = ["LOW", "HIGH", "LOW", "LOW", "HIGH", None, "LOW"]
    assert area_risk.stabilize(raw) == area_risk.stabilize(raw)
    mid = area_risk.DwellState(level="HIGH", pending_exit=1)
    assert area_risk.step("LOW", mid) == area_risk.step("LOW", mid)


def test_해제_지연이_문서와_같다():
    assert area_risk.EXIT_DWELL_STEPS == 3
    assert area_risk.STEP_MINUTES == 10


def test_compute는_억제를_적용하지_않는다():
    """집계와 억제를 분리해 둔다.

    `compute()` 는 그 시각의 raw 등급만 낸다. 억제는 재생 수열을 걷는 쪽이
    `step()` 으로 얹는다. 섞으면 `compute()` 가 순수하지 않게 된다.
    """
    calm = load(FIXTURES / "risk_S1_calm.json")
    assert area_risk.compute(calm["sensors"])["ai_risk_level"] == "LOW"
    assert "ai_risk_level" in area_risk.compute(calm["sensors"])
    assert not hasattr(area_risk.compute(calm["sensors"]), "pending_exit")


# --- 센서별 판정 (annotate) --------------------------------------------------
#
# 지도가 임계를 다시 적용하지 않으려면(CLAUDE.md 10절) 비율을 만든 그 판정이
# 응답에 실려야 한다. 그러면 화면의 점 개수와 `basis` 의 "n/m" 이 같은 값에서
# 나온다. 아래 검사가 그 "같은 값"을 강제한다.

#: 센서를 실제로 싣는 픽스처. (파일, RiskAssessment 본문까지의 경로)
SENSOR_BODIES = [(p, []) for p in RISK_FILES] + [
    (p, ["risk"]) for p in sorted((FIXTURES / "demo").glob("*.json"))
]


def dig(payload: dict, path: list[str]) -> dict:
    for key in path:
        payload = payload[key]
    return payload


@pytest.mark.parametrize("path,inner", SENSOR_BODIES, ids=lambda v: getattr(v, "name", ""))
def test_센서_판정이_area_risk_비율과_일치한다(path: Path, inner: list[str]):
    """**이것이 이 기능의 핵심 불변식이다.**

    지도는 `in_area_scope` 로 점을 고르고 `exceeds_sensor_threshold` 로 표현을
    가른다. 그 두 값으로 센 수가 `area_risk` 의 분모·분자와 다르면, 화면이
    등급과 다른 말을 하게 된다 — 앞선 시도가 되돌려진 이유가 그것이다.

    두 조건을 **함께** 보는 이유는 범위 안이면서 확률이 없는 센서가 가능하고,
    그 센서는 분모에 들어가지 않기 때문이다.
    """
    body = dig(load(path), inner)
    sensors, area = body["sensors"], body["area_risk"]

    judged = [
        s for s in sensors
        if s["in_area_scope"] and s["exceeds_sensor_threshold"] is not None
    ]
    over = sum(1 for s in judged if s["exceeds_sensor_threshold"])

    if not judged:
        assert area["risk_probability"] is None, (
            f"{path.name}: 판정된 센서가 없는데 비율이 있다"
        )
        return

    assert area["risk_probability"] == round(over / len(judged), 4), (
        f"{path.name}: 센서 판정 {over}/{len(judged)} 이 비율과 다르다"
    )
    assert f"비율 {over}/{len(judged)}." in area["basis"], (
        f"{path.name}: basis 의 n/m 이 센서 판정과 다르다 — {area['basis']}"
    )


@pytest.mark.parametrize("path,inner", SENSOR_BODIES, ids=lambda v: getattr(v, "name", ""))
def test_픽스처의_모든_센서가_판정을_싣는다(path: Path, inner: list[str]):
    """생성기를 `annotate()` 없이 돌리면 여기서 잡힌다."""
    for sensor in dig(load(path), inner)["sensors"]:
        assert "in_area_scope" in sensor, f"{path.name} {sensor['id']}"
        assert "exceeds_sensor_threshold" in sensor, f"{path.name} {sensor['id']}"


def test_좌표가_없으면_범위_안이라고_말하지_않는다():
    """`23-0007` 처럼 UNMATCHED 인 센서는 확률이 높아도 지도에 올라오지 않는다.

    좌표를 모르는 센서를 범위 안이라고 표시하면 화면이 그 점을 어딘가에 찍어야
    하고, 그 위치는 무엇의 근거도 아니다.
    """
    scope = area_risk.load_scope()
    unknown = {
        "id": "U",
        "horizons": {"30": {"high_level_p": 0.9991}},
        "location": {"lat": None, "lon": None, "quality": "UNMATCHED"},
    }

    out = area_risk.annotate([unknown], scope)[0]
    assert out["in_area_scope"] is False
    # 확률 자체는 임계를 넘는다. 그래도 범위 안이 아니다 — 두 판정은 다른 축이다.
    assert out["exceeds_sensor_threshold"] is True


def test_확률이_없으면_판정이_None이다():
    """"임계 미만"과 "판단할 값이 없다"를 같은 값으로 표현하지 않는다."""
    scope = area_risk.load_scope()
    blank = {
        "id": "B",
        "horizons": {"30": {}},
        "location": {"lat": 37.4980, "lon": 127.0277, "quality": "T"},
    }

    out = area_risk.annotate([blank], scope)[0]
    assert out["exceeds_sensor_threshold"] is None, "False 로 채우면 안 된다"
    assert out["in_area_scope"] is True, "확률이 없는 것과 범위는 다른 축이다"

    # 그리고 이 센서는 분모에 들어가지 않는다 — 지도도 같은 규칙으로 세야 한다.
    assert area_risk.compute([blank], scope)["risk_probability"] is None


def test_판정에_쓰는_임계는_compute와_같다():
    """지도가 다른 임계를 쓰면 점 개수와 등급이 어긋난다."""
    scope = area_risk.load_scope()
    at = {
        "id": "AT",
        "horizons": {"30": {"high_level_p": area_risk.SENSOR_THRESHOLD}},
        "location": {"lat": 37.4980, "lon": 127.0277, "quality": "T"},
    }
    just_under = {
        "id": "UNDER",
        "horizons": {"30": {"high_level_p": area_risk.SENSOR_THRESHOLD - 0.0001}},
        "location": {"lat": 37.4980, "lon": 127.0277, "quality": "T"},
    }

    marked = area_risk.annotate([at, just_under], scope)
    assert marked[0]["exceeds_sensor_threshold"] is True, "임계값 자체는 초과로 센다"
    assert marked[1]["exceeds_sensor_threshold"] is False
    # compute 도 같은 경계를 쓴다 — 2개 중 1개.
    assert area_risk.compute([at, just_under], scope)["risk_probability"] == 0.5


def test_annotate는_입력을_건드리지_않는다():
    """N-04. 순수 함수이며 호출해도 원본 dict 가 바뀌지 않는다."""
    scope = area_risk.load_scope()
    sensor = {
        "id": "S",
        "horizons": {"30": {"high_level_p": 0.9}},
        "location": {"lat": 37.4980, "lon": 127.0277, "quality": "T"},
    }
    before = json.dumps(sensor, sort_keys=True)

    area_risk.annotate([sensor], scope)
    assert json.dumps(sensor, sort_keys=True) == before, "입력이 오염됐다"

    # 같은 입력이면 같은 출력이다.
    assert area_risk.annotate([sensor], scope) == area_risk.annotate([sensor], scope)
