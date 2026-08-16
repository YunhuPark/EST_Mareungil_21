"""공식정보 가시성 필터 — 재생 시각에 **당시 알 수 있었던 것만** 남긴다.

M-36 이 정한 규칙 하나를 구현한다.

    available_time <= 재생 시각  인 항목만 판단에 쓴다.

왜 필요한가
-----------
2022-08-08 을 재생하면서 21:00 에 공개된 통제 정보를 20:00 화면에서 쓰면,
서비스가 **당시 사용자가 알 수 없었던 것을 안 것처럼** 보인다. 그 상태로 만든
행동·경로는 실제 상황에서 재현될 수 없고, 발표에서는 그것이 성능처럼 보인다.

두 시각을 구분하는 이유도 같다. `issued_at`·`since`·`observed_at` 은 **실제
발생·관측시각**(event_time)이고 `available_time` 은 **공개시각**이다. 통제가
20:00 에 시작됐더라도 20:40 에 공개됐다면 20:10 화면은 그것을 몰라야 한다.

`available_time` 이 `null` 이면 **쓰지 않는다.** 공개시각을 확인하지 못한
정보이므로 언제부터 알 수 있었는지 말할 수 없고, 확인하지 못한 것을 "처음부터
알고 있었다"로 취급하면 위 문제가 그대로 돌아온다. 대신 걸러진 개수를 함께
돌려주어 화면과 발표가 "이 시각에는 아직 공개되지 않은 정보가 있다"를 말할 수
있게 한다.

**`evacuation_order` 는 거르지 않는다.** 스냅샷 전체의 `asof` 가 이미 그 시각을
말하고 있고, 항목 배열이 아니라 스냅샷 자체의 값이기 때문이다.

순수 함수만 둔다. I/O·HTTP·파일 읽기를 하지 않는다(N-04 재현성).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#: available_time 을 가진 항목 배열. 이 셋만 시각으로 거른다.
TIMED_BLOCKS = ("alerts", "closures", "confirmed_flooding")


@dataclass(frozen=True)
class VisibilityResult:
    """필터 결과.

    Attributes:
        official: 걸러낸 뒤의 공식정보. 원본을 수정하지 않고 새 dict 를 만든다.
        hidden: 블록별로 숨겨진 항목 수. 0 이 아니면 "이 시각에는 아직
            공개되지 않은 정보가 있다"를 표시할 근거가 된다.
        undated: 블록별로 `available_time` 이 null 이라 뺀 항목 수. 위와 나눠
            세는 이유는 **"아직 안 알려졌다"와 "공개시각을 확인 못 했다"가 다른
            상태**이기 때문이다. 후자는 데이터 작업이 남았다는 뜻이다.
    """

    official: dict
    hidden: dict[str, int]
    undated: dict[str, int]

    @property
    def hidden_total(self) -> int:
        return sum(self.hidden.values())

    @property
    def undated_total(self) -> int:
        return sum(self.undated.values())


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def visible_at(official: dict, replay_time: str) -> VisibilityResult:
    """재생 시각 기준으로 공식정보 항목을 거른다.

    Args:
        official: `official_info@v1` 문서.
        replay_time: 재생 시각. `AssessResponse.clock.event_time` 과 같은 값이다.

    Returns:
        걸러낸 공식정보와 숨긴 개수.
    """
    now = _parse(replay_time)

    filtered = dict(official)
    hidden: dict[str, int] = {}
    undated: dict[str, int] = {}

    for block in TIMED_BLOCKS:
        items = official.get(block)
        if items is None:
            continue

        kept = []
        hidden_count = 0
        undated_count = 0

        for item in items:
            available = item.get("available_time")
            if available is None:
                undated_count += 1
                continue
            if _parse(available) <= now:
                kept.append(item)
            else:
                hidden_count += 1

        filtered[block] = kept
        hidden[block] = hidden_count
        undated[block] = undated_count

    return VisibilityResult(official=filtered, hidden=hidden, undated=undated)
