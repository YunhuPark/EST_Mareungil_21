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
| ②→③ 판단 산출 | `DS-S1` | `decision/` | `ActionDecision` | **STUB** — 판단 엔진 미구현 |
| 공식정보 | — | `official/` | `OfficialInfo` | **미채움 (DRAFT)** |
| 거부 예제 | — | `invalid/` | 각 파일이 선언 | 통과하면 검증 실패 |

파일명은 호환을 위해 `risk_S1_calm.json` 그대로 두고, 문서·테스트에서만 `RF-` 접두사를 붙인다.

## `RF-*` — 모델 위험 스냅샷

| 파일 | 시점 | 상황 | 지역 위험 |
|---|---|---|---|
| `risk_S1_calm.json` | 2022-08-08 11:00 | 평상 — 무강우, 고수위 0개, 경보 0개 | 0.0 `LOW` |
| `risk_S2_rising.json` | 2022-08-08 12:10 | **강우 상승 — 고수위 0개인데 경보 13개** | 0.4 `LOW` |
| `risk_S3_peak.json` | 2022-08-08 21:40 | 사건 정점 — 고수위 29개, 경보 30개 | 1.0 `HIGH` |
| `risk_S4_recovery.json` | 2022-08-09 09:00 | 회복 — 고수위 14개로 감소 | 0.6 `HIGH` |
| `risk_E1_no_data.json` | — | 예외. 손으로 작성한 유일한 파일 | `null` |

`경보` 열은 **전체 센서** 기준이고 `지역 위험` 은 **경로 범위 1km 안 5개** 기준이라
분모가 다르다. 나란히 놓고 빼거나 비교하지 않는다.

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
| `DS-S7` | `EVACUATE` + 1순위 시설 만석 | 2순위로 전환, `EVACUATE` 유지 | **있음** (M-32) |
| `DS-S8` | `EVACUATE` + 후보 0개 | `NO_SAFE_POINT`, `EVACUATE` 유지 + 119 강조 | **있음** (M-32) |

미작성분은 T+6:00~8:00 구간 작업이다. 생성기의 `BUILDERS` 에 함수를 추가한다.

### `DS-S7`·`DS-S8` — 시설 상태는 전부 합성값이다

M-32 가 "1순위 만석 → 2순위 전환 → 후보 0개 → `NO_SAFE_POINT`" 흐름을 고정 픽스처로
시연하기로 정해서 만들었다. **저장소에 수해대피소 원자료가 없으므로 시설 id·이름·좌표와
운영 상태는 전부 지어낸 값**이며, 라벨에 "합성 대피시설 … 실제 시설 아님"으로 적었다(M-24).
`risk` 블록만 `RF-S3`(실제 모델 출력)이다.

두 파일은 **같은 재생 시각(21:40)의 두 갈래**다. 시간이 흐르며 시설이 닫히는 시계열
데이터가 없으므로 순서가 아니라 상태 차이로 보여준다. 발표에서 "시간이 지나 닫혔다"고
말하지 않는다.

두 파일이 함께 증명하는 것은 **행동이 바뀌지 않는다**는 것이다(M-15). 갈 곳이 하나도
없어도 `action` 은 `EVACUATE` 이고, `EMERGENCY` 로도 `WAIT` 으로도 가지 않는다.

### `DS-S1` 에서 진짜와 STUB 의 경계

| 블록 | 출처 |
|---|---|
| `risk` | **실제 모델 출력** (`RF-S1` 을 그대로 실었다) |
| `decision` | **STUB** — 판단 엔진 미구현. 손으로 적은 값 |
| `route` | **STUB** — 경로 엔진 미구현. 후보를 비교하지 않았다 |

각 블록의 `_stub` 필드와 응답의 `source_kind: "FIXTURE"` 가 이 사실을 표시한다.
**mock 을 실제 모델 결과처럼 말하지 않는다.**

## `decision/` — ②판단 → ③경로

`ActionDecision` 계약의 예시다. **`demo/` 의 `decision` 블록과 필드가 다르다** — 헷갈리기 쉬우니
아래를 먼저 본다.

