"""공식정보 가시성 필터 (M-36).

여기서 지키는 것은 하나다. **2022년 재생 화면은 그 시각에 공개돼 있던 정보만
쓴다.** 나중에 공개된 정보를 미리 쓰면 서비스가 당시 사용자가 알 수 없었던 것을
안 것처럼 보이고, 그 상태로 만든 판단은 실제 상황에서 재현되지 않는다.

아래 값은 전부 **필터 동작을 확인하려고 지어낸 합성값**이며 2022-08-08 의 사실이
아니다. 실제 값은 `contracts/fixtures/official/official_0808.json` 에만 들어간다.
"""

from __future__ import annotations

import json

import pytest

from contracts.validate import FIXTURE_DIR, ROOT, load_schemas
from services.decision import visible_at

REPLAY = "2022-08-08T20:10:00+09:00"


def _official() -> dict:
    """항목이 채워진 합성 공식정보. 세 블록의 시각을 일부러 어긋나게 뒀다."""
    return {
        "source": "fixture:shape_probe",
        "asof": REPLAY,
        "verification": "DEMO_FIXTURE",
        "evacuation_order": False,
        "alerts": [
            {
                "type": "SYNTHETIC_ALERT_PUBLISHED",
                "issued_at": "2022-08-08T19:30:00+09:00",
                "cleared_at": None,
                # 발령보다 20분 늦게 공개됐지만 재생 시각보다는 이르다 -> 보인다
                "available_time": "2022-08-08T19:50:00+09:00",
            },
            {
                "type": "SYNTHETIC_ALERT_FUTURE",
                "issued_at": "2022-08-08T20:00:00+09:00",
                "cleared_at": None,
                # 발생은 재생 시각 이전이지만 공개는 이후다 -> 아직 몰라야 한다
                "available_time": "2022-08-08T20:40:00+09:00",
            },
        ],
        "closures": [
            {
                "kind": "ROAD",
                "geom_ref": "SYNTHETIC-R-001",
                "mode": "BOTH",
                "since": "2022-08-08T20:00:00+09:00",
                "until": None,
                "available_time": "2022-08-08T20:10:00+09:00",
                "blocks_destination_ids": ["GN-001"],
            }
        ],
        "confirmed_flooding": [
            {
                "geom_ref": "SYNTHETIC-F-001",
                "observed_at": "2022-08-08T20:05:00+09:00",
                # 공개시각을 확인하지 못한 항목
                "available_time": None,
                "blocks_destination_ids": ["GN-002"],
            }
        ],
    }


def test_합성_공식정보가_계약을_통과한다():
    """이 파일의 합성값이 실제 계약 모양인지부터 확인한다.

    통과하지 못하는 모양으로 필터를 시험하면 필터가 무엇을 받을지 알 수 없다.
    """
    errors = list(load_schemas()["official_info"].iter_errors(_official()))
    assert errors == [], [e.message for e in errors]


def test_공개시각이_지난_정보만_남는다():
    result = visible_at(_official(), REPLAY)
    assert [a["type"] for a in result.official["alerts"]] == ["SYNTHETIC_ALERT_PUBLISHED"]
    assert result.hidden["alerts"] == 1


def test_발생시각이_아니라_공개시각으로_거른다():
    """두 시각이 어긋나는 항목이 이 규칙의 전부다.

    숨겨진 경보는 발생(20:00)이 재생 시각(20:10)보다 이르다. 발생시각으로
    걸렀다면 남았을 것이고, 그러면 M-36 이 막으려던 상태가 그대로 된다.
    """
    hidden = _official()["alerts"][1]
    assert hidden["issued_at"] < REPLAY < hidden["available_time"]
    assert visible_at(_official(), REPLAY).official["alerts"] == [
        _official()["alerts"][0]
    ]


def test_공개시각이_재생시각과_같으면_보인다():
    """경계는 '이하'다. 같은 시각에 공개된 정보를 숨기지 않는다."""
    result = visible_at(_official(), REPLAY)
    assert len(result.official["closures"]) == 1
    assert result.hidden["closures"] == 0


def test_공개시각을_모르는_항목은_쓰지_않는다():
    """null 을 '처음부터 알고 있었다'로 취급하지 않는다."""
    result = visible_at(_official(), REPLAY)
    assert result.official["confirmed_flooding"] == []
    assert result.undated["confirmed_flooding"] == 1
    # 숨김과 미확인은 다르게 센다.
    assert result.hidden["confirmed_flooding"] == 0


def test_시각이_지나면_보이기_시작한다():
    later = visible_at(_official(), "2022-08-08T20:40:00+09:00")
    assert len(later.official["alerts"]) == 2
    assert later.hidden_total == 0
    # 공개시각이 없는 항목은 시간이 지나도 계속 빠진다.
    assert later.undated_total == 1


