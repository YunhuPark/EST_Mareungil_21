"""안전거점(`SAFE_POINT`) 후보 집합.

이 파일이 지키는 것은 **후보 집합이 닫혔다**는 사실 하나다. 후보 순위나
`relative_risk` 는 아직 정해지지 않았으므로 여기서 검사하지 않는다 — 검사하면
정하지 않은 정책을 테스트로 확정하는 셈이 된다.

깨뜨리면 빨개지는 것(CLAUDE.md 8절):

1. `contracts/safe_points.json` 을 손으로 고치면 생성기 재현 검사가 실패한다.
2. `destinations.json` 의 범위를 바꾸고 여기를 다시 만들지 않으면 범위 일치가 실패한다.
3. 범위 안에 민간건물이 들어오면 M-25 검사가 실패한다.
4. 두 목록의 id 체계가 겹치면 충돌 검사가 실패한다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_safe_points import SOURCE, build  # noqa: E402
from mareungil.area_risk import haversine_m  # noqa: E402

SAFE_POINTS = ROOT / "contracts" / "safe_points.json"
DESTINATIONS = ROOT / "contracts" / "destinations.json"

pytestmark = pytest.mark.skipif(
    not SOURCE.exists(),
    reason=f"대피시설 전달 자료가 없다: {SOURCE.name}",
)


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(SAFE_POINTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def destinations() -> dict:
    return json.loads(DESTINATIONS.read_text(encoding="utf-8"))


# --- 재현성 -----------------------------------------------------------------


def test_커밋본이_생성기_결과와_같다(payload: dict):
    """손으로 고쳤거나 원본이 바뀌었으면 여기서 잡힌다."""
    assert payload == build(), (
        "contracts/safe_points.json 이 생성 결과와 다르다. "
        "python scripts/build_safe_points.py --write 로 다시 만든다."
    )


def test_check_모드가_실제로_작동한다():
    """`--check` 가 늘 0 을 뱉으면 재현성 검사가 없는 것과 같다."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_safe_points.py"), "--check"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr


# --- 범위는 destinations.json 하나에서 온다 ---------------------------------


def test_범위가_destinations_json과_같다(payload: dict, destinations: dict):
    """범위의 정본은 C 가 소유하는 파일 하나다. 사본이 갈라지면 실패한다."""
    mine, theirs = payload["scope"], destinations["scope"]
    for key in ("center_label", "center_lat", "center_lon", "radius_m"):
        assert mine[key] == theirs[key], f"scope.{key} 가 destinations.json 과 다르다"


def test_모든_후보가_범위_안에_있다(payload: dict):
    scope = payload["scope"]
    for point in payload["points"]:
        distance = haversine_m(
            scope["center_lat"], scope["center_lon"], point["lat"], point["lon"]
        )
        assert distance <= scope["radius_m"], f"{point['id']} 가 범위 밖이다"
        assert round(distance, 1) == point["distance_from_center_m"]


def test_경계_간격이_기록돼_있다(payload: dict):
    """반경을 조금 흔들어도 집합이 같다는 근거. 사라지면 컷의 정당성이 사라진다."""
    boundary = payload["_boundary"]
    assert boundary["gap_m"] > 0
    assert boundary["first_excluded_m"] > payload["scope"]["radius_m"]
    assert boundary["last_included_m"] <= payload["scope"]["radius_m"]


@pytest.mark.parametrize("radius", [800.0, 900.0, 1000.0, 1100.0])
def test_반경을_흔들어도_같은_집합이다(payload: dict, radius: float):
    """`_boundary` 가 주장하는 성질을 실제로 다시 계산해 확인한다."""
    scope = payload["scope"]
    expected = {p["id"] for p in payload["points"]}
    actual = {
        p["id"]
        for p in payload["points"]
        if haversine_m(scope["center_lat"], scope["center_lon"], p["lat"], p["lon"])
        <= radius
    }
    assert actual == expected, f"반경 {radius}m 에서 집합이 달라진다"


# --- 확정된 정책과 어긋나지 않는다 ------------------------------------------


def test_민간건물이_후보에_없다(payload: dict):
    """M-25. 민간 임시 안전거점은 MVP 제외다."""
    allowed = {"학교", "관공서"}
    offenders = [
        f"{p['label']}({p['facility']['category']})"
        for p in payload["points"]
        if p["facility"]["category"] not in allowed
    ]
    assert not offenders, (
        "공공시설이 아닌 후보가 있다. M-25 는 민간건물을 MVP 에서 제외한다: "
        + ", ".join(offenders)
    )


def test_집합이_닫혔다고_표시돼_있다(payload: dict):
    assert payload["_status"] == "CLOSED"
    assert payload["_owner"] == "C · 박윤후"
    assert payload["points"], "후보가 0곳이면 EVACUATE 가 항상 NO_SAFE_POINT 가 된다"


def test_소유자_확인_상태가_적혀_있다(payload: dict):
    """누가 닫았는지와 소유자 확인 여부를 숨기지 않는다.

    소유자가 아닌 사람이 닫아두고 확인받지 않은 상태(`PENDING`)로 두면 실패한다.
    """
    assert payload["_owner_ack"] in {"PENDING", "CONFIRMED"}
    assert payload["_owner_ack"] == "CONFIRMED", (
        f"{payload['_closed_by']} 가 닫았고 소유자 {payload['_owner']} 확인이 남아 있다"
    )


def test_id가_고유하고_형식이_같다(payload: dict):
    ids = [p["id"] for p in payload["points"]]
    assert len(ids) == len(set(ids)), "id 가 중복된다"
    assert ids == sorted(ids), "id 가 거리순으로 정렬돼 있지 않다"
    for point_id in ids:
        assert point_id.startswith("SP-"), f"{point_id} 가 SP- 로 시작하지 않는다"


def test_목적지_목록과_id가_겹치지_않는다(payload: dict, destinations: dict):
    """두 목록은 도달 대상이 다르다(RT-12). id 가 겹치면 조용히 섞인다."""
    mine = {p["id"] for p in payload["points"]}
    theirs = {p["id"] for p in destinations["points"]}
    assert not (mine & theirs), f"id 충돌: {sorted(mine & theirs)}"


def test_좌표_품질을_검증됨으로_표기하지_않는다(payload: dict):
    """원천기관 재확인 전이다. 등급을 올려 적으면 여기서 실패한다."""
    for point in payload["points"]:
        assert point["coordinate_quality"] == "SOURCE_PROVIDED_UNVERIFIED"


# --- 아직 정하지 않은 것을 슬쩍 정해두지 않았는지 ---------------------------


def test_후보에_순위나_위험값이_없다(payload: dict):
    """순위·relative_risk 는 경로 엔진의 결정이다. 여기서 미리 넣지 않는다."""
    forbidden = {"rank", "relative_risk", "excluded", "excluded_by", "priority"}
    for point in payload["points"]:
        leaked = forbidden & set(point) | forbidden & set(point["facility"])
        assert not leaked, (
            f"{point['id']} 에 아직 정하지 않은 정책 필드가 있다: {sorted(leaked)}"
        )
