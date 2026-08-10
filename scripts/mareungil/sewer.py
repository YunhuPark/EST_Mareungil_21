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
