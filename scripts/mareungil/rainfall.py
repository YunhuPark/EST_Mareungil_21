"""서울시 2022년 10분 강우 로딩과 사건 정의."""

from __future__ import annotations

import pandas as pd

from . import config as C

RAIN_COLUMNS = ["gauge_code", "gauge_name", "gu_code", "gu_name", "rain_10m_mm", "collected_at"]


def load_rainfall_2022(gauges_only: bool = True) -> pd.DataFrame:
    """월별 CP949 CSV 12개를 읽어 10분 격자에 올린다.

    원본 `자료수집 시각`은 :09 :19 ... :59 이고 일부 행은 초까지 붙어 있어
    format="mixed" 로 파싱한 뒤 floor 해야 한다. config.BIN 주석 참고.
    """
    frames = []
    for path in sorted(C.RAW_RAINFALL_DIR.glob("*.csv")):
        df = pd.read_csv(path, encoding=C.RAW_ENCODING)
        df.columns = RAIN_COLUMNS
        frames.append(df)
    rain = pd.concat(frames, ignore_index=True)

    rain["collected_at"] = pd.to_datetime(rain["collected_at"], format="mixed")
    rain["time_10m"] = rain["collected_at"].dt.floor(C.BIN)
    rain["rain_10m_mm"] = pd.to_numeric(rain["rain_10m_mm"], errors="coerce")

    if gauges_only:
        rain = rain[rain["gauge_code"].isin(C.RAIN_GAUGES)].copy()
        rain["district"] = rain["gauge_code"].map(C.RAIN_GAUGES)

    dup = rain.duplicated(["gauge_code", "time_10m"]).sum()
    if dup:
        raise ValueError(f"강우 10분 격자에 중복 키 {dup}건. 시각 규칙을 다시 확인할 것.")

    return rain.sort_values(["gauge_code", "time_10m"]).reset_index(drop=True)


def regional_rain_series(rain: pd.DataFrame) -> pd.DataFrame:
    """10분 격자별 지역 대표 강우. 사건 판정과 무강우 판정에 쓴다.

    관측소별 결측 시각이 서로 달라 max 를 대표값으로 쓴다. 한 관측소라도
    비를 기록하면 그 시각은 강우로 본다.
    """
    grid = rain.groupby("time_10m")["rain_10m_mm"].agg(
        rain_max_mm="max", rain_mean_mm="mean", gauge_count="count"
    )
    full = pd.date_range(
        pd.Timestamp("2022-01-01 00:00"), pd.Timestamp("2022-12-31 23:50"), freq=C.BIN
    )
    return grid.reindex(full).rename_axis("time_10m").reset_index()


def define_events(regional: pd.DataFrame, rain: pd.DataFrame) -> pd.DataFrame:
    """강우 사건 구간을 뽑는다.

    강우가 있는 10분 슬롯을 모으고, 무강우가 EVENT_DRY_GAP_HOURS 이상 이어지면
    별개 사건으로 끊는다. 누적강우가 EVENT_MIN_TOTAL_MM 미만인 덩어리는 버린다.
    """
    wet = regional[regional["rain_max_mm"].fillna(0) > 0].copy()
    gap = pd.Timedelta(hours=C.EVENT_DRY_GAP_HOURS)
    new_group = wet["time_10m"].diff() > gap
    wet["group"] = new_group.cumsum()

    rows = []
    for _gid, part in wet.groupby("group"):
        envelope = part["rain_max_mm"].sum()  # 슬롯별 최대의 합. 사건 크기 정렬용 상한.
        if envelope < C.EVENT_MIN_TOTAL_MM:
            continue
        rain_start, rain_end = part["time_10m"].min(), part["time_10m"].max()
        span = rain.loc[rain["time_10m"].between(rain_start, rain_end)]
        per_gauge = span.groupby("gauge_code")["rain_10m_mm"].sum()
        rows.append(
            {
                "event_id": None,
                "kind": "RAIN",
                "rain_start": rain_start,
                "rain_end": rain_end,
                "window_start": rain_start - pd.Timedelta(hours=C.EVENT_LEAD_HOURS),
                "window_end": rain_end + pd.Timedelta(hours=C.EVENT_TAIL_HOURS),
                # 실제 한 관측소가 기록한 최대 누적. 사건 규모는 이 값으로 읽는다.
                "max_gauge_total_mm": round(float(per_gauge.max()), 1),
                "mean_gauge_total_mm": round(float(per_gauge.mean()), 1),
                "envelope_total_mm": round(float(envelope), 1),
                "peak_10m_mm": round(float(part["rain_max_mm"].max()), 1),
                "duration_h": round((rain_end - rain_start).total_seconds() / 3600, 1),
                "rain_slots": int(len(part)),
            }
        )

    events = pd.DataFrame(rows).sort_values("rain_start").reset_index(drop=True)
    events["event_id"] = [f"E{i + 1:02d}_" + d.strftime("%m%d") for i, d in enumerate(events["rain_start"])]
    return events


def define_dry_controls(regional: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """대조 무강우일.

    당일과 직전 DRY_LOOKBACK_DAYS 일이 모두 무강우인 날만 고른다. 사건 창과
    겹치는 날은 제외한다. 정상 수위 분포와 오경보율 평가에 쓴다.
    """
    daily = regional.copy()
    daily["date"] = daily["time_10m"].dt.date
    per_day = daily.groupby("date").agg(
        rain_sum=("rain_max_mm", "sum"), observed=("gauge_count", "sum")
    )
    # 관측이 전혀 없는 날은 무강우로 볼 수 없다.
    per_day = per_day[per_day["observed"] > 0]

    dry_flags = (per_day["rain_sum"].fillna(0) == 0).astype(bool)
    ok = dry_flags.copy()
    for back in range(1, C.DRY_LOOKBACK_DAYS + 1):
        ok &= dry_flags.shift(back, fill_value=False)

    covered = set()
    for row in events.itertuples():
        for ts in pd.date_range(row.window_start.date(), row.window_end.date(), freq="D"):
            covered.add(ts.date())

    candidates = [pd.Timestamp(d) for d, good in ok.items() if good and d not in covered]
    # 무강우일은 160일 넘게 나온다. 전부 넣으면 정상 구간이 학습을 지배하므로
    # 계절 편향 없이 월별 상한만큼 고르게 뽑는다.
    picked: list[pd.Timestamp] = []
    for _month, group in pd.Series(candidates).groupby([d.month for d in candidates]):
        step = max(1, len(group) // C.DRY_DAYS_PER_MONTH)
        picked.extend(list(group)[::step][: C.DRY_DAYS_PER_MONTH])

    rows = []
    for start in sorted(picked):
        rows.append(
            {
                "event_id": "D" + start.strftime("%m%d"),
                "kind": "DRY",
                "rain_start": pd.NaT,
                "rain_end": pd.NaT,
                "window_start": start,
                "window_end": start + pd.Timedelta(hours=23, minutes=50),
                "max_gauge_total_mm": 0.0,
                "mean_gauge_total_mm": 0.0,
                "envelope_total_mm": 0.0,
                "peak_10m_mm": 0.0,
                "duration_h": 0.0,
                "rain_slots": 0,
            }
        )
    return pd.DataFrame(rows)
