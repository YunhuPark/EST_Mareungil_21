"""기존 픽스처의 `data_quality.observed_rate` 만 다시 계산한다. **모델을 다시 학습하지 않는다.**

    python scripts/refresh_observed_rate.py            # 미리보기
    python scripts/refresh_observed_rate.py --write    # 실제로 저장

왜 별도 스크립트인가
--------------------
`refresh_area_risk.py` 와 같은 이유다. `build_demo_fixtures.py` 는 모델을 **재학습**한다.
관측률 계산식(C-28)만 바꿨는데 재학습을 돌리면 센서별 확률까지 다시 만들어지고, 그건
픽스처 README 가 "실제 모델 출력"이라고 보증한 값이다. 관측률은 그 확률과 **무관한
데이터 품질 지표**이므로 확률을 건드리지 않고 다시 계산하는 것이 맞다.

두 경로 모두 `mareungil/sewer.py` 의 `observed_rate()` 를 쓴다. 한쪽에만 식을 두면 다음
전체 재생성에서 값이 조용히 되돌아간다 — C-20 에서 실제로 밟았다. 분모를 맞추기 위해
`evaluate.prepare()` 필터도 생성기와 똑같이 적용한다(`observed==1` 인 행만 남는다).

C-28 (O-16 확정)
----------------
    before   (sample_count >= 10).mean()             # 이진 판정
    after    (sample_count / 10).clip(upper=1).mean()

`sample_count` 의 중앙값이 정확히 10 이라 예전 컷오프는 분포의 최빈값 바로 위에 놓였다.
판독 하나 빠진 센서(9개)가 통째로 미관측이 되어, 실제 손실 약 10% 가 지표에서 44포인트
하락으로 증폭됐다. 근거와 수치는 `docs/DECISIONS.md` 2.5 에 있다.

`risk_E1_no_data.json` 처럼 센서가 0개인 픽스처는 건드리지 않는다 — 계산할 원본 행이 없고
`observed_rate: 0.0` 은 "무데이터"를 뜻하는 의도된 값이다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import config as C
from mareungil import evaluate as E
from mareungil import sewer
from run_models import TAG

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contracts" / "fixtures"

#: 데모 픽스처가 재생하는 사건과 주 horizon. `build_demo_fixtures.py` 와 같아야 한다.
EVENT = "E13_0808"
HORIZON = 30


def targets() -> list[tuple[Path, list[str]]]:
    """(파일, `RiskAssessment` 본문까지의 경로) 목록."""
    found: list[tuple[Path, list[str]]] = [
        (path, []) for path in sorted(FIXTURES.glob("risk_*.json"))
    ]
    found += [(path, ["risk"]) for path in sorted((FIXTURES / "demo").glob("*.json"))]
    return found


def dig(payload: dict, path: list[str]) -> dict:
    for key in path:
        payload = payload[key]
    return payload


def main(argv: list[str]) -> int:
    write = "--write" in argv

    df = pd.read_parquet(C.DATASET_PARQUET)
    # 생성기와 **같은 필터**를 쓴다. `sensors[]` 에 실리는 집합과 분모가 같아야 한다.
    ev = E.prepare(df[df["event_id"] == EVENT], HORIZON, TAG)
    print(f"사건 {EVENT} · 공칭 판독 수 {sewer.NOMINAL_SAMPLES}/10분 "
          f"· prepare() 통과 {len(ev):,}행\n")

    changed = skipped = 0
    for path, inner in targets():
        payload = json.loads(path.read_text(encoding="utf-8"))
        body = dig(payload, inner)
        quality = body.get("data_quality")
        if quality is None or not body.get("sensors"):
            skipped += 1
            continue

        asof = pd.Timestamp(body["asof"]).tz_localize(None)
        snap = ev[ev["time_10m"] == asof]
        if snap.empty:
            print(f"  건너뜀 {path.relative_to(ROOT).as_posix()} — {asof} 원본 행 없음")
            skipped += 1
            continue

        before = quality["observed_rate"]
        after = sewer.observed_rate(snap)
        quality["observed_rate"] = after

        # 분모가 `sensors_active` 와 어긋나면 조용히 틀린 값이 저장된다. 여기서 막는다.
        active = quality.get("sensors_active")
        if active is not None and active != len(snap):
            print(f"  !! {path.relative_to(ROOT).as_posix()} — "
                  f"sensors_active={active} 인데 snap 은 {len(snap)}행이다. 중단한다.")
            return 1

        rel = path.relative_to(ROOT).as_posix()
        print(f"  {rel}")
        print(f"      asof={asof} 센서 {len(snap)}개 · {before} -> {after}")

        if write:
            # 두 생성기 모두 끝에 개행을 넣지 않는다. 여기서 넣으면 다음
            # `make.ps1 fixtures` 마다 헛 diff 가 난다.
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        changed += 1

    print(f"\n{'저장함' if write else '미리보기'} — 대상 {changed}건 · 건너뜀 {skipped}건")
    if not write:
        print("실제로 쓰려면 --write 를 붙인다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