| 필드 | `decision/` (ActionDecision) | `demo/` 의 `.decision` |
|---|---|---|
| `asof`·`stage` | 있음 (required) | **없음** — `clock.event_time` 이 대신한다 |
| `official`·`route_prefs` | 있음 — ③이 소비하는 입력 | **없음** — `official` 은 응답 최상위에 따로 있다 |
| `primary_action`·`route_postprocess_applied` | **없음** | 있음 — 경로 후처리 **이후**에 생기는 값이다 |

### 이 폴더가 왜 생겼나

G0 전까지 `action_decision.schema.json` 을 검증하는 픽스처가 **하나도 없었다.** 4대 계약 중
하나가 아무도 안 보는 죽은 스키마였고, 그 결과 `official` 블록이 `official_0808.json` 을
**받지 못하는 상태**를 아무도 눈치채지 못했다 (`blocks_destination_ids` 가 거부됐다).

`tests/test_contracts.py` 의 `test_모든_계약이_적어도_하나의_픽스처로_검증된다` 가 재발을 막는다.
**새 계약을 만들면 픽스처도 같이 만든다.**

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
| `severe_without_direct_signal.json` | C-23 — AI 예측만으로 `SEVERE` 에 올라갈 수 없다 |
| `evacuate_route_failure_escalated.json` | M-15 / C-31 — 경로 실패를 `EMERGENCY` 로 승격 금지 |
| `move_destination_blocked_switched_to_wait.json` | M-16 — 목적지 차단과 안전경로 없음은 다른 상태다 |
| `expired_without_stale.json` | M-08 — 신선도 10분·30분은 포함 관계다 |

각 파일의 `_expect_invalid` 가 대상 스키마와 사유를 선언한다.

## 지역 위험은 어떻게 계산되나

`area_risk` 집계 규칙(TH-04)과 `threshold_basis` 는 **G0 에서 확정됐다** (C-17 · C-19).
집계는 `scripts/mareungil/area_risk.py` 한 곳에만 있고 `tests/test_area_risk.py` 가
픽스처와 규칙이 어긋나지 않는지 계속 확인한다.

- 지역 위험 = **경로 범위(강남역 1km) 안 센서 중 `t+30 확률 ≥ 0.33` 인 비율**
- 그 비율이 **`0.5` 이상이면 `ai_risk_level = HIGH`**
- 임계값만 바꿔 다시 계산하려면 `python scripts/refresh_area_risk.py --write`
  (모델을 재학습하지 않는다 — 센서 확률은 그대로 두고 집계만 다시 만든다)

> **분모가 5다.** 재생 시점에 범위 안에 존재하는 센서가 5개뿐이라 지역 위험은
> 0 / 0.2 / 0.4 / 0.6 / 0.8 / 1.0 의 6단계로만 움직인다. 지역 임계 0.5 는 실질적으로
> "5개 중 3개 이상"이며 **검증값이 아니라 팀 합의값**이다 (DECISIONS 3.0.2).

## 계약 회의에서 아직 정하지 못한 것

- **`drivers[].contribution` 이 전부 null.** SHAP 미설치라 기여도를 지어내지 않았다. 피처 값만 실려 있다.
- **공식정보 값**(O-11)과 **데모 시각**(O-12). `official/` 참조.

## 픽스처를 볼 때 주의

- `location.lat/lon` 이 **공식 좌표가 아니다.** `quality` 를 반드시 함께 본다.
  `LANDMARK_MATCH_MANUAL_REVIEW` · `ROAD_NAME_ONLY_APPROX` 는 도로 차단에 쓰면 안 되고 시각화까지만.
- `predicted_level_unit` 이 `UNCONFIRMED` 다. **화면에 m·cm 를 붙이지 않는다.**
- 센서 수가 픽스처마다 다르다(31~32개). 레지스트리는 35개지만 응답은 해당 재생 시점에
  데이터·품질 조건을 통과한 센서만 담는다. 억지로 35개를 채우지 않는다.
