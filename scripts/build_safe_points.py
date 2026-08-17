"""안전거점(`SAFE_POINT`) 후보 집합 생성.

    python scripts/build_safe_points.py           # 미리보기
    python scripts/build_safe_points.py --write   # contracts/safe_points.json 갱신
    python scripts/build_safe_points.py --check   # 커밋본과 일치하는지만 확인

대피시설 107곳에서 **경로 범위 안에 있는 것만** 남긴다. 범위는 새로 정하지 않고
`contracts/destinations.json` 의 `scope` 를 그대로 읽는다(RT-15 · O-09).

**이 스크립트가 하지 않는 것**을 먼저 적는다. 후보 사이의 순위를 매기지 않고,
`relative_risk` 를 계산하지 않고, 수용인원으로 거르지 않고, 시설 운영상태를 보지
않는다(M-32 는 여전히 고정 픽스처다). 그건 전부 경로 엔진의 일이며 여기서 정하면
CLAUDE.md 9절이 금지하는 "임의의 안전정책"이 된다. 여기서 닫는 것은 **어떤 시설이
후보 목록에 오르는가** 하나뿐이다.

거리는 CSV 의 `distance_from_gangnam_station_m` 열을 쓰지 않고 다시 계산한다. 그 열의
기준점(127.02762, 37.49794)과 `destinations.json` 의 범위 중심(127.0276, 37.4979)이
약 5m 어긋나 있어서, 둘을 섞으면 범위의 정본이 두 개가 된다.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil.area_risk import haversine_m, load_scope  # noqa: E402

SOURCE = (
    ROOT
    / "data_unified"
    / "processed"
    / "safe_route_v1"
    / "flood_shelters_107.csv"
)
OUT = ROOT / "contracts" / "safe_points.json"

#: 좌표 품질. `destinations.json` 의 `APPROX_UNVERIFIED` 와 **다른 등급**이다.
#: 저쪽은 사람이 지도를 보고 찍은 근사값이고, 이쪽은 배포 데이터셋이 실은 값을
#: 그대로 옮긴 것이다. 다만 원천기관·배포페이지·기준연도를 아직 재확인하지
#: 않았으므로 검증됨으로 표기하지 않는다.
COORDINATE_QUALITY = "SOURCE_PROVIDED_UNVERIFIED"

RULES = [
    "이 목록은 EVACUATE 의 도달 대상(SAFE_POINT) 후보다. MOVE 의 목적지는 destinations.json 이며 두 목록은 섞지 않는다.",
    "범위의 정본은 contracts/destinations.json 의 scope 다. 여기 실린 scope 는 사본이며 tests/test_safe_points.py 가 두 값이 같은지 확인한다.",
    "목록 등재는 안전 보장이 아니다. 이 시설로 가는 경로가 존재한다는 뜻도 아니다.",
    "후보 순위·relative_risk·수용인원 반영·시설 운영상태는 여기서 정하지 않는다. 경로 엔진이 정한다.",
    "M-32. 시설 상태로 후보를 빼는 것은 만석·폐쇄·접근 불가가 확인된 경우뿐이다. 확인되지 않은 상태는 제외 사유가 아니다.",
    "M-25. 민간건물 임시 안전거점은 MVP 제외다. 범위 안 시설은 전부 학교·관공서라 별도 제외 규칙이 필요 없다.",
]


def load_shelters() -> list[dict[str, str]]:
    """대피시설 원본을 읽는다.

    Raises:
        FileNotFoundError: 전달 자료가 없을 때. 안내 문구를 붙여 다시 던진다.
    """
    if not SOURCE.exists():
        raise FileNotFoundError(
            f"대피시설 원본이 없다: {SOURCE.relative_to(ROOT).as_posix()}\n"
            "data_unified/processed/safe_route_v1/ 전달 자료를 먼저 받는다."
        )
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build() -> dict[str, Any]:
    """범위 안 시설만 남긴 후보 집합을 만든다.

    Returns:
        `contracts/safe_points.json` 에 그대로 쓸 dict.
    """
    scope = load_scope()
    rows = load_shelters()

    measured = []
    for row in rows:
        lat, lon = float(row["YCORD"]), float(row["XCORD"])
        distance = haversine_m(scope["lat"], scope["lon"], lat, lon)
        measured.append((distance, row, lat, lon))

    # 거리 오름차순. 같은 거리가 나오면 원본 일련번호로 순서를 고정한다 —
    # 정렬이 흔들리면 id 가 흔들리고, id 가 흔들리면 픽스처가 조용히 깨진다.
    measured.sort(key=lambda item: (item[0], float(item[1]["R_SEQ_NO"])))

    inside = [m for m in measured if m[0] <= scope["radius_m"]]
    outside = [m for m in measured if m[0] > scope["radius_m"]]

    points = []
    for index, (distance, row, lat, lon) in enumerate(inside, start=1):
        points.append(
            {
                "id": f"SP-{index:03d}",
                "label": row["EQUP_NM"],
                "lat": lat,
                "lon": lon,
                "coordinate_quality": COORDINATE_QUALITY,
                "distance_from_center_m": round(distance, 1),
                "facility": {
                    "sigungu": row["SGG_NM"],
                    "category": row["GB_ACMD"],
                    "source_class": row["CD_GUBUN"],
                    "capacity": int(float(row["QTY_CPTY"])),
                    "address": row["LOC_SFPR_A"],
                    "source_seq": int(float(row["R_SEQ_NO"])),
                },
            }
        )

    nearest_outside = outside[0]
    return {
        "_status": "CLOSED",
        "_owner": "C · 박윤후",
        "_closed_on": "2026-08-17",
        # 런북 40행 표에서 이 자리(지정 지점·시설·경로 후보)의 소유자는 C 다.
        # 소유자가 직접 닫았으므로 별도 승인 절차가 없다.
        "_closed_by": "C · 박윤후",
        "_owner_ack": "CONFIRMED",
        "_closed_what": (
            "어떤 시설이 SAFE_POINT 후보 목록에 오르는가. 이것만 닫았다. "
            "순위·relative_risk·수용인원 반영·시설 운영상태 연동은 열려 있다."
        ),
        "_warning": (
            "등재는 안전 보장이 아니다. 원천기관·배포페이지·기준연도를 재확인하기 전에는 "
            "발표나 화면에서 검증된 시설로 표현하지 않는다."
        ),
        "_generator": "scripts/build_safe_points.py",
        "_source": {
            "file": SOURCE.relative_to(ROOT).as_posix(),
            "rows": len(rows),
            "source_status": "원천기관 재확인 전. 전달 자료의 열 이름을 그대로 옮겼다.",
        },
        "_rules": RULES,
        "_selection": {
            "criterion": "scope 중심에서 haversine 거리 <= scope.radius_m",
            "criterion_note": (
                "RT-15 · O-09 에서 이미 닫힌 경로 범위를 그대로 적용한 것이다. "
                "이 스크립트가 새로 정한 기준이 아니다."
            ),
            "kept": len(points),
            "dropped": len(outside),
        },
        # 컷이 임계 민감한지 아닌지를 숫자로 남긴다. 손으로 적으면 데이터가
        # 바뀌었을 때 조용히 거짓말이 되므로 계산해서 싣는다.
        "_boundary": {
            "last_included_m": round(inside[-1][0], 1),
            "first_excluded_m": round(nearest_outside[0], 1),
            "first_excluded_label": nearest_outside[1]["EQUP_NM"],
            "gap_m": round(nearest_outside[0] - inside[-1][0], 1),
            "_note": (
                "이 간격 안에서는 반경을 어떻게 잡아도 후보 집합이 같다. "
                "컷이 임계 민감하지 않다는 근거다."
            ),
        },
        "scope": {
            "center_label": scope["label"],
            "center_lat": scope["lat"],
            "center_lon": scope["lon"],
            "radius_m": scope["radius_m"],
            "_scope_note": "contracts/destinations.json 의 사본이다. 여기서 고치지 않는다.",
        },
        "points": points,
    }


def render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def summarize(payload: dict[str, Any]) -> None:
    scope = payload["scope"]
    boundary = payload["_boundary"]
    selection = payload["_selection"]
    print(
        f"범위 {scope['center_label']} 반경 {scope['radius_m']:.0f}m "
        f"— 후보 {selection['kept']}곳 / 제외 {selection['dropped']}곳"
    )
    for point in payload["points"]:
        facility = point["facility"]
        print(
            f"  {point['id']}  {point['label']:<12} {facility['sigungu']:<4} "
            f"{facility['category']:<4} 수용 {facility['capacity']:>5}  "
            f"{point['distance_from_center_m']:>6.1f}m"
        )
    print(
        f"  경계: 마지막 포함 {boundary['last_included_m']:.1f}m / "
        f"첫 제외 {boundary['first_excluded_label']} {boundary['first_excluded_m']:.1f}m "
        f"(간격 {boundary['gap_m']:.1f}m)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="파일에 쓴다")
    parser.add_argument("--check", action="store_true", help="커밋본과 다르면 1 을 반환한다")
    args = parser.parse_args()

    payload = build()
    text = render(payload)

    if args.check:
        if not OUT.exists():
            print(f"{OUT.relative_to(ROOT).as_posix()} 이 없다", file=sys.stderr)
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print(
                f"{OUT.relative_to(ROOT).as_posix()} 이 생성 결과와 다르다. "
                "python scripts/build_safe_points.py --write 로 다시 만든다.",
                file=sys.stderr,
            )
            return 1
        print("일치한다")
        return 0

    summarize(payload)
    if args.write:
        OUT.write_text(text, encoding="utf-8")
        print(f"\n{OUT.relative_to(ROOT).as_posix()} 갱신")
    else:
        print("\n미리보기다. 실제로 쓰려면 --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
