"""목적지 지정 지점 목록(`RT-14`) — O-13 이 열려 있는 동안 이 파일이 지키는 것.

이 파일은 **좌표가 맞는지 검사하지 않는다.** 좌표가 실제 그 장소인지는 지도를
보고 사람이 확인하는 일이고(O-13), 테스트가 대신할 수 없다. 여기가 지키는 것은
그보다 좁은 두 가지다.

1. **파일이 스스로에 대해 하는 말이 서로 어긋나지 않는다.** 좌표 품질을 올려
   적으려면 출처가 있어야 하고, 다 올렸으면 파일과 문서가 함께 닫혀야 한다.
2. **좌표에서 유도되는 값이 좌표와 같다.** `distance_from_center_m` 은 기록이
   아니라 계산 결과다. 좌표를 고치고 여기를 안 고치면 두 값이 갈라진다.

깨뜨리면 빨개지는 것(CLAUDE.md 8절):

- 근거 없이 `coordinate_quality` 를 `MAP_VERIFIED` 로 바꾸면 출처 검사가 실패한다.
- 5개를 다 확인해놓고 `_status: DRAFT` 로 두면 상태 검사가 실패한다.
- 파일만 닫고 CLAUDE.md 의 O-13 줄을 남겨두면 문서 일치 검사가 실패한다.
- 좌표를 옮기고 `distance_from_center_m` 을 그대로 두면 거리 검사가 실패한다.
- 범위 밖 지점을 넣으면(RT-15) 범위 검사가 실패한다.
- 차단 여부나 순위를 여기에 미리 적어두면(RT-17) 정책 누출 검사가 실패한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mareungil.area_risk import haversine_m  # noqa: E402

DESTINATIONS = ROOT / "contracts" / "destinations.json"
SAFE_POINTS = ROOT / "contracts" / "safe_points.json"

#: 좌표 품질 등급. `safe_points.json` 의 `SOURCE_PROVIDED_UNVERIFIED`(전달 자료를
#: 그대로 옮긴 것)와 **다른 축이다.** 여기 좌표는 손으로 찍은 근사값이라 사람이
#: 지도에서 대조한 것만 `MAP_VERIFIED` 가 된다.
APPROX = "APPROX_UNVERIFIED"
VERIFIED = "MAP_VERIFIED"
QUALITIES = {APPROX, VERIFIED}


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(DESTINATIONS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def points(payload: dict) -> list[dict]:
    return payload["points"]


# --- 목록의 모양 -------------------------------------------------------------


def test_지점이_비어_있지_않다(points: list[dict]):
    """F-19. 목적지는 필수 선택이다. 목록이 비면 아무도 아무것도 못 고른다."""
    assert points, "지정 지점이 0개면 목적지를 고를 수 없다(F-19)"


def test_필수_필드가_다_있고_타입이_맞다(points: list[dict]):
    for point in points:
        for key in ("id", "label", "coordinate_quality", "distance_from_center_m"):
            assert key in point, f"{point.get('id', '?')} 에 {key} 가 없다"
        assert isinstance(point["lat"], (int, float)), f"{point['id']} lat 이 숫자가 아니다"
        assert isinstance(point["lon"], (int, float)), f"{point['id']} lon 이 숫자가 아니다"
        assert point["label"].strip(), f"{point['id']} 라벨이 비어 있다"


def test_id와_라벨이_고유하고_형식이_같다(points: list[dict]):
    ids = [p["id"] for p in points]
    labels = [p["label"] for p in points]
    assert len(ids) == len(set(ids)), "id 가 중복된다"
    assert len(labels) == len(set(labels)), "라벨이 중복된다 — 사용자가 둘을 구분할 수 없다"
    for point_id in ids:
        assert point_id.startswith("GN-"), f"{point_id} 가 GN- 로 시작하지 않는다"


def test_안전거점과_id가_겹치지_않는다(points: list[dict]):
    """RT-12. 두 목록은 도달 대상이 다르다. id 가 겹치면 조용히 섞인다.

    `tests/test_safe_points.py` 에 같은 검사가 있지만 그쪽은 대피시설 원본 CSV 가
    없으면 파일째 건너뛴다. 목적지 쪽에서도 한 번 본다.
    """
    if not SAFE_POINTS.exists():
        pytest.skip("safe_points.json 이 없다")
    theirs = {p["id"] for p in json.loads(SAFE_POINTS.read_text(encoding="utf-8"))["points"]}
    mine = {p["id"] for p in points}
    assert not (mine & theirs), f"id 충돌: {sorted(mine & theirs)}"


# --- 좌표에서 유도되는 값 ----------------------------------------------------


def test_모든_지점이_경로_범위_안에_있다(payload: dict, points: list[dict]):
    """RT-15. 범위 밖 지점은 목록에 넣지 않는다."""
    scope = payload["scope"]
    for point in points:
        distance = haversine_m(
            scope["center_lat"], scope["center_lon"], point["lat"], point["lon"]
        )
        assert distance <= scope["radius_m"], (
            f"{point['id']} {point['label']} 가 범위 밖이다: "
            f"{distance:.1f}m > {scope['radius_m']}m"
        )


def test_기록된_거리가_좌표에서_계산한_값과_같다(payload: dict, points: list[dict]):
    """`distance_from_center_m` 은 유도값이다. 좌표를 고치면 여기도 따라와야 한다."""
    scope = payload["scope"]
    for point in points:
        distance = haversine_m(
            scope["center_lat"], scope["center_lon"], point["lat"], point["lon"]
        )
        assert round(distance, 1) == point["distance_from_center_m"], (
            f"{point['id']} 의 distance_from_center_m 이 좌표와 다르다: "
            f"기록 {point['distance_from_center_m']} vs 계산 {distance:.1f}"
        )


def test_좌표가_서울_안에_있다(points: list[dict]):
    """위경도를 뒤집어 넣거나 자릿수를 흘리면 여기서 먼저 걸린다."""
    for point in points:
        assert 37.4 <= point["lat"] <= 37.7, f"{point['id']} lat 이 서울 밖이다"
        assert 126.7 <= point["lon"] <= 127.3, f"{point['id']} lon 이 서울 밖이다"


# --- 좌표 품질과 출처 (O-13 의 본체) ----------------------------------------


def test_좌표_품질이_정의된_등급이다(points: list[dict]):
    for point in points:
        assert point["coordinate_quality"] in QUALITIES, (
            f"{point['id']} 의 좌표 품질 {point['coordinate_quality']} 은 "
            f"정의된 등급이 아니다: {sorted(QUALITIES)}"
        )


def test_검증됨으로_올리려면_출처가_있어야_한다(points: list[dict]):
    """등급만 올리고 근거를 안 적으면 '검증됐다'가 빈 말이 된다.

    O-13 은 좌표를 확인하는 일이지 필드값을 바꾸는 일이 아니다. 무엇을 보고
    확인했는지가 파일에 남아야 나중에 다시 따라갈 수 있다.
    """
    for point in points:
        if point["coordinate_quality"] != VERIFIED:
            continue
        source = point.get("source")
        assert isinstance(source, dict), f"{point['id']} 이 {VERIFIED} 인데 source 가 없다"
        for key in ("name", "checked_on", "checked_by"):
            assert source.get(key), f"{point['id']} 의 source.{key} 가 비어 있다"


def test_미검증_지점에는_출처를_붙이지_않는다(points: list[dict]):
    """출처가 붙었는데 등급이 그대로면 둘 중 하나는 잘못 적힌 것이다."""
    for point in points:
        if point["coordinate_quality"] == APPROX:
            assert "source" not in point, (
                f"{point['id']} 에 출처가 있는데 등급이 {APPROX} 다. "
                f"확인했으면 {VERIFIED} 로 올리고, 아니면 출처를 지운다"
            )


# --- 파일과 문서가 같은 말을 한다 -------------------------------------------


def test_상태가_좌표_품질과_어긋나지_않는다(payload: dict, points: list[dict]):
    """5개를 다 확인했으면 파일을 닫고, 하나라도 남았으면 초안으로 둔다."""
    status = payload["_status"]
    assert status in {"DRAFT", "CLOSED"}, f"알 수 없는 상태: {status}"
    remaining = [p["id"] for p in points if p["coordinate_quality"] != VERIFIED]
    if remaining:
        assert status == "DRAFT", f"아직 확인 안 된 지점이 있는데 CLOSED 다: {remaining}"
    else:
        assert status == "CLOSED", (
            "5개 좌표가 모두 확인됐는데 파일이 DRAFT 다. O-13 을 닫는다"
        )


def test_닫았으면_누가_언제_닫았는지_적혀_있다(payload: dict):
    """`safe_points.json` 이 C-32 를 닫을 때 쓴 형식과 같다."""
    if payload["_status"] != "CLOSED":
        pytest.skip("아직 초안이다(O-13 열림)")
    for key in ("_closed_on", "_closed_by", "_owner_ack"):
        assert payload.get(key), f"{key} 가 없다"
    assert payload["_owner_ack"] == "CONFIRMED", (
        f"{payload['_closed_by']} 가 닫았고 소유자 {payload['_owner']} 확인이 남아 있다"
    )


def test_문서와_파일이_O_13_을_같은_상태로_적는다(payload: dict):
    """파일만 닫고 문서를 두면 발표 체크리스트가 거짓말을 하게 된다.

    CLAUDE.md 9절이 남은 OPEN 을 열거한다. 파일을 닫는 커밋에서 그 줄도 함께
    지워야 한다 — 이 검사가 그것을 강제한다.
    """
    claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    open_line = "- O-13 목적지 지정 지점 목록 확정"
    if payload["_status"] == "CLOSED":
        assert open_line not in claude_md, (
            "destinations.json 은 닫혔는데 CLAUDE.md 9절이 O-13 을 미확정으로 적고 있다"
        )
    else:
        assert open_line in claude_md, (
            "destinations.json 이 초안인데 CLAUDE.md 9절에 O-13 이 없다"
        )


# --- 아직 정하지 않은 것을 슬쩍 정해두지 않았는지 ---------------------------


def test_차단이나_순위를_목록에_적어두지_않았다(points: list[dict]):
    """RT-17. 등재는 안전 보장이 아니고, 차단은 재생 시각마다 공식정보가 정한다.

    O-07 이 "좌표 거리로 차단을 추정하지 않는다"로 닫혔다. 차단 여부가 이 파일에
    상수로 들어오면 그 결정을 우회하게 된다.
    """
    forbidden = {"blocked", "blocked_by", "rank", "priority", "relative_risk", "safe"}
    for point in points:
        leaked = forbidden & set(point)
        assert not leaked, (
            f"{point['id']} 에 아직 정하지 않은 정책 필드가 있다: {sorted(leaked)}"
        )
