# 계약 픽스처

계약(모듈 간 주고받는 JSON)의 **값이 채워진 실제 예시 파일**이다.
스키마 문서만 있으면 다섯 명이 각자 다르게 해석하지만, 값이 박힌 파일이 있으면
해석의 여지가 없다. API 가 이 파일을 그대로 응답하므로 엔진 없이도 UI 를 끝까지 만들 수 있다.

전체 검증:

```powershell
.\make.ps1 contracts
```

## 이름 공간 — `RF-*` 와 `DS-*` 를 섞지 않는다

두 종류가 있고 **서로 다른 것**이다. `RF-S2` 와 `DS-S2` 는 같은 시나리오가 아니다.

| 구분 | ID | 위치 | 계약 | 값의 출처 |
|---|---|---|---|---|
| 모델 위험 스냅샷 | `RF-S1`~`RF-S4`, `RF-E1` | `risk_*.json` (이 폴더 바로 아래) | `RiskAssessment` | **실제 모델 출력** |
| 통합 데모 | `DS-S1`~`DS-S6` | `demo/` | `AssessResponse` | risk 블록은 실제 모델 출력, decision·route 는 **STUB** |
| 공식정보 | — | `official/` | `OfficialInfo` | **미채움 (DRAFT)** |
| 거부 예제 | — | `invalid/` | 각 파일이 선언 | 통과하면 검증 실패 |

파일명은 호환을 위해 `risk_S1_calm.json` 그대로 두고, 문서·테스트에서만 `RF-` 접두사를 붙인다.

## `RF-*` — 모델 위험 스냅샷

| 파일 | 시점 | 상황 |
|---|---|---|
| `risk_S1_calm.json` | 2022-08-08 11:00 | 평상 — 무강우, 고수위 0개, 경보 0개 |
| `risk_S2_rising.json` | 2022-08-08 12:10 | **강우 상승 — 고수위 0개인데 경보 13개** |
| `risk_S3_peak.json` | 2022-08-08 21:40 | 사건 정점 — 고수위 29개, 경보 30개 |
| `risk_S4_recovery.json` | 2022-08-09 09:00 | 회복 — 고수위 14개로 감소 |
| `risk_E1_no_data.json` | — | 예외. 손으로 작성한 유일한 파일 |

`_index.csv` 에 네 시점의 요약 수치가 있다.

### `RF-S2` 가 데모의 핵심이다

12:10 시점에 **물이 높은 센서는 하나도 없다.** 그런데 모델은 13개 센서에 경보를 켠다.
30분 뒤 12:40에 **13개 중 12개가 실제로 고수위가 됐다.**

"지금 물이 높으면 나중에도 높다"고만 답하는 기준선은 12:10에 경보를 하나도 못 켠다.
모델이 만든 가치가 이 한 장면에 전부 들어 있다. 발표 동선은 **S1 → S2 → S3** 이 가장 강하다.

> 이 12/13 은 **데모 스냅샷의 사실**이며 전체 모델 성능이 아니다.
> 성능은 재현율 0.648 / 오경보 0.029 / 사전감지 85.3% 로 말한다.

### 값은 지어내지 않았다

`_` 로 시작하는 필드를 뺀 나머지는 전부 실제 모델 출력이며
`scripts/build_demo_fixtures.py` 로 재생성된다. 이 사건(2022-08-08)은 **학습에서 완전히
제외된 test 사건**이므로, 모델이 한 번도 본 적 없는 규모의 호우에 내놓은 값이다.

## `DS-*` — 통합 데모 (`demo/`)

UI 가 실제로 받는 `AssessResponse` 다.

```powershell
.\make.ps1 fixtures     # scripts/build_demo_assess_fixtures.py
```

