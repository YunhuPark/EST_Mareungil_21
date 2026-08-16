"""마른길 모델링 파이프라인 공통 설정.

여기 있는 값은 전부 데이터 계약이다. 바꾸면 데이터셋을 다시 만들어야 한다.
"""

from __future__ import annotations

from pathlib import Path

#: 저장소 루트. **절대경로를 박지 않는다** — 이 파일은
#: `<루트>/scripts/mareungil/config.py` 이므로 두 단계 위가 루트다.
#: 예전에는 `Path(r"C:\2026_Mareungil")` 이었고, 그 기계 밖에서는 아무도
#: 파이프라인을 돌릴 수 없었다(다른 팀원·macOS·CI 전부).
#: 아래 파생 경로는 문자열 그대로 유지되므로 데이터 계약은 바뀌지 않는다.
ROOT = Path(__file__).resolve().parents[2]

RAW_RAINFALL_DIR = ROOT / "data_unified" / "raw" / "seoul" / "rainfall" / "2022" / "monthly"
RAW_SEWER_DIR = ROOT / "data_unified" / "raw" / "seoul" / "sewer_level" / "2022" / "monthly"
SENSOR_META = ROOT / "data_unified" / "metadata" / "sewer_sensors" / "sensor_metadata_2022_address.csv"

OUT_DIR = ROOT / "data_unified" / "processed" / "v2"
EVENT_WINDOWS_CSV = OUT_DIR / "event_windows.csv"
SEWER_10MIN_PARQUET = OUT_DIR / "sewer_10min_event_windows.parquet"
RAIN_10MIN_PARQUET = OUT_DIR / "rain_10min_event_windows.parquet"
DATASET_PARQUET = OUT_DIR / "modeling_dataset_sensor_10min.parquet"

RAW_ENCODING = "cp949"

# 대상 구. 하수 원본의 `구분코드`, 강우 원본의 `구청 코드`가 서로 다른 체계라 따로 둔다.
SEWER_DISTRICT_CODES = ("22", "23")  # 22=서초, 23=강남
DISTRICT_NAME_BY_SEWER_CODE = {"22": "서초", "23": "강남"}

# 강남·서초 강우량계. 코드는 서울시 `강우량계 코드`.
RAIN_GAUGES = {
    101: "강남",
    102: "강남",
    103: "강남",
    2401: "서초",
    2402: "서초",
}

# --- 시간 격자 규칙 -------------------------------------------------------
#
# 서울시 강우 `자료수집 시각`은 :09 :19 :29 :39 :49 :59 에 기록된다.
# HH:09 행은 [HH:00, HH:10) 구간의 10분 누적강우로 해석한다.
# 하수 수위는 1분 간격이므로 같은 규칙으로 floor 하면 두 자료가 같은 격자에 놓인다.
#
#     floor("10min"):  00:09 -> 00:00,  00:59 -> 00:50
#
# 이 해석이 바뀌면 강우와 수위가 최대 10분 어긋난다.
BIN = "10min"
STEPS_PER_HOUR = 6

# --- 사건 정의 ------------------------------------------------------------
# 대상 5개 강우계의 10분 강우 최대값을 지역 강우강도로 본다.
EVENT_MIN_TOTAL_MM = 30.0  # 사건 누적강우 하한(5개 강우계 중 최대 관측소 기준)
EVENT_DRY_GAP_HOURS = 6  # 무강우가 이만큼 이어지면 별개 사건으로 끊는다
EVENT_LEAD_HOURS = 12  # 선행강우·초기수위 확보용 사건 앞 여유
EVENT_TAIL_HOURS = 24  # 수위 회복 관찰용 사건 뒤 여유

# 대조 무강우일: 당일·전일·전전일 모두 무강우인 날 중에서 고른다.
# 조건을 만족하는 날이 160일 넘게 나오므로 월별 상한을 둬서 고르게 뽑는다.
DRY_LOOKBACK_DAYS = 2
DRY_DAYS_PER_MONTH = 2

# --- 예측 설계 ------------------------------------------------------------
HORIZONS_MIN = (10, 30, 60)
PRIMARY_HORIZON_MIN = 30

# 고수위 임계는 학습 사건에서만 계산한다(누출 방지). 아래는 후보 분위수.
HIGH_LEVEL_QUANTILES = (0.95, 0.99)

# 임계 주변 지터를 전이로 세지 않기 위한 여유(히스테리시스 폭).
# 측정 분해능이 0.01인데 학습 상승전이의 26%가 임계를 0.01만 넘는다.
# 이 값 안쪽의 넘나듦은 AMBIGUOUS 로 빼고 대표지표에서 제외한다.
HIGH_LEVEL_MARGIN = 0.05

# 모델 비교는 이 오경보 예산 안에서의 상승전이 재현율로 한다.
# 예산을 고정하지 않으면 임계값만 낮춰 재현율을 얼마든지 올릴 수 있다.
FPR_BUDGET = 0.05

# 동적범위가 사실상 없는 센서는 모델링에서 제외한다.
MIN_SENSOR_LEVEL_RANGE = 0.10  # 학습기간 max - min
MIN_SENSOR_DISTINCT_VALUES = 10

# 누적강우 피처를 만들 되돌아보기 구간(분).
RAIN_LOOKBACK_MIN = (10, 30, 60, 120, 360)
# 수위 변화 피처를 만들 되돌아보기 구간(분).
LEVEL_LOOKBACK_MIN = (10, 30, 60)

# --- 사건 단위 분할 -------------------------------------------------------
#
# 행 단위 무작위 분할은 금지한다. 사건 통째로 갈라야 인접 10분 행이 학습과
# 평가에 동시에 들어가지 않는다.
#
# 테스트에 8/8 극한호우를 두는 것은 의도적이다. 학습에서 본 적 없는 규모의
# 사건에 모델이 어떻게 반응하는지가 이 프로젝트의 핵심 질문이다.
# 이 분할을 바꾸면 보고한 성능은 전부 무효다.
TEST_EVENTS = ("E13_0808", "E14_0810", "D0818")
VAL_EVENTS = ("E17_0904", "E11_0731", "D0902", "D0728")
# 나머지 사건은 전부 학습.
