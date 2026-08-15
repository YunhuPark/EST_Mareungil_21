"""데모 리플레이용 RiskAssessment 픽스처 생성.

    python scripts/build_demo_fixtures.py

2022-08-08 극한호우(테스트 사건) 창에서 네 국면의 시점을 골라, 그 시각의
**실제 모델 출력**을 계약 스키마 모양으로 저장한다. 값을 지어내지 않는 것이
목적이다 — 손으로 만든 확률로 UI를 맞춰두면 실제 모델을 붙일 때 다시 맞춰야 한다.

주의: 이 사건은 학습에서 완전히 제외된 test 사건이다. 아래 확률은 모델이
한 번도 본 적 없는 규모의 호우에 대해 내놓은 값이다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import area_risk
from mareungil import config as C
from mareungil import evaluate as E
from run_models import FEATURES, RANDOM_STATE, TAG, build_xy, make_models

HORIZON = 30
EVENT = "E13_0808"
THRESHOLD = 0.33  # val 사건에서 고른 운영 임계. run_models.py 참조
OUT = C.ROOT / "contracts" / "fixtures"

# 네 국면. demo_window 요약을 보고 고른 시점이며 근거를 함께 적는다.
SCENARIOS = {
    "S1_calm": ("2022-08-08 11:00", "평상 — 무강우, 고수위 센서 0개"),
    "S2_rising": ("2022-08-08 12:10", "강우 상승 — 상승전이 27건으로 창 내 최대. 아직 고수위 아님"),
    "S3_peak": ("2022-08-08 21:40", "사건 정점 — 평균 수위 1.82로 창 내 최대"),
    "S4_recovery": ("2022-08-09 09:00", "회복 — 무강우, 고수위 센서 절반 이하로 감소"),
}

# UI 이유 문장에 쓸 후보 피처. 값은 실제로 싣되 기여도(SHAP)는 해커톤 작업으로 남긴다.
DRIVER_FEATURES = ["rain_past_60m_mm", "rain_past_30m_mm", "level_delta_30m", "level_last"]


def grade_note() -> str:
    return (
        "area_risk.ai_risk_level 은 LOW/HIGH 두 값뿐이며 TH-04(O-01) 규칙으로 여기서 매긴다. "
        "②(의사결정)는 이 값을 그대로 받아 쓰고 확률에 임계를 다시 적용하지 않는다. "
        "최종 서비스 등급(SAFE/CAUTION/DANGER/SEVERE)은 별개 축이며 ②가 정한다."
    )


def main() -> None:
    df = pd.read_parquet(C.DATASET_PARQUET)
    meta = pd.read_csv(
        C.ROOT / "data_unified" / "metadata" / "sewer_sensors" / "sensor_metadata_2022_geocoded.csv",
        encoding="utf-8-sig",
    ).set_index("unq_no")

    train = df[df["split"] == "train"]
    x, y = build_xy(train, HORIZON)

    print("분류기 학습 (고수위 확률)")
    clf = make_models()["histgb"]
    clf.fit(x, y)

    print("회귀 학습 (예측 수위)")
    reg_mask = (train["observed"] == 1) & train[f"y_level_t{HORIZON}"].notna()
    reg = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.06, max_leaf_nodes=31,
        l2_regularization=1.0, early_stopping=True, random_state=RANDOM_STATE,
    )
    reg.fit(train.loc[reg_mask, FEATURES], train.loc[reg_mask, f"y_level_t{HORIZON}"])

    ev = E.prepare(df[df["event_id"] == EVENT], HORIZON, TAG)
    probs = {}
    for h in C.HORIZONS_MIN:
        m = make_models()["histgb"]
        hx, hy = build_xy(train, h)
        m.fit(hx, hy)
        probs[h] = pd.Series(m.predict_proba(ev[FEATURES])[:, 1], index=ev.index)
        print(f"  t+{h}분 확률 준비")

    ev = ev.assign(pred_level=reg.predict(ev[FEATURES]))

    OUT.mkdir(parents=True, exist_ok=True)
    index = []

    for name, (ts, why) in SCENARIOS.items():
        at = pd.Timestamp(ts)
        snap = ev[ev["time_10m"] == at]
        if snap.empty:
            print(f"  !! {name}: {ts} 에 관측 없음")
            continue

        sensors = []
        for row in snap.itertuples():
            p = {h: round(float(probs[h].loc[row.Index]), 4) for h in C.HORIZONS_MIN}
            now_high = bool(row.now_high)
            will_high = p[HORIZON] >= THRESHOLD
            transition = (
                "RISE" if (not now_high and will_high)
                else "FALL" if (now_high and not will_high)
                else "STABLE"
            )
            md = meta.loc[row.unq_no]
            sensors.append({
                "id": row.unq_no,
                "district": f"{row.district}구",
                "horizons": {str(h): {"high_level_p": p[h]} for h in C.HORIZONS_MIN},
                "is_high_now": now_high,
                "predicted_transition": transition,
                "predicted_level": round(float(row.pred_level), 3),
                "predicted_level_unit": "UNCONFIRMED",
                "physical_fill_ratio": None,
                "location": {
                    "lat": None if pd.isna(md.lat) else round(float(md.lat), 6),
                    "lon": None if pd.isna(md.lon) else round(float(md.lon), 6),
                    "quality": str(md.geocode_quality),
                },
                "observed_sample_count": int(row.sample_count),
            })

        # TH-04 / O-01. 집계 규칙은 scripts/mareungil/area_risk.py 한 곳에만 있다.
        # 예전 규칙("상위 25% 평균")은 회복 국면을 못 따라가 G0 에서 교체했다.
        area = area_risk.compute(sensors)
        first = snap.iloc[0]

        payload = {
            "_scenario": name,
            "_why_this_moment": why,
            "_note": grade_note(),
            "_source": "2022 서울시 공개데이터 리플레이. 이 사건은 학습에서 제외된 test 사건이다.",
            "asof": at.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
            "primary_horizon": HORIZON,
            "sensors": sensors,
            "area_risk": area,
            "drivers": [
                {
                    "feature": f,
                    "value": None if pd.isna(first[f]) else round(float(first[f]), 3),
                    "contribution": None,
                }
                for f in DRIVER_FEATURES
            ],
            "model": {
                "name": "histgb",
                "version": "v2",
                # 센서 단위 임계다. 실제로 val 사건에서 튜닝해 나온 값이므로
                # threshold_basis 는 val_events@fpr_0.05 가 정확한 표기다.
                # TEAM_AGREED 가 붙는 것은 지역 비율 임계이며 area_risk.basis 가 싣는다 (O-14).
                "threshold": THRESHOLD,
                "threshold_basis": "val_events@fpr_0.05",
                "threshold_version": f"sensor-{THRESHOLD}+area-{area_risk.AREA_THRESHOLD}",
            },
            "data_quality": {
                "sensors_active": len(sensors),
                "observed_rate": round(float(snap["sample_count"].ge(10).mean()), 3),
                "rain_available": bool(pd.notna(first["rain_local_mean_mm"])),
            },
        }

        path = OUT / f"risk_{name}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        n_alarm = sum(1 for s in sensors if s["horizons"]["30"]["high_level_p"] >= THRESHOLD)
        n_rise = sum(1 for s in sensors if s["predicted_transition"] == "RISE")
        n_fall = sum(1 for s in sensors if s["predicted_transition"] == "FALL")
        index.append({
            "scenario": name, "asof": ts, "센서": len(sensors),
            "현재고수위": int(snap["now_high"].sum()), "경보": n_alarm,
            "RISE": n_rise, "FALL": n_fall,
            "10분강우mm": round(float(first["rain_local_mean_mm"] or 0), 2),
            "60분강우mm": round(float(first["rain_past_60m_mm"] or 0), 1),
            # 경보 열은 전체 센서 기준이고, 아래 둘은 경로 범위(강남역 1km) 기준이다.
            # 분모가 다르므로 나란히 놓고 비교하지 않는다.
            "지역위험": area["risk_probability"],
            "지역등급": area["ai_risk_level"],
        })
        print(f"  -> {path.name}")

    summary = pd.DataFrame(index)
    summary.to_csv(OUT / "_index.csv", index=False, encoding="utf-8-sig")
    print("\n=== 데모 시나리오 요약 ===")
    print(summary.to_string(index=False))
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
