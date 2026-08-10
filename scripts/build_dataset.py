"""마른길 모델링 데이터셋 빌더.

    python scripts/build_dataset.py events    # 강우사건·대조 무강우일 정의
    python scripts/build_dataset.py sewer     # 사건 창 수위 10분 집계
    python scripts/build_dataset.py rain      # 사건 창 강우 10분 정리
    python scripts/build_dataset.py all

원본(raw)은 절대 수정하지 않는다. 산출물은 data_unified/processed/v2 에만 쓴다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import config as C
from mareungil import rainfall as R
from mareungil import sewer as S


def step_events() -> pd.DataFrame:
    print("[events] 2022년 강우 로딩")
    rain = R.load_rainfall_2022()
    regional = R.regional_rain_series(rain)

    events = R.define_events(regional, rain)
    dry = R.define_dry_controls(regional, events)
    windows = pd.concat([events, dry], ignore_index=True).sort_values("window_start")
    windows = windows.reset_index(drop=True)

    C.OUT_DIR.mkdir(parents=True, exist_ok=True)
    windows.to_csv(C.EVENT_WINDOWS_CSV, index=False, encoding="utf-8-sig")

    span = (windows["window_end"] - windows["window_start"]).sum()
    print(f"[events] 강우사건 {len(events)}개 + 대조 무강우일 {len(dry)}개")
    print(f"[events] 총 창 기간 {span}, -> {C.EVENT_WINDOWS_CSV}")
    return windows


def load_windows() -> pd.DataFrame:
    windows = pd.read_csv(C.EVENT_WINDOWS_CSV, encoding="utf-8-sig")
    for col in ("window_start", "window_end", "rain_start", "rain_end"):
        windows[col] = pd.to_datetime(windows[col])
    return windows


def step_sewer(windows: pd.DataFrame) -> pd.DataFrame:
    print("[sewer] 월별 원본에서 사건 창 추출 (약 7.28GB 스캔)")
    agg = S.extract_10min(windows)
    print(f"[sewer] 관측된 10분 슬롯 {len(agg):,}행, 센서 {agg['unq_no'].nunique()}개")

    full = S.reindex_full_grid(agg, windows)
    observed = int(full["observed"].sum())
    print(f"[sewer] 완전 격자 {len(full):,}행 중 관측 {observed:,}행 "
          f"({observed / len(full):.1%})")

    full.to_parquet(C.SEWER_10MIN_PARQUET, index=False)
    print(f"[sewer] -> {C.SEWER_10MIN_PARQUET}")
    return full


def step_rain(windows: pd.DataFrame) -> pd.DataFrame:
    print("[rain] 사건 창 강우 정리")
    rain = R.load_rainfall_2022()
    lookup = S._slot_to_event(windows)
    rain = rain[rain["time_10m"].isin(lookup.index)].copy()
    rain["event_id"] = rain["time_10m"].map(lookup)

    wide = rain.pivot_table(
        index=["event_id", "time_10m"], columns="gauge_code", values="rain_10m_mm"
    )
    wide.columns = [f"rain_gauge_{c}" for c in wide.columns]
    wide = wide.reset_index()

    by_district = rain.pivot_table(
        index=["event_id", "time_10m"], columns="district", values="rain_10m_mm",
        aggfunc=["mean", "max"],
    )
    by_district.columns = [f"rain_{d}_{a}_mm" for a, d in by_district.columns]
    by_district = by_district.reset_index()

    out = wide.merge(by_district, on=["event_id", "time_10m"], how="outer")
    out.to_parquet(C.RAIN_10MIN_PARQUET, index=False)
    print(f"[rain] {len(out):,}행 -> {C.RAIN_10MIN_PARQUET}")
    return out


def step_features() -> pd.DataFrame:
    from mareungil import features as F

    print("[features] 수위·강우 결합")
    sewer = pd.read_parquet(C.SEWER_10MIN_PARQUET)
    rain = pd.read_parquet(C.RAIN_10MIN_PARQUET)

    df = F.assign_split(sewer)
    df = F.add_rain_features(df, rain)
    df = F.add_level_features(df)
    df = F.add_time_features(df)
    df = F.add_targets(df)

    df, sensor_stats = F.select_modelable_sensors(df)
    dropped = sensor_stats[~sensor_stats["modelable"]]
    print(f"[features] 모델링 센서 {df['unq_no'].nunique()}개, 제외 {len(dropped)}개")
    if len(dropped):
        print("           제외:", ", ".join(dropped["unq_no"]))
    sensor_stats.to_csv(C.OUT_DIR / "sensor_screening.csv", index=False, encoding="utf-8-sig")

    for q in C.HIGH_LEVEL_QUANTILES:
        thresholds = F.fit_high_level_thresholds(df, q)
        df = F.add_high_level_targets(df, thresholds, q)

    df.to_parquet(C.DATASET_PARQUET, index=False)
    print(f"[features] {len(df):,}행 x {df.shape[1]}열 -> {C.DATASET_PARQUET}")

    summary = df.groupby("split").agg(
        rows=("level_last", "size"),
        observed=("observed", "sum"),
        events=("event_id", "nunique"),
        sensors=("unq_no", "nunique"),
    )
    print("\n[features] 분할 요약")
    print(summary.to_string())
    return df


def main() -> None:
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    if step in ("events", "all"):
        windows = step_events()
    elif step in ("sewer", "rain"):
        windows = load_windows()
    if step in ("sewer", "all"):
        step_sewer(windows)
    if step in ("rain", "all"):
        step_rain(windows)
    if step in ("features", "all"):
        step_features()


if __name__ == "__main__":
    main()
