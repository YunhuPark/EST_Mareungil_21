"""경보 정책: 임계값 산출 방식과 경보해제.

두 가지를 다룬다.

1. 임계값 산출 방식. 고정 확률임계는 사건마다 오경보율이 흔들린다(val 4.7% ->
   test 2.9%). 이걸 결함으로 보고 상위 n% 방식과 강우량 구간별 방식을 만들어
   비교했는데, **둘 다 재현율만 잃었다.**

   흔들림은 결함이 아니었다. 고정임계는 확률이 높은 고강우 구간에 경보를 저절로
   몰아주는데, 물이 차오르는 순간이 실제로 몰려 있는 곳이 거기다. 구간마다
   오경보율을 똑같이 맞추라고 강제하면 그 배분이 깨진다.

   -> 결론은 `fire_absolute` 를 쓰는 것. 나머지 함수는 비교 근거로만 남긴다.
      자세한 기록은 설계안 §13.1.

2. 경보해제. `y_high` 만 학습하면 "지금 높은데 곧 내려간다"는 신호가 모델에 없다.
   현재 고수위 행만 따로 떼어 해제 전용 모델을 만든다(§13.2).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# --- 임계값 정책 ----------------------------------------------------------


def fire_absolute(prob: pd.Series, threshold: float) -> pd.Series:
    """고정 확률 임계. 비교 결과 이게 제일 낫다. 운영 정책은 이것으로 확정."""
    return (prob >= threshold).astype(int)


def fire_global_rate(prob: pd.Series, rate: float) -> pd.Series:
    """확률 상위 rate 비율만 울린다.

    임계를 확률값이 아니라 경보 발생비율로 고정한다. 사건 규모가 커져 확률이 전반적으로
    올라가도 울리는 행의 비율은 유지되므로 오경보율이 훨씬 덜 흔들린다.
    운영에서는 최근 구간의 확률 분위수로 같은 계산을 한다.
    """
    if prob.empty:
        return prob.astype(int)
    cut = prob.quantile(1 - rate)
    return (prob >= cut).astype(int)


def fire_per_sensor_rate(prob: pd.Series, sensor: pd.Series, rate: float) -> pd.Series:
    """센서별로 상위 rate 비율만 울린다.

    센서마다 기저 수위와 반응이 달라 전역 분위수는 특정 센서에 경보가 몰린다.
    센서별로 끊으면 경보가 고르게 퍼지지만, 조용한 센서에서도 억지로
    rate 만큼 울리게 되는 부작용이 있다.
    """
    out = pd.Series(0, index=prob.index, dtype=int)
    for _sid, idx in sensor.groupby(sensor).groups.items():
        part = prob.loc[idx]
        if part.empty:
            continue
        out.loc[idx] = (part >= part.quantile(1 - rate)).astype(int)
    return out


def tune_rate(
    prob: pd.Series, evalset: pd.DataFrame, target_fpr: float, mode: str = "global"
) -> float:
    """목표 오경보율을 내는 경보 발생비율(rate)을 찾는다. val 에서만 호출한다."""
    best, best_gap = 0.01, np.inf
    for rate in np.linspace(0.005, 0.30, 60):
        pred = (
            fire_global_rate(prob, rate)
            if mode == "global"
            else fire_per_sensor_rate(prob, evalset["unq_no"], rate)
        )
        stable_low = evalset["regime"] == "STABLE_LOW"
        fpr = pred[stable_low].mean() if stable_low.any() else np.nan
        gap = abs(fpr - target_fpr)
        if gap < best_gap:
            best, best_gap = float(rate), gap
    return best


# --- 사건 규모 조건부 임계 (비교용. 채택하지 않음) --------------------------
#
# 강우량 구간마다 목표 오경보율을 내는 임계가 크게 다르다. 선행 6시간 강우
# 0mm 구간은 0.05, 15mm 이상 구간은 0.6~0.7 이 필요하다. 그래서 구간별로 다른
# 임계를 쓰면 오경보율이 안정될 것으로 봤다.
#
# 실제로 오경보율 오차는 0.021 -> 0.010 으로 줄었지만 상승전이 재현율이
# 0.648 -> 0.376 으로 반토막 났다. 고정임계가 오경보 0.05 에서 0.773 을 내므로
# 더 쓰고 덜 잡는 셈이다. 채택하지 않는다.
#
# 남겨 두는 이유는 같은 시도를 반복하지 않기 위해서다. 설계안 §13.1 참고.


# 선행강우 구간(mm). 분위수로 나누면 안 된다. 행의 73.8%가 0mm 이라 분위수
# 경계가 0 근처로 뭉개져 구간이 2개로 붕괴한다(첫 시도가 그렇게 실패했다).
# 강우량으로서 의미 있는 고정 경계를 쓴다.
SEVERITY_EDGES = (-0.001, 0.001, 1.0, 5.0, 15.0, 40.0, np.inf)


def fit_severity_thresholds(
    evalset: pd.DataFrame,
    prob: pd.Series,
    target_fpr: float,
    severity_col: str = "rain_past_360m_mm",
    min_rows: int = 100,
) -> pd.DataFrame:
    """규모 구간별로 목표 오경보율을 내는 임계를 구한다.

    학습 사건에서 호출하되 반드시 out-of-fold 확률을 넘겨야 한다.
    in-sample 확률로 맞추면 임계가 낙관적으로 잡힌다.
    """
    sev = evalset[severity_col].fillna(0.0)
    stable_low = evalset["regime"] == "STABLE_LOW"

    rows = []
    for lo, hi in zip(SEVERITY_EDGES[:-1], SEVERITY_EDGES[1:]):
        part = (sev > lo) & (sev <= hi) & stable_low
        if part.sum() < min_rows:
            continue
        rows.append(
            {
                "lo": lo,
                "hi": hi,
                "n": int(part.sum()),
                "threshold": float(prob[part].quantile(1 - target_fpr)),
            }
        )
    return pd.DataFrame(rows)


def apply_severity_threshold(
    prob: pd.Series,
    severity: pd.Series,
    table: pd.DataFrame,
) -> pd.Series:
    """규모 구간에 해당하는 임계를 그대로 적용한다(계단함수).

    0mm 구간이 전체의 74%인 뾰족한 분포라 보간보다 계단이 안전하다.
    표에 없는 구간은 가장 가까운 쪽 임계를 쓴다.
    """
    sev = severity.fillna(0.0)
    thr = pd.Series(np.nan, index=prob.index)
    for row in table.itertuples():
        thr[(sev > row.lo) & (sev <= row.hi)] = row.threshold
    thr = thr.fillna(table["threshold"].iloc[-1])
    return (prob >= thr).astype(int)


# --- 경보해제 -------------------------------------------------------------


def combine(
    now_high: pd.Series,
    rise_fire: pd.Series,
    release_fire: pd.Series,
) -> pd.Series:
    """상승 모델과 해제 모델을 하나의 경보 상태로 합친다.

    현재 저수위면 상승 모델이 경보를 켤지 정하고,
    현재 고수위면 해제 모델이 경보를 끌지 정한다.
    해제 모델이 없던 기존 정책은 현재 고수위면 무조건 경보 유지였고,
    그래서 FALL 국면 해제율이 0 이었다.
    """
    alarm = pd.Series(0, index=now_high.index, dtype=int)
    low = now_high == 0
    alarm[low] = rise_fire[low]
    alarm[~low] = (1 - release_fire[~low]).astype(int)
    return alarm