| ID | 조건 | 기대 | 상태 |
|---|---|---|---|
| `DS-S1` | 평온, 데이터 정상 | `MOVE` + `USER_DESTINATION` | **있음** |
| `DS-S2` | 강우·위험 상승 | `WAIT` | 미작성 |
| `DS-S3` | 공식 대피 지시 또는 AI `HIGH`+실외 | `EVACUATE` + `SAFE_POINT` | 미작성 |
| `DS-S4` | `trapped=true` | `EMERGENCY` | 미작성 |
| `DS-S5` | `MOVE` + 후보 전부 제외 | `NO_SAFE_ROUTE` → 최종 `WAIT` | 미작성 |
| `DS-S6` | `MOVE` + 목적지가 통제 구간 | `DESTINATION_BLOCKED` | 미작성 |

미작성분은 T+6:00~8:00 구간 작업이다. 생성기의 `BUILDERS` 에 함수를 추가한다.

### `DS-S1` 에서 진짜와 STUB 의 경계

| 블록 | 출처 |
|---|---|
| `risk` | **실제 모델 출력** (`RF-S1` 을 그대로 실었다) |
| `decision` | **STUB** — 판단 엔진 미구현. 손으로 적은 값 |
| `route` | **STUB** — 경로 엔진 미구현. 후보를 비교하지 않았다 |

각 블록의 `_stub` 필드와 응답의 `source_kind: "FIXTURE"` 가 이 사실을 표시한다.
**mock 을 실제 모델 결과처럼 말하지 않는다.**

## `official/` — 공식정보

**값이 비어 있고, 그건 의도한 것이다.** 원출처를 확인하기 전에 경보 시각을 지어내지 않는다.
`verification: "DRAFT_UNVERIFIED"` 인 동안 이 내용을 "공식 확인된 사실"로 말하지 않는다.
자세한 것은 [official/README.md](./official/README.md).

## `invalid/` — 반드시 거부되어야 하는 조합

계약이 무엇을 막는지는 통과 예제가 아니라 **거부 예제**가 증명한다.
이 파일들이 **통과하면 검증이 실패한다.**

| 파일 | 규칙 |
|---|---|
| `move_with_no_safe_point.json` | RT-13 — 안전거점 탐색은 `EVACUATE` 에만 있다 |
| `evacuate_with_destination_blocked.json` | RT-13 — 안전거점은 안전 조건을 통과한 후보만 고른다 |
| `no_safe_route_without_attempt.json` | RT-09b — 탐색하지 않고 "경로가 없다"고 단정할 수 없다 |
| `destination_null.json` | F-19 / R13 — 목적지는 필수 |
| `ambiguous_risk_level.json` | AI-10 — 이름만 `risk_level` 인 필드 금지 |
| `profile_wheelchair.json` | X1 / C-14 — MVP 제외 프로필 |

각 파일의 `_expect_invalid` 가 대상 스키마와 사유를 선언한다.

## 계약 회의에서 아직 정하지 못한 것

- **`drivers[].contribution` 이 전부 null.** SHAP 미설치라 기여도를 지어내지 않았다. 피처 값만 실려 있다.
- **`area_risk` 집계 규칙(TH-04).** "상위 25% 평균"은 검증된 적 없는 임시 규칙이다
  ([DECISIONS.md](../../docs/DECISIONS.md) O-01).
- **`threshold_basis`.** 현재 `val_events@fpr_0.05`(모델 평가 근거)이며 목표는 `TEAM_AGREED` 다 (O-14).

## 픽스처를 볼 때 주의

- `location.lat/lon` 이 **공식 좌표가 아니다.** `quality` 를 반드시 함께 본다.
  `LANDMARK_MATCH_MANUAL_REVIEW` · `ROAD_NAME_ONLY_APPROX` 는 도로 차단에 쓰면 안 되고 시각화까지만.
- `predicted_level_unit` 이 `UNCONFIRMED` 다. **화면에 m·cm 를 붙이지 않는다.**
- 센서 수가 픽스처마다 다르다(31~32개). 레지스트리는 35개지만 응답은 해당 재생 시점에
  데이터·품질 조건을 통과한 센서만 담는다. 억지로 35개를 채우지 않는다.
