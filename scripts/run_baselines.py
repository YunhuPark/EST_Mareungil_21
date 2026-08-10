"""기준선 평가. 모델을 붙이기 전에 넘어야 할 바닥을 확정한다.

    python scripts/run_baselines.py [horizon]

지속성 기준선은 정의상 RISE 를 하나도 못 잡고 STABLE_LOW 오경보도 0이다.
즉 (rise_recall=0, stable_low_fpr=0) 인 한 점이다. 모델은 이 점에서
오경보를 얼마나 지불하고 상승전이를 얼마나 사는지로 평가한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import config as C
from mareungil import evaluate as E

TAG = "p95"


def persistence(evalset: pd.DataFrame) -> pd.Series:
    """현재 고수위면 미래도 고수위."""
    return evalset["now_high"]


def rule_baseline(evalset: pd.DataFrame, rain_mm: float, rise_m: float) -> pd.Series:
    """지속성에 상승 규칙을 얹는다.

    최근 30분 누적강우가 rain_mm 이상이고 최근 30분 수위상승이 rise_m 이상이면
    지금 저수위여도 30분 뒤 고수위로 본다. 임계값 근거는 아래 sweep 로 고른다.
    """
    rising = (
        (evalset["rain_past_30m_mm"].fillna(0) >= rain_mm)
        & (evalset["level_delta_30m"].fillna(0) >= rise_m)
    )
    return ((evalset["now_high"] == 1) | rising).astype(int)


def main() -> None:
    horizon = int(sys.argv[1]) if len(sys.argv) > 1 else C.PRIMARY_HORIZON_MIN
    df = pd.read_parquet(C.DATASET_PARQUET)

    print(f"=== 기준선 평가  horizon=t+{horizon}분  기준={TAG} ===\n")

    for split in ("val", "test"):
        evalset = E.prepare(df[df["split"] == split], horizon, TAG)
        counts = evalset["regime"].value_counts()
        print(f"[{split}] 평가행 {len(evalset):,}")
        print("  국면 분포:", {k: int(v) for k, v in counts.items()})

        amb = int((evalset["regime"] == "AMBIGUOUS").sum())
        print(f"  AMBIGUOUS {amb:,}행({amb / len(evalset):.1%})은 임계 +-{C.HIGH_LEVEL_MARGIN} "
              f"밴드에 걸쳐 대표지표에서 제외")

        reports = {"persistence": E.classification_report(evalset, persistence(evalset))}

        # 규칙 기준선 임계 탐색은 학습 사건에서만 한다.
        if split == "val":
            train = E.prepare(df[df["split"] == "train"], horizon, TAG)
            best, best_score = None, -np.inf
            for rain_mm in (1.0, 3.0, 5.0, 10.0):
                for rise_m in (0.01, 0.03, 0.05, 0.10):
                    rep = E.classification_report(train, rule_baseline(train, rain_mm, rise_m))
                    # 오경보 5% 예산 안에서 상승전이 재현율을 최대화
                    if rep["stable_low_fpr"] <= 0.05 and rep["rise_recall"] > best_score:
                        best, best_score = (rain_mm, rise_m), rep["rise_recall"]
            print(f"  규칙 임계(학습에서 선택): 30분누적강우>={best[0]}mm, 30분상승>={best[1]}m")
            main.rule_params = best

        rain_mm, rise_m = main.rule_params
        reports["rule"] = E.classification_report(
            evalset, rule_baseline(evalset, rain_mm, rise_m)
        )

        table = E.compare(reports)
        print(table.round(4).to_string())

        reg = E.regression_report(df[df["split"] == split], horizon, df[df["split"] == split]["level_last"], TAG)
        print(f"  지속성 회귀: MAE {reg['mae']:.4f} | 고수위구간 {reg['mae_high_level']:.4f} "
              f"| 상위10%변동 {reg['mae_moved_top10pct']:.4f}")

        lead = E.onset_lead_time(evalset, rule_baseline(evalset, rain_mm, rise_m), horizon)
        if len(lead):
            caught = (lead["lead_min"] > 0).mean()
            print(f"  고수위 시작 {len(lead)}건 중 사전경보 {caught:.1%}, "
                  f"평균 선행 {lead.loc[lead['lead_min'] > 0, 'lead_min'].mean():.1f}분")
        print()

    # 센서별 편향 점검
    evalset = E.prepare(df[df["split"] == "test"], horizon, TAG)
    rain_mm, rise_m = main.rule_params
    ps = E.per_sensor(evalset, rule_baseline(evalset, rain_mm, rise_m))
    print("=== test 센서별 상승전이 재현율 (하위 8개) ===")
    print(ps.head(8).round(4).to_string(index=False))

    out = C.OUT_DIR / f"baseline_per_sensor_t{horizon}.csv"
    ps.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
