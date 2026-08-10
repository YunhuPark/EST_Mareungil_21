"""로지스틱 회귀와 HistGradientBoosting 비교.

    python scripts/run_models.py [horizon]

프로토콜은 고정이다. 이걸 어기면 보고한 숫자는 무효다.

    1. train 사건으로만 학습한다.
    2. 운영 임계값은 val 사건에서 오경보 예산 안의 상승전이 재현율을 최대화해 고른다.
    3. 그렇게 고정된 임계값을 test 에 그대로 적용한다. test 에서 임계를 다시 고르지 않는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import config as C
from mareungil import evaluate as E

TAG = "p95"
RANDOM_STATE = 42

# 시각 피처 중 month/dayofweek 는 제외한다. 분할이 사건 단위이고 사건은 특정 월에
# 몰려 있어서, 모델이 월만 보고 분할을 알아맞히는 지름길이 생긴다.
FEATURES = [
    "level_last", "level_mean", "level_max", "level_min",
    "level_lag_10m", "level_lag_30m", "level_lag_60m",
    "level_delta_10m", "level_delta_30m", "level_delta_60m",
    "level_slope_30m", "level_roll_max_60m", "level_roll_mean_60m",
    "rain_local_mean_mm", "rain_local_max_mm",
    "rain_past_10m_mm", "rain_past_30m_mm", "rain_past_60m_mm",
    "rain_past_120m_mm", "rain_past_360m_mm", "rain_past_60m_max_10m_mm",
    "minutes_since_rain_start",
    "sample_count", "signal_good_rate",
    "high_threshold_p95",  # 센서별 스케일. 학습 사건에서만 계산된 값이라 누출 아님
    "hour",
]


def build_xy(df: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.Series]:
    y_col = f"y_high_{TAG}_t{horizon}"
    d = df[(df["observed"] == 1) & df[y_col].notna()]
    return d[FEATURES], d[y_col].astype(int)


def make_models() -> dict[str, object]:
    return {
        "logistic": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000, class_weight="balanced", C=0.3, random_state=RANDOM_STATE
                    ),
                ),
            ]
        ),
        "histgb": HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.06,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            early_stopping=True,
            validation_fraction=0.15,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
    }


def main() -> None:
    horizon = int(sys.argv[1]) if len(sys.argv) > 1 else C.PRIMARY_HORIZON_MIN
    df = pd.read_parquet(C.DATASET_PARQUET)

    x_train, y_train = build_xy(df[df["split"] == "train"], horizon)
    print(f"=== t+{horizon}분 / {TAG} ===")
    print(f"학습 {len(x_train):,}행, 양성 {y_train.mean():.2%}, 피처 {len(FEATURES)}개\n")

    eval_val = E.prepare(df[df["split"] == "val"], horizon, TAG)
    eval_test = E.prepare(df[df["split"] == "test"], horizon, TAG)

    rows = []
    for name, model in make_models().items():
        model.fit(x_train, y_train)

        prob_val = pd.Series(
            model.predict_proba(eval_val[FEATURES])[:, 1], index=eval_val.index
        )
        prob_test = pd.Series(
            model.predict_proba(eval_test[FEATURES])[:, 1], index=eval_test.index
        )

        # 임계값은 val 에서만 고른다.
        curve = E.sweep(eval_val, prob_val)
        picked = E.recall_at_fpr_budget(curve, C.FPR_BUDGET)
        thr = picked["threshold"]
        if np.isnan(thr):
            print(f"[{name}] 오경보 예산 {C.FPR_BUDGET} 를 만족하는 임계값이 없다.")
            continue

        rep_val = E.classification_report(eval_val, (prob_val >= thr).astype(int))
        rep_test = E.classification_report(eval_test, (prob_test >= thr).astype(int))
        lead = E.onset_lead_time(eval_test, (prob_test >= thr).astype(int), horizon)
        caught = float((lead["lead_min"] > 0).mean()) if len(lead) else np.nan

        print(f"[{name}] val 에서 고른 임계값 {thr:.3f}")
        for split_name, rep in (("val", rep_val), ("test", rep_test)):
            print(
                f"  {split_name:4s}  상승전이재현율 {rep['rise_recall']:.4f}"
                f"  오경보율 {rep['stable_low_fpr']:.4f}"
                f"  경보해제율 {rep['fall_release_rate']:.4f}"
                f"  전체F1 {rep['overall_f1']:.4f}"
            )
        print(f"  test 고수위 시작 {len(lead)}건 중 사전경보 {caught:.1%}\n")

        rows.append(
            {
                "model": name,
                "threshold": round(thr, 3),
                "val_rise_recall": rep_val["rise_recall"],
                "val_fpr": rep_val["stable_low_fpr"],
                "test_rise_recall": rep_test["rise_recall"],
                "test_fpr": rep_test["stable_low_fpr"],
                "test_fall_release": rep_test["fall_release_rate"],
                "test_f1": rep_test["overall_f1"],
                "test_onset_catch": caught,
            }
        )

    # 기준선을 같은 표에 넣어 비교한다.
    for name, pred_fn in (
        ("persistence", lambda d: d["now_high"]),
        (
            "rule",
            lambda d: (
                (d["now_high"] == 1)
                | ((d["rain_past_30m_mm"].fillna(0) >= 1.0) & (d["level_delta_30m"].fillna(0) >= 0.01))
            ).astype(int),
        ),
    ):
        rep_v, rep_t = E.classification_report(eval_val, pred_fn(eval_val)), E.classification_report(
            eval_test, pred_fn(eval_test)
        )
        lead = E.onset_lead_time(eval_test, pred_fn(eval_test), horizon)
        rows.append(
            {
                "model": name,
                "threshold": np.nan,
                "val_rise_recall": rep_v["rise_recall"],
                "val_fpr": rep_v["stable_low_fpr"],
                "test_rise_recall": rep_t["rise_recall"],
                "test_fpr": rep_t["stable_low_fpr"],
                "test_fall_release": rep_t["fall_release_rate"],
                "test_f1": rep_t["overall_f1"],
                "test_onset_catch": float((lead["lead_min"] > 0).mean()) if len(lead) else np.nan,
            }
        )

    table = pd.DataFrame(rows).sort_values("test_rise_recall", ascending=False)
    print("=== 종합 (대표지표 = test 상승전이 재현율, 오경보 예산 %.2f) ===" % C.FPR_BUDGET)
    print(table.round(4).to_string(index=False))

    out = C.OUT_DIR / f"model_comparison_t{horizon}.csv"
    table.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
