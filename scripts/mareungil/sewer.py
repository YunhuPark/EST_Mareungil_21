"""2022년 하수관로 수위 원본에서 사건 창 구간만 뽑아 10분 격자로 올린다.

원본 월별 CSV 12개는 합쳐서 약 7.28GB라 전량 적재하지 않는다. 청크로 읽으면서
강남·서초 + 사건 창에 해당하는 행만 남긴 뒤 집계한다.
"""

from __future__ import annotations

import pandas as pd

from . import config as C

SEWER_COLUMNS = ["unq_no", "se_cd", "se_nm", "measured_at", "level", "signal_status"]
CHUNK_ROWS = 2_000_000


def _slot_to_event(windows: pd.DataFrame) -> pd.Series:
    """사건 창을 10분 슬롯 -> event_id 룩업 시리즈로 편다.

    창끼리 겹치면 먼저 시작한 사건이 이긴다(E13 과 E14 처럼 붙어 있는 경우).
    """
    pieces = []
    for row in windows.sort_values("window_start").itertuples():
        slots = pd.date_range(row.window_start, row.window_end, freq=C.BIN)
        pieces.append(pd.Series(row.event_id, index=slots))
    lookup = pd.concat(pieces)
    return lookup[~lookup.index.duplicated(keep="first")].sort_index()


def extract_10min(windows: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """사건 창에 걸리는 강남·서초 수위를 10분 격자로 집계한다."""
    lookup = _slot_to_event(windows)
    keep_months = {ts.strftime("%Y%m") for ts in lookup.index}

    frames = []
    for path in sorted(C.RAW_SEWER_DIR.glob("*.csv")):
        month = path.stem[-6:]
        if month not in keep_months:
            continue
        kept = 0
        for chunk in pd.read_csv(
            path,
            encoding=C.RAW_ENCODING,
            header=0,
            names=SEWER_COLUMNS,
            skiprows=1,
            chunksize=CHUNK_ROWS,
            dtype=str,
        ):
            chunk = chunk[chunk["se_cd"].isin(C.SEWER_DISTRICT_CODES)]
            if chunk.empty:
                continue
            chunk["measured_at"] = pd.to_datetime(chunk["measured_at"], format="mixed")
            chunk["time_10m"] = chunk["measured_at"].dt.floor(C.BIN)
            chunk["event_id"] = chunk["time_10m"].map(lookup)
            chunk = chunk[chunk["event_id"].notna()]
            if chunk.empty:
                continue
            chunk["level"] = pd.to_numeric(chunk["level"], errors="coerce")
            frames.append(
                chunk[
                    ["unq_no", "se_cd", "time_10m", "event_id", "measured_at", "level", "signal_status"]
                ]
            )
            kept += len(chunk)
        if verbose:
            print(f"  {path.name}: 사건 창 내 {kept:,}행")

    raw = pd.concat(frames, ignore_index=True)
    raw = raw.sort_values(["unq_no", "measured_at"])

    good = raw["signal_status"].astype(str).str.strip() == "통신양호"
    raw = raw.assign(signal_good=good.astype(int))

    agg = raw.groupby(["unq_no", "se_cd", "event_id", "time_10m"], as_index=False).agg(
        level_last=("level", "last"),
        level_mean=("level", "mean"),
        level_max=("level", "max"),
        level_min=("level", "min"),
        sample_count=("level", "size"),
        signal_good_rate=("signal_good", "mean"),
    )
    agg["district"] = agg["se_cd"].map(C.DISTRICT_NAME_BY_SEWER_CODE)
    return agg


#: 10분 구간의 공칭 판독 수. `sample_count` 를 이 값으로 나눠 충족도를 낸다.
NOMINAL_SAMPLES = 10


def observed_rate(snap: pd.DataFrame) -> float:
    """`data_quality.observed_rate` — 센서별 샘플링 충족도의 평균 (C-28 / O-16).

    **이진 판정이 아니다.** 예전 식은 `sample_count >= 10` 인 센서의 비율이었는데
    `sample_count` 의 중앙값이 정확히 10 이라 컷오프가 분포의 최빈값 바로 위에 놓였다.
    판독 하나 빠진 센서(9개)가 통째로 미관측이 되어, 실제 손실 약 10% 가 지표에서
    44포인트 하락으로 증폭됐다. 그래서 데모 사건에서 DQ-03 이 시점의 88.1% 에서
    발화해 `DS-S1`·`DS-S6` 의 `SAFE` 와 어긋났다. 근거는 `docs/DECISIONS.md` 2.5.

    **DQ-03 임계 0.70 은 바꾸지 않았다.** 계산식만 바꿨다.

    이 함수가 정본이며 `build_demo_fixtures.py`(전체 재생성)와
    `refresh_observed_rate.py`(재학습 없는 갱신) 두 경로가 같이 쓴다. 한쪽에만
    식을 두면 다음 전체 재생성에서 값이 조용히 되돌아간다 — C-20 에서 실제로 밟았다.

    Args:
        snap: 한 시점의 센서 행들. `sample_count` 열이 있어야 한다.
              **호출 전에 `evaluate.prepare()` 로 걸러진 집합을 넘긴다** —
              `sensors_active` 와 분모가 같아야 하기 때문이다.
    """
    return round(float((snap["sample_count"] / NOMINAL_SAMPLES).clip(upper=1.0).mean()), 3)


def reindex_full_grid(agg: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    """센서 x 사건창의 10분 격자를 빠짐없이 채운다.

    원본에는 통신 두절 구간의 행이 아예 없다. 그대로 shift 하면 t+30 이
    실제로는 t+120 인 행과 짝지어지므로, 완전 격자로 되채운 뒤 결측으로 남긴다.
    `observed` 가 0 인 행은 학습에서 뺀다.
    """
    windows = windows.set_index("event_id")
    out = []
    for (unq_no, event_id), part in agg.groupby(["unq_no", "event_id"], sort=False):
        w = windows.loc[event_id]
        grid = pd.date_range(w.window_start, w.window_end, freq=C.BIN, name="time_10m")
        part = part.set_index("time_10m").reindex(grid)
        part["unq_no"] = unq_no
        part["event_id"] = event_id
        part["se_cd"] = part["se_cd"].ffill().bfill()
        part["district"] = part["district"].ffill().bfill()
        part["observed"] = part["level_last"].notna().astype(int)
        part["sample_count"] = part["sample_count"].fillna(0).astype(int)
        out.append(part.reset_index())
    full = pd.concat(out, ignore_index=True)
    return full.sort_values(["unq_no", "time_10m"]).reset_index(drop=True)
