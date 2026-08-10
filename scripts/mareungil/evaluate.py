"""상승전이 중심 평가.

전체 F1 을 보고하면 안 되는 이유는 데이터에 이미 답이 있다. 지속성 기준선
(현재 고수위면 30분 뒤에도 고수위라고 예측)이 test 에서 F1 0.894 를 낸다.
대부분의 행에서 수위가 거의 안 움직이기 때문이다.

그래서 행을 네 국면으로 나눠서 본다. 지속성이 정의상 맞는 국면과 정의상
틀리는 국면을 섞어서 평균내면 모델의 기여가 보이지 않는다.

    현재\미래   저수위        고수위
    저수위      STABLE_LOW    RISE        <- 지속성이 틀린다. 잡아야 할 것.
    고수위      FALL          STABLE_HIGH
                ^ 지속성이 틀린다. 경보를 제때 풀어야 할 것.

핵심 지표는 두 개다.

    rise_recall        RISE 국면을 몇 % 잡았는가          (높을수록 좋다)
    stable_low_fpr     STABLE_LOW 를 몇 % 잘못 울렸는가   (낮을수록 좋다)

이 둘은 맞바꾸는 관계라 반드시 함께 본다. 하나만 보고하면 의미가 없다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

REGIMES = ("STABLE_LOW", "RISE", "FALL", "STABLE_HIGH")


def label_regime(
    level_now: pd.Series,
    level_future: pd.Series,
    threshold: pd.Series,
    margin: float = C.HIGH_LEVEL_MARGIN,
) -> pd.Series:
    """히스테리시스를 넣어 국면을 붙인다.

    측정 분해능이 0.01인데 학습 상승전이의 26%가 임계를 0.01만 넘는다.
    그 넘나듦은 물리적 사건이 아니라 잡음이므로 전이로 세면 안 된다.
    임계 +-margin 밴드를 두고, 밴드를 확실히 벗어난 것만 국면으로 인정한다.
    밴드에 걸친 행은 AMBIGUOUS 로 빼서 대표지표에서 제외하되 개수는 보고한다.
    """
    clear_low_now = level_now <= threshold - margin
    clear_high_now = level_now >= threshold + margin
    clear_low_fut = level_future <= threshold - margin
    clear_high_fut = level_future >= threshold + margin

    regime = pd.Series("AMBIGUOUS", index=level_now.index, dtype="object")
    regime[clear_low_now & clear_low_fut] = "STABLE_LOW"
    regime[clear_low_now & clear_high_fut] = "RISE"
    regime[clear_high_now & clear_low_fut] = "FALL"
    regime[clear_high_now & clear_high_fut] = "STABLE_HIGH"
    return regime


def prepare(
    df: pd.DataFrame, horizon: int, tag: str = "p95", margin: float = C.HIGH_LEVEL_MARGIN
) -> pd.DataFrame:
    """평가 가능한 행만 남기고 국면을 붙인다.

    관측이 없는 행과 타깃이 결측인 행은 평가 대상이 아니다.
    """
    y_col = f"y_high_{tag}_t{horizon}"
    now_col = f"is_high_now_{tag}"
    level_col = f"y_level_t{horizon}"
    out = df[
        (df["observed"] == 1) & df[y_col].notna() & df[now_col].notna() & df[level_col].notna()
    ].copy()
    out["y_true"] = out[y_col].astype(int)
    out["now_high"] = out[now_col].astype(int)
    out["regime"] = label_regime(
        out["level_last"], out[level_col], out[f"high_threshold_{tag}"], margin
    )
    return out


def _safe_div(num: float, den: float) -> float:
    return float(num) / float(den) if den else np.nan


def classification_report(evalset: pd.DataFrame, pred: pd.Series) -> dict:
    """국면별 지표와 전체 지표를 함께 낸다."""
    pred = pd.Series(np.asarray(pred).astype(int), index=evalset.index)
    y = evalset["y_true"]

    tp = int(((y == 1) & (pred == 1)).sum())
    fp = int(((y == 0) & (pred == 1)).sum())
    fn = int(((y == 1) & (pred == 0)).sum())
    tn = int(((y == 0) & (pred == 0)).sum())

    recall = _safe_div(tp, tp + fn)
    precision = _safe_div(tp, tp + fp)

    out = {
        "n": int(len(y)),
        "overall_recall": recall,
        "overall_precision": precision,
        "overall_f1": _safe_div(2 * precision * recall, precision + recall)
        if precision and recall
        else 0.0,
        "overall_fpr": _safe_div(fp, fp + tn),
    }

    # 국면별. 각 국면에서 "고수위라고 예측한 비율"이 뜻하는 바가 다르다.
    for regime in (*REGIMES, "AMBIGUOUS"):
        part = evalset["regime"] == regime
        n = int(part.sum())
        fired = int(pred[part].sum())
        out[f"{regime.lower()}_n"] = n
        out[f"{regime.lower()}_fire_rate"] = _safe_div(fired, n)

    # 핵심 두 지표에 읽기 쉬운 이름을 준다.
    out["rise_recall"] = out["rise_fire_rate"]  # RISE 를 고수위로 맞힌 비율
    out["stable_low_fpr"] = out["stable_low_fire_rate"]  # 조용한 구간 오경보율
    out["fall_release_rate"] = 1 - out["fall_fire_rate"]  # 내려갈 때 경보를 푼 비율
    out["stable_high_recall"] = out["stable_high_fire_rate"]
    return out


def headline(evalset: pd.DataFrame, prob: pd.Series, budget: float = C.FPR_BUDGET) -> dict:
    """모델 하나를 한 줄로 요약하는 대표지표.

    오경보 예산을 고정한 뒤 얻은 상승전이 재현율. 이 숫자 하나로 모델을 비교하고,
    전체 F1 은 참고로만 함께 싣는다.
    """
    curve = sweep(evalset, prob)
    best = recall_at_fpr_budget(curve, budget)
    if np.isnan(best["threshold"]):
        return {**best, "onset_catch_rate": np.nan, "median_lead_min": np.nan}

    pred = (pd.Series(np.asarray(prob, dtype=float), index=evalset.index) >= best["threshold"]).astype(int)
    rep = classification_report(evalset, pred)
    lead = onset_lead_time(evalset, pred, horizon=30)
    return {
        **best,
        "fall_release_rate": rep["fall_release_rate"],
        "overall_f1": rep["overall_f1"],
        "onset_catch_rate": float((lead["lead_min"] > 0).mean()) if len(lead) else np.nan,
        "median_lead_min": float(lead.loc[lead["lead_min"] > 0, "lead_min"].median())
        if (lead["lead_min"] > 0).any()
        else 0.0,
    }


def sweep(evalset: pd.DataFrame, prob: pd.Series, steps: int = 50) -> pd.DataFrame:
    """확률 임계를 훑어 rise_recall - stable_low_fpr 곡선을 만든다.

    운영 임계값은 이 표에서 오경보 예산을 정해 고른다. 모델 코드가 아니라
    정책으로 관리해야 하는 값이다.
    """
    prob = pd.Series(np.asarray(prob, dtype=float), index=evalset.index)
    rows = []
    for thr in np.linspace(0.01, 0.99, steps):
        rep = classification_report(evalset, (prob >= thr).astype(int))
        rows.append(
            {
                "threshold": round(float(thr), 4),
                "rise_recall": rep["rise_recall"],
                "stable_low_fpr": rep["stable_low_fpr"],
                "fall_release_rate": rep["fall_release_rate"],
                "overall_f1": rep["overall_f1"],
            }
        )
    return pd.DataFrame(rows)


def recall_at_fpr_budget(curve: pd.DataFrame, budget: float) -> dict:
    """오경보 예산 안에서 얻을 수 있는 최대 상승전이 재현율.

    모델 비교는 이 값으로 한다. 예산을 고정하지 않으면 재현율은 임계값만
    낮춰서 얼마든지 올릴 수 있다.
    """
    ok = curve[curve["stable_low_fpr"] <= budget]
    if ok.empty:
        return {"budget": budget, "rise_recall": np.nan, "threshold": np.nan}
    best = ok.loc[ok["rise_recall"].idxmax()]
    return {
        "budget": budget,
        "rise_recall": float(best["rise_recall"]),
        "stable_low_fpr": float(best["stable_low_fpr"]),
        "threshold": float(best["threshold"]),
    }


def regression_report(df: pd.DataFrame, horizon: int, pred: pd.Series, tag: str = "p95") -> dict:
    """회귀 지표. 전체 MAE 는 거의 안 움직이는 행에 지배되므로 함께 쪼갠다."""
    y_col = f"y_level_t{horizon}"
    mask = (df["observed"] == 1) & df[y_col].notna()
    d = df[mask]
    p = pd.Series(np.asarray(pred, dtype=float), index=df.index)[mask]
    err = (d[y_col] - p).abs()

    high = d[f"y_high_{tag}_t{horizon}"].astype("float") == 1
    # 실제로 움직인 행: 30분 상승량 상위 10%
    moved = d[f"y_rise_t{horizon}"].abs() >= d[f"y_rise_t{horizon}"].abs().quantile(0.90)

    return {
        "n": int(len(d)),
        "mae": float(err.mean()),
        "rmse": float(np.sqrt(((d[y_col] - p) ** 2).mean())),
        "mae_high_level": float(err[high].mean()),
        "mae_moved_top10pct": float(err[moved].mean()),
    }


def per_sensor(evalset: pd.DataFrame, pred: pd.Series) -> pd.DataFrame:
    """센서별 상승전이 재현율과 오경보율. 특정 센서 편향을 잡는다."""
    pred = pd.Series(np.asarray(pred).astype(int), index=evalset.index)
    rows = []
    for unq_no, part in evalset.groupby("unq_no"):
        rep = classification_report(part, pred.loc[part.index])
        rows.append(
            {
                "unq_no": unq_no,
                "n": rep["n"],
                "rise_n": rep["rise_n"],
                "rise_recall": rep["rise_recall"],
                "stable_low_fpr": rep["stable_low_fpr"],
                "overall_f1": rep["overall_f1"],
            }
        )
    return pd.DataFrame(rows).sort_values("rise_recall")


def onset_lead_time(evalset: pd.DataFrame, pred: pd.Series, horizon: int) -> pd.DataFrame:
    """고수위 구간이 시작되기 전에 모델이 얼마나 일찍 울렸는가.

    경로 재계산에 필요한 대응시간이 실제로 얼마나 확보되는지를 보는 지표다.
    분류 지표만으로는 이 값이 안 나온다.
    """
    pred = pd.Series(np.asarray(pred).astype(int), index=evalset.index)
    d = evalset.assign(pred=pred).sort_values(["unq_no", "event_id", "time_10m"])

    rows = []
    for (unq_no, event_id), part in d.groupby(["unq_no", "event_id"], sort=False):
        now = part["now_high"].to_numpy()
        fired = part["pred"].to_numpy()
        times = part["time_10m"].to_numpy()
        # 고수위 구간 시작점: 직전이 저수위이고 현재가 고수위
        onsets = np.where((now == 1) & (np.r_[0, now[:-1]] == 0))[0]
        for i in onsets:
            # 시작 전 최대 horizon 만큼 거슬러 보며 첫 경보 시점을 찾는다
            back = max(0, i - (horizon // 10))
            window = fired[back:i]
            if window.size and window.any():
                first = back + int(np.argmax(window))
                lead = (times[i] - times[first]) / np.timedelta64(1, "m")
            else:
                lead = 0.0
            rows.append(
                {"unq_no": unq_no, "event_id": event_id, "onset": times[i], "lead_min": float(lead)}
            )
    return pd.DataFrame(rows)


def compare(reports: dict[str, dict], keys: tuple[str, ...] = (
    "rise_recall", "stable_low_fpr", "fall_release_rate", "overall_f1",
)) -> pd.DataFrame:
    """여러 모델 리포트를 나란히 놓는다."""
    return pd.DataFrame({name: {k: rep[k] for k in keys} for name, rep in reports.items()}).T