def test_원본을_고치지_않는다():
    """N-04. 같은 입력을 다시 넣으면 같은 결과가 나와야 한다."""
    official = _official()
    before = json.dumps(official, sort_keys=True)
    visible_at(official, REPLAY)
    assert json.dumps(official, sort_keys=True) == before


def test_대피지시는_거르지_않는다():
    """항목 배열이 아니라 스냅샷 자체의 값이며 asof 가 이미 시각을 말한다."""
    official = {**_official(), "evacuation_order": True}
    assert visible_at(official, REPLAY).official["evacuation_order"] is True


def test_실제_픽스처에도_그대로_적용된다():
    """O-11 로 채운 실제 값에 필터가 실제로 걸린다.

    2026-08-16 확정 시각 21:40 기준이다. 그날 강남 도로 통제 보도는 **전부 22:01
    이후 송고**됐으므로 이 시각에 공개돼 있던 공식 통제는 0건이다. 데이터 누락이
    아니라 당시 시민이 알 수 있던 것의 실제 범위이며, 이 사실이 조용히 뒤집히면
    (누군가 available_time 을 발생시각으로 바꾸면) 여기가 빨개진다.
    """
    official = _real_official()
    result = visible_at(official, DEMO_REPLAY)

    assert result.official["closures"] == [], (
        "21:40 에 공개된 공식 통제가 생겼다. available_time 을 발생시각으로 "
        "바꾸지 않았는지 확인하라 (M-36)"
    )
    assert result.hidden["closures"] == 5
    # 양재천로는 구간·시각이 모두 미확인이라 공개시각도 특정할 수 없다.
    assert result.undated["closures"] == 1

    # 특보는 발효와 동시에 공표되므로 21:40 에 세 건이 보인다.
    assert [a["type"] for a in result.official["alerts"]] == [
        "호우주의보",
        "호우경보",
        "홍수주의보",
    ]


def _real_official() -> dict:
    return json.loads(
        (FIXTURE_DIR / "official" / "official_0808.json").read_text(encoding="utf-8")
    )


#: O-12 확정. 2022-08-08 21:40 — 강남구 1시간 최대 강수량이 관측된 시간대다.
DEMO_REPLAY = "2022-08-08T21:40:00+09:00"

DEMO_RESPONSES = sorted((FIXTURE_DIR / "demo").glob("*.assess_response.json"))


def test_검사할_데모_응답이_있다():
    assert DEMO_RESPONSES


@pytest.mark.parametrize("path", DEMO_RESPONSES, ids=lambda p: p.name.split(".")[0])
def test_공식정보_블록은_재생시각_필터를_거친_결과다(path):
    """M-36. 생성기가 공식정보 파일을 **통째로** 싣던 것을 막는다.

    이 검사가 없던 동안 `build_demo_assess_fixtures.py` 는 `official_0808.json` 을
    필터 없이 각 응답에 넣었다. 파일이 비어 있어 아무 일도 없었을 뿐이고, O-11 이
    실제 값을 채우는 순간 **11:00 화면이 22:01 에 보도된 통제를 아는** 상태가 됐다.

    필터를 빼면 DS-S1 의 closures 가 5건이 되면서 여기가 빨개진다.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    official = payload["official"]
    event_time = payload["clock"]["event_time"]

    source = json.loads((ROOT / official["_source_file"]).read_text(encoding="utf-8"))
    expected = visible_at(source, event_time).official

    assert official["asof"] == event_time, (
        "공식정보 스냅샷 시각이 재생 시각과 다르다. 한 화면이 두 시각을 말하게 된다"
    )
    for block in ("alerts", "closures", "confirmed_flooding"):
        assert official[block] == expected[block], f"{block} 이 필터 결과와 다르다"


@pytest.mark.parametrize("path", DEMO_RESPONSES, ids=lambda p: p.name.split(".")[0])
def test_재생시각_이후에_공개된_정보가_화면에_없다(path):
    """위 검사가 '필터를 돌렸다'를 본다면 이건 **결과가 실제로 맞는지**를 본다.

    필터 구현이 바뀌어도(예: 비교가 `>=` 로 뒤집혀도) 이 검사는 남는다.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    event_time = payload["clock"]["event_time"]

    for block in ("alerts", "closures", "confirmed_flooding"):
        for item in payload["official"].get(block, []):
            available = item.get("available_time")
            assert available is not None, (
                f"{path.name} {block}: 공개시각을 확인하지 못한 항목이 화면까지 갔다"
            )
            assert available <= event_time, (
                f"{path.name} {block}: {available} 에 공개된 정보가 "
                f"{event_time} 화면에 있다 (M-36)"
            )
