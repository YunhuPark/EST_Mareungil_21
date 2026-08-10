"""임계값 안정화 + 경보해제 모델.

    python scripts/run_alarm_policy.py [horizon]

두 실험을 한 번에 돌린다.

  실험 1  임계값 정책 3종의 val -> test 오경보율 전이 안정성
  실험 2  해제 전용 모델을 붙였을 때 FALL 국면 해제율

프로토콜은 run_models.py 와 같다. 임계와 경보 발생비율은 val 에서만 고른다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import config as C
from mareungil import evaluate as E
from mareungil import policy as P
from run_models import FEATURES, TAG, RANDOM_STATE, build_xy, make_models


def fit_rise_model(df: pd.DataFrame, horizon: int):
    x, y = build_xy(df[df["split"] == "train"], horizon)
    model = make_models()["histgb"]
    model.fit(x, y)
    return model


def fit_release_model(df: pd.DataFrame, horizon: int):
    """현재 고수위인 행만 학습. 타깃은 '30분 뒤 내려간다'.

    상승 모델과 분리하는 이유는 두 문제의 조건부 분포가 다르기 때문이다.
    y_high 하나로 학습하면 현재 수위가 높다는 사실이 예측을 지배해서
    감수 국면의 신호가 묻힌다.
    """
    y_col = f"y_high_{TAG}_t{horizon}"
    now_col = f"is_high_now_{TAG}"
    d = df[
        (df["split"] == "train")
        & (df["observed"] == 1)
        & df[y_col].notna()
        & (df[now_col] == 1)
    ]
    x = d[FEATURES]
    y = (d[y_col].astype(int) == 0).astype(int)  # 1 = 내려간다 = 해제해야 한다
    model = HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.06,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.15,
        class_weight="balanced",
        random_state=RANDOM_STATE,
    )
    model.fit(x, y)
    print(f"[release] 학습 {len(d):,}행 (현재 고수위), 하강 비율 {y.mean():.2%}")
    return model


def main() -> None:
    horizon = int(sys.argv[1]) if len(sys.argv) > 1 else C.PRIMARY_HORIZON_MIN
    df = pd.read_parquet(C.DATASET_PARQUET)
    print(f"=== 경보 정책 실험  t+{horizon}분 / {TAG} ===\n")

    rise_model = fit_rise_model(df, horizon)
    release_model = fit_release_model(df, horizon)

    ev = {s: E.prepare(df[df["split"] == s], horizon, TAG) for s in ("val", "test")}
    rise_prob, release_prob = {}, {}
    for s, e in ev.items():
        rise_prob[s] = pd.Series(rise_model.predict_proba(e[FEATURES])[:, 1], index=e.index)
        release_prob[s] = pd.Series(release_model.predict_proba(e[FEATURES])[:, 1], index=e.index)

    # ---------- 실험 1: 임계값 정책 ----------
    print("\n### 실험 1. 임계값 정책의 val -> test 전이")
    print(f"목표 오경보율 {C.FPR_BUDGET:.3f} 을 val 에서 맞춘 뒤 test 에 그대로 적용\n")

    curve = E.sweep(ev["val"], rise_prob["val"])
    abs_thr = E.recall_at_fpr_budget(curve, C.FPR_BUDGET)["threshold"]
    global_rate = P.tune_rate(rise_prob["val"], ev["val"], C.FPR_BUDGET, "global")
    sensor_rate = P.tune_rate(rise_prob["val"], ev["val"], C.FPR_BUDGET, "per_sensor")

    policies = {
        "absolute": lambda s: P.fire_absolute(rise_prob[s], abs_thr),
        "global_rate": lambda s: P.fire_global_rate(rise_prob[s], global_rate),
        "per_sensor_rate": lambda s: P.fire_per_sensor_rate(
            rise_prob[s], ev[s]["unq_no"], sensor_rate
        ),
    }
    print(f"  고정임계 {abs_thr:.3f} | 상위n%(전체) {global_rate:.3f} "
          f"| 상위n%(센서별) {sensor_rate:.3f}\n")

    rows = []
    for name, fn in policies.items():
        rep_v = E.classification_report(ev["val"], fn("val"))
        rep_t = E.classification_report(ev["test"], fn("test"))
        rows.append(
            {
                "policy": name,
                "val_fpr": rep_v["stable_low_fpr"],
                "test_fpr": rep_t["stable_low_fpr"],
                "fpr_drift": abs(rep_t["stable_low_fpr"] - rep_v["stable_low_fpr"]),
                "val_rise_recall": rep_v["rise_recall"],
                "test_rise_recall": rep_t["rise_recall"],
            }
        )
    t1 = pd.DataFrame(rows).sort_values("fpr_drift")
    print(t1.round(4).to_string(index=False))
    print("\n  fpr_drift 가 작을수록 운영에서 예측 가능한 정책이다.")

    # ---------- 실험 2: 경보해제 ----------
    print("\n\n### 실험 2. 해제 모델을 붙였을 때")
    # 실험 1 결과 rate 계열이 absolute 를 재현율·오경보율 양쪽에서 이기지 못했다.
    # fpr_drift 만 작을 뿐이므로 상승 판정은 기존 absolute 정책을 그대로 쓴다.
    best_policy = "absolute"
    print(f"  상승 판정은 {best_policy} 정책으로 고정 (실험 1 참고)\n")

    # 해제 임계도 val 에서만 고른다. 위험한 오해제(STABLE_HIGH 를 풀어버림)에 예산을 둔다.
    FALSE_RELEASE_BUDGET = 0.05
    best_thr, best_recall = None, -np.inf
    for thr in np.linspace(0.05, 0.95, 91):
        rel = (release_prob["val"] >= thr).astype(int)
        alarm = P.combine(ev["val"]["now_high"], policies[best_policy]("val"), rel)
        rep = E.classification_report(ev["val"], alarm)
        false_release = 1 - rep["stable_high_recall"]
        if false_release <= FALSE_RELEASE_BUDGET and rep["fall_release_rate"] > best_recall:
            best_thr, best_recall = float(thr), rep["fall_release_rate"]

    rows = []
    for label, use_release in (("해제모델 없음", False), ("해제모델 적용", True)):
        for s in ("val", "test"):
            rel = (
                (release_prob[s] >= best_thr).astype(int)
                if use_release
                else pd.Series(0, index=ev[s].index)
            )
            alarm = P.combine(ev[s]["now_high"], policies[best_policy](s), rel)
            rep = E.classification_report(ev[s], alarm)
            rows.append(
                {
                    "정책": label,
                    "split": s,
                    "상승전이재현율": rep["rise_recall"],
                    "오경보율": rep["stable_low_fpr"],
                    "경보해제율": rep["fall_release_rate"],
                    "오해제율": 1 - rep["stable_high_recall"],
                    "전체F1": rep["overall_f1"],
                }
            )
    t2 = pd.DataFrame(rows)
    print(f"  해제 임계 {best_thr:.2f} (val 에서 오해제 예산 {FALSE_RELEASE_BUDGET} 안에서 선택)\n")
    print(t2.round(4).to_string(index=False))

    out = C.OUT_DIR / f"alarm_policy_t{horizon}.csv"
    t2.to_csv(out, index=False, encoding="utf-8-sig")
    t1.to_csv(C.OUT_DIR / f"threshold_policy_t{horizon}.csv", index=False, encoding="utf-8-sig")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
