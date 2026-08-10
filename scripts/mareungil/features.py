"""센서 x 10분 모델링 테이블 구성.

랙(과거)·리드(미래) 피처는 모두 (센서, 사건창) 안에서만 만든다. 완전 격자로
되채운 뒤 shift 하므로 결측 구간을 건너뛰어 잘못 짝지어지는 일이 없다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


def assign_split(df: pd.DataFrame) -> pd.DataFrame:
    """사건 단위 학습/검증/테스트 배정."""
    split = pd.Series("train", index=df.index)
    split[df["event_id"].isin(C.VAL_EVENTS)] = "val"
    split[df["event_id"].isin(C.TEST_EVENTS)] = "test"
    return df.assign(split=split)


def add_rain_features(sewer: pd.DataFrame, rain: pd.DataFrame) -> pd.DataFrame:
    """구 단위 강우를 붙이고 누적강우를 만든다.

    센서 공식 좌표가 없어 최근접 강우계 매칭은 아직 못 한다. 대신 센서가 속한
    구의 강우계 평균·최대를 쓴다. 좌표를 확보하면 여기에 최근접 피처를 더한다.
    """
    rain = rain.copy()
    keep = ["event_id", "time_10m"] + [c for c in rain.columns if c.startswith("rain_")]
    rain = rain[keep]

    out = sewer.merge(rain, on=["event_id", "time_10m"], how="left")

    # 센서가 속한 구의 강우를 그 센서의 강우로 본다.
    for stat in ("mean", "max"):
        gangnam = out.get(f"rain_강남_{stat}_mm")
        seocho = out.get(f"rain_서초_{stat}_mm")
        out[f"rain_local_{stat}_mm"] = np.where(
            out["district"].eq("강남"), gangnam, seocho
        )

    out = out.sort_values(["unq_no", "event_id", "time_10m"])
    grp = out.groupby(["unq_no", "event_id"], sort=False)["rain_local_mean_mm"]
    for minutes in C.RAIN_LOOKBACK_MIN:
        steps = minutes // 10
        out[f"rain_past_{minutes}m_mm"] = grp.transform(
            lambda s, n=steps: s.rolling(n, min_periods=1).sum()
        )
    out["rain_past_60m_max_10m_mm"] = out.groupby(
        ["unq_no", "event_id"], sort=False
    )["rain_local_max_mm"].transform(lambda s: s.rolling(6, min_periods=1).max())

    # 강우 시작 후 경과시간: 창 안에서 처음 비가 온 슬롯 기준.
    def _elapsed(s: pd.Series) -> pd.Series:
        wet = s.fillna(0) > 0
        if not wet.any():
            return pd.Series(np.nan, index=s.index)
        first = wet.idxmax()
        return (np.arange(len(s)) - s.index.get_loc(first)) * 10.0

    out["minutes_since_rain_start"] = out.groupby(
        ["unq_no", "event_id"], sort=False
    )["rain_local_mean_mm"].transform(_elapsed)
    out.loc[out["minutes_since_rain_start"] < 0, "minutes_since_rain_start"] = np.nan
    return out


def add_level_features(df: pd.DataFrame) -> pd.DataFrame:
    """과거 수위와 변화율."""
    df = df.sort_values(["unq_no", "event_id", "time_10m"])
    grp = df.groupby(["unq_no", "event_id"], sort=False)["level_last"]

    for minutes in C.LEVEL_LOOKBACK_MIN:
        steps = minutes // 10
        df[f"level_lag_{minutes}m"] = grp.shift(steps)
        df[f"level_delta_{minutes}m"] = df["level_last"] - df[f"level_lag_{minutes}m"]

    df["level_slope_30m"] = df["level_delta_30m"] / 30.0
    df["level_roll_max_60m"] = grp.transform(lambda s: s.rolling(6, min_periods=1).max())
    df["level_roll_mean_60m"] = grp.transform(lambda s: s.rolling(6, min_periods=1).mean())
    return df


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = df["time_10m"]
    return df.assign(
        hour=ts.dt.hour,
        minute_of_day=ts.dt.hour * 60 + ts.dt.minute,
        dayofweek=ts.dt.dayofweek,
        month=ts.dt.month,
    )


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    """회귀 타깃과 보조 타깃. 분류 타깃은 임계 계산 뒤에 붙인다."""
    df = df.sort_values(["unq_no", "event_id", "time_10m"])
    grp = df.groupby(["unq_no", "event_id"], sort=False)["level_last"]

    for minutes in C.HORIZONS_MIN:
        steps = minutes // 10
        df[f"y_level_t{minutes}"] = grp.shift(-steps)
        df[f"y_rise_t{minutes}"] = df[f"y_level_t{minutes}"] - df["level_last"]

    # 향후 30분 최대수위(다음 1~3 슬롯).
    df["y_level_max_next_30"] = grp.transform(
        lambda s: s.shift(-3).rolling(3, min_periods=1).max()
    )
    return df


def fit_high_level_thresholds(df: pd.DataFrame, quantile: float) -> pd.Series:
    """센서별 고수위 임계. 학습 사건의 관측행에서만 계산한다.

    검증·테스트 구간을 포함해 분위수를 잡으면 미래정보가 새어 들어간다.
    """
    train = df[(df["split"] == "train") & (df["observed"] == 1)]
    return train.groupby("unq_no")["level_last"].quantile(quantile)


def add_high_level_targets(df: pd.DataFrame, thresholds: pd.Series, quantile: float) -> pd.DataFrame:
    tag = f"p{int(quantile * 100)}"
    thr = df["unq_no"].map(thresholds)
    df[f"high_threshold_{tag}"] = thr
    df[f"is_high_now_{tag}"] = (df["level_last"] >= thr).astype("Int8")
    for minutes in C.HORIZONS_MIN:
        df[f"y_high_{tag}_t{minutes}"] = (df[f"y_level_t{minutes}"] >= thr).astype("Int8")
        df.loc[df[f"y_level_t{minutes}"].isna(), f"y_high_{tag}_t{minutes}"] = pd.NA
    return df


def select_modelable_sensors(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """학습기간 동적범위가 없는 센서를 걸러낸다.

    분해능이 0.01인데 변동폭이 그보다 몇 배 안 되는 센서는 분위수 초과가
    사실상 노이즈다. 걸러낸 목록은 함께 반환해 문서에 남긴다.
    """
    train = df[(df["split"] == "train") & (df["observed"] == 1)]
    stats = train.groupby("unq_no")["level_last"].agg(
        level_min="min", level_max="max", distinct="nunique", n="size"
    )
    stats["level_range"] = stats["level_max"] - stats["level_min"]
    stats["modelable"] = (
        (stats["level_range"] >= C.MIN_SENSOR_LEVEL_RANGE)
        & (stats["distinct"] >= C.MIN_SENSOR_DISTINCT_VALUES)
    )
    keep = set(stats.index[stats["modelable"]])
    return df[df["unq_no"].isin(keep)].copy(), stats.reset_index()
