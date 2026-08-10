# 마른길 — 하수관로 고수위 위험 예측

강남·서초 하수관로 센서의 **10·30·60분 후 고수위 위험**을 예측한다.
주 예측시간은 30분. 2022년 서울시 공개데이터 기반.

## 먼저 읽을 것

| 문서 | 내용 |
|---|---|
| [reports/안윤지_위험예측_데이터조사.md](reports/안윤지_위험예측_데이터조사.md) | **메인 설계안.** 데이터 검증부터 모델 결과까지 전부 |
| [reports/안윤지_데이터_현황_및_자료요청_가이드.md](reports/안윤지_데이터_현황_및_자료요청_가이드.md) | 서울시 자료요청 문안과 절차 |
| [data_unified/processed/v2/README.md](data_unified/processed/v2/README.md) | 데이터셋 계약과 재현 방법 |

## 반드시 알고 시작할 것

**전체 정확도·F1로 성과를 판단하면 안 된다.**

아무것도 학습하지 않은 기준선("지금 물이 높으면 30분 뒤에도 높다")이 F1 **0.894** 를 낸다.
대부분의 행에서 수위가 거의 안 변하기 때문이다. 그런데 이 기준선은 **물이 차오르기
시작하는 순간을 단 한 건도 못 잡는다(0.000).**

그래서 대표지표는 **상승전이 재현율**이다.

| test (8/8 극한호우), t+30 | 차오르는 순간 잡은 비율 | 오경보율 | 미리 경고한 비율 | 전체 F1 |
|---|---:|---:|---:|---:|
| 로지스틱 | **0.731** | 0.051 | 87.7% | 0.829 |
| HistGB | 0.648 | 0.029 | 85.3% | 0.839 |
| 규칙 기준선 | 0.108 | 0.006 | 43.1% | 0.892 |
| 지속성 기준선 | 0.000 | 0.000 | 23.0% | 0.894 |

전체 F1만 보면 기준선이 더 높다. 상승전이로 보면 정반대다.
고수위 시작 374건 중 **328건(87.7%)을 미리 경고**한다 — 이것이 모델이 만든 가치다.

## 데이터는 이 저장소에 없다

원본 약 7.5GB 는 용량 때문에 제외했다. 공식 포털에서 각자 내려받는다.

- 서울시 강우량 [OA-1168](https://data.seoul.go.kr/dataList/OA-1168/F/1/datasetView.do)
- 서울시 하수관로 수위 [OA-2527](https://data.seoul.go.kr/dataList/OA-2527/S/1/datasetView.do?tab=A)
- 경로와 배치는 `data_unified/metadata/source_manifest.csv` 참고

**모델링용 데이터셋(`processed/v2/*.parquet`)은 포함돼 있으므로**, 원본 없이도
평가·모델 스크립트는 바로 돌릴 수 있다.

## 재현

```powershell
# 1) 데이터셋 (원본 7.28GB 필요. 이미 만들어진 parquet 이 있으면 건너뛴다)
python scripts\build_dataset.py events
python scripts\build_dataset.py sewer
python scripts\build_dataset.py rain
python scripts\build_dataset.py features

# 2) 기준선과 모델
python scripts\run_baselines.py 30
python scripts\run_models.py 30

# 3) 경보 정책
python scripts\run_alarm_policy.py 30
python scripts\run_severity_threshold.py 30
```

## 코드 구조

```text
scripts/
├─ mareungil/
│  ├─ config.py      데이터 계약·사건분할·예산. 바꾸면 전부 재실행해야 한다
│  ├─ rainfall.py    강우 로딩, 강우사건 정의
│  ├─ sewer.py       수위 추출, 완전격자 되채움
│  ├─ features.py    피처·타깃·고수위 임계
│  ├─ evaluate.py    국면 분해 평가 (상승전이 중심)
│  └─ policy.py      경보 임계정책, 경보해제
└─ run_*.py          실행 진입점
```

## 지금 못 하는 것

- **물리적 만관율** — 관 높이와 센서 영점이 없어 "몇 % 찼다"를 말할 수 없다.
  수위 단위(m/cm)도 미확인이라 출력에 `UNCONFIRMED` 로 표시한다.
- **정확한 도로 위치** — 센서 35개 중 공식 좌표는 0개. 주소 지오코딩 추정값이며
  정확 번지 수준은 10개뿐이다. `geocode_quality` 를 반드시 함께 보고 판단할 것.
- **경보 해제** — 켜는 건 되는데 끄는 게 아직 부정확하다(오해제율 0.117). 운영 투입 금지.
- **예보 활용** — 현재는 관측된 비만 쓴다. KMA 초단기예보는 미수집.

## 보안

`secrets/` 는 커밋하지 않는다. 서울시 OpenAPI 키는 로컬
`secrets/seoul_openapi_key.txt` 에서 읽으며 로그·산출물에 남기지 않는다.
