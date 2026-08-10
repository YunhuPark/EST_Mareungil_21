"""사건 규모 조건부 임계.

    python scripts/run_severity_threshold.py [horizon]

§13.1 에서 상위 n% 정책이 실패한 뒤 진단했더니, 목표 오경보율을 내는 임계는
선행강우에 따라 0.05 에서 0.65 까지 크게 달라진다. 하나의 고정 임계로 두
국면을 모두 맞출 수 없었던 것이다.

그래서 임계를 선행 6시간 강우의 계단함수로 만든다. 규모는 예측시점에 이미
관측된 값이므로 미래 정보를 쓰지 않는다.

임계는 학습 사건의 **out-of-fold** 확률에서 맞춘다. in-sample 확률로 맞추면
임계가 낙관적으로 잡혀 실전에서 오경보가 폭발한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import config as C
from mareungil import evaluate as E
from mareungil import policy as P
from run_models import FEATURES, TAG, build_xy, make_models

SEVERITY = "rain_past_360m_mm"


def out_of_fold_probs(df: pd.DataFrame, horizon: int) -> tuple[pd.DataFrame, pd.Series]:
    """사건 단위 GroupKFold 로 학습 구간의 out-of-fold 확률을 만든다."""
    train = df[df["split"] == "train"]
    evalset = E.prepare(train, horizon, TAG)
    x, y = evalset[FEATURES], evalset["y_true"]

    oof = pd.Series(np.nan, index=evalset.index)
    base = make_models()["histgb"]
    for tr_idx, te_idx in GroupKFold(n_splits=5).split(x, y, evalset["event_id"]):
        model = clone(base)
        model.fit(x.iloc[tr_idx], y.iloc[tr_idx])
        oof.iloc[te_idx] = model.predict_proba(x.iloc[te_idx])[:, 1]
    return evalset, oof


def main() -> None:
    horizon = int(sys.argv[1]) if len(sys.argv) > 1 else C.PRIMARY_HORIZON_MIN
    df = pd.read_parquet(C.DATASET_PARQUET)
    print(f"=== 사건 규모 조건부 임계  t+{horizon}분 / {TAG} ===\n")

    print("[1/3] 학습 사건 out-of-fold 확률 생성 (사건 단위 5-fold)")
    train_eval, oof = out_of_fold_probs(df, horizon)

    thr_table = P.fit_severity_thresholds(train_eval, oof, C.FPR_BUDGET, SEVERITY)
    print("  선행 6시간 강우 구간 -> 임계")
    for r in thr_table.itertuples():
        hi = "inf" if np.isinf(r.hi) else f"{r.hi:.0f}"
        print(f"    {max(r.lo, 0):5.0f} ~ {hi:>5s} mm   n={r.n:>7,}   ->  {r.threshold:.3f}")
    print()

    print("[2/3] 전체 학습자료로 최종 모델 학습")
    x, y = build_xy(df[df["split"] == "train"], horizon)
    model = make_models()["histgb"]
    model.fit(x, y)

    ev = {s: E.prepare(df[df["split"] == s], horizon, TAG) for s in ("val", "test")}
    prob = {
        s: pd.Series(model.predict_proba(e[FEATURES])[:, 1], index=e.index)
        for s, e in ev.items()
    }
    # 비교 대상: val 에서 고른 고정 임계 (기존 방식)
    fixed_thr = E.recall_at_fpr_budget(E.sweep(ev["val"], prob["val"]), C.FPR_BUDGET)["threshold"]

    # 학습 OOF 임계는 최종 모델 확률과 스케일이 다르다(OOF 모델은 사건 4/5 로만 학습).
    # 스케일을 맞춘 공정 비교를 위해 같은 최종 모델 확률로 val 에서 다시 맞춘 표도 만든다.
    thr_table_val = P.fit_severity_thresholds(ev["val"], prob["val"], C.FPR_BUDGET, SEVERITY)
    print("  (참고) 같은 모델 확률로 val 에서 맞춘 임계")
    for r in thr_table_val.itertuples():
        hi = "inf" if np.isinf(r.hi) else f"{r.hi:.0f}"
        print(f"    {max(r.lo, 0):5.0f} ~ {hi:>5s} mm   n={r.n:>7,}   ->  {r.threshold:.3f}")
    print()

    print(f"[3/3] 비교  (목표 오경보율 {C.FPR_BUDGET})\n")
    policies = {
        "고정임계(val)": lambda s: P.fire_absolute(prob[s], fixed_thr),
        "규모조건부(학습OOF)": lambda s: P.apply_severity_threshold(
            prob[s], ev[s][SEVERITY], thr_table
        ),
        "규모조건부(val)": lambda s: P.apply_severity_threshold(
            prob[s], ev[s][SEVERITY], thr_table_val
        ),
    }
    rows = []
    for name, fn in policies.items():
        for s in ("val", "test"):
            pred = fn(s)
            rep = E.classification_report(ev[s], pred)
            rows.append(
                {
                    "정책": name,
                    "split": s,
                    "상승전이재현율": rep["rise_recall"],
                    "오경보율": rep["stable_low_fpr"],
                    "목표대비오차": abs(rep["stable_low_fpr"] - C.FPR_BUDGET),
                    "경보해제율": rep["fall_release_rate"],
                    "전체F1": rep["overall_f1"],
                }
            )
    result = pd.DataFrame(rows)
    print(result.round(4).to_string(index=False))

    test = result[result["split"] == "test"].set_index("정책")
    print("\n  test 결과 요약 (목표 오경보율 %.2f)" % C.FPR_BUDGET)
    for name in policies:
        row = test.loc[name]
        print(
            f"    {name:20s} 오경보 {row['오경보율']:.4f}(오차 {row['목표대비오차']:.4f})"
            f"   상승전이재현율 {row['상승전이재현율']:.4f}"
        )

    result.to_csv(
        C.OUT_DIR / f"severity_threshold_t{horizon}.csv", index=False, encoding="utf-8-sig"
    )
    thr_table.to_csv(
        C.OUT_DIR / f"severity_threshold_curve_t{horizon}.csv", index=False, encoding="utf-8-sig"
    )
    print(f"\n-> {C.OUT_DIR / f'severity_threshold_t{horizon}.csv'}")


if __name__ == "__main__":
    main()
