# 저장소 감사

> 감사일: 2026-08-15 · 대상: 부트스트랩 직전 체크아웃 (`e3f7f8c`)
>
> **문서에 적혀 있다는 이유로 구현 완료로 적지 않았다.** 아래는 전부 실제 파일을 열어 확인한 것이다.

## 1. 감사 시점의 상태

| 항목 | 확인 결과 |
|---|---|
| 커밋 | 2개 (`0ad0765` 데이터셋·평가·모델 파이프라인, `e3f7f8c` 데모 계약 샘플) |
| 추적 파일 | 55개 · 합계 8.4MB |
| 작업 트리 | 15.4GB (원본 데이터·중복 사본 포함) |
| Python | 3.13.9 (Anaconda), `jsonschema` 4.25.0 설치됨 |
| Node / npm | v24.14.1 / 11.11.0 |
| 패키지 설정 | `package.json` · `pyproject.toml` · `requirements*.txt` · `tsconfig.json` **전부 없음** |

## 2. 기존 구현 — 실제로 있던 것

| 구성 | 상태 | 위치 |
|---|---|---|
| 데이터 파이프라인 | **구현됨** | `scripts/mareungil/` (config·rainfall·sewer·features·evaluate·policy) |
| 모델 학습·평가 | **구현됨** | `scripts/run_baselines.py`, `run_models.py`, `run_alarm_policy.py`, `run_severity_threshold.py` |
| 모델링 데이터셋 | **있음** | `data_unified/processed/v2/*.parquet` (356,246행 × 61열) |
| RF 위험 픽스처 | **있음 · 실제 모델 출력** | `contracts/fixtures/risk_S1~S4`, `risk_E1_no_data` |
| `RiskAssessment` 스키마 | **있음** (단, 미추적이었음) | `contracts/schema/risk_assessment.schema.json` |
| `ActionDecision` 스키마 | **있음 · rev.5 반영 완료** (미추적이었음) | `contracts/schema/action_decision.schema.json` |
| 설계 문서 4종 + 다이어그램 22장 | **있음** (전부 미추적이었음) | `docs/` |

> **중요:** `contracts/schema/` 와 `docs/` 전체가 **Git 에 추적되지 않고 있었다.**
> 다섯 명이 clone 하면 설계 문서도 계약 스키마도 받지 못하는 상태였다.

## 3. 문서와 체크아웃의 차이 — 감사 시점

| 구성 | 문서상 | 감사 시점 실제 |
|---|---|---|
| `services/decision/` | 구현 담당 배정 | **디렉터리 없음** |
| `services/route/` | rev.5 에서 "사전 구현·테스트 통과" 보고 | **디렉터리 없음.** 보고와 체크아웃이 불일치 |
| `api/` | 통합 API | **없음** |
| `web/` | Vite + React + Leaflet | **없음** |
| `tests/` | 계약·정책 테스트 | **없음** |
| `SafeRoute` 스키마 | G0 필수 산출물 | **없음** |
| `AssessResponse` 스키마 | G0 필수 산출물 | **없음** |
| `official_0808.json` | G0 필수 산출물 | **없음** |
| 목적지 지정 지점 목록 | G0 정의 · T+12h 마감 | **없음** |
| 계약 검증 명령 | 필요 | **없음** |

### 스키마와 문서의 불일치 (감사 시점)

| 계약 | 문서 요구 | 실제 스키마 |
|---|---|---|
| `RiskAssessment` | `risk_probability`, `ai_risk_level`, `threshold_version` (AI-09/AI-10) | `area_risk.score` 만 있고 세 필드 전부 없음 |
| `RiskAssessment` | `threshold_basis = TEAM_AGREED` | 픽스처가 `val_events@fpr_0.05` (모델 평가 근거) |
| `ActionDecision` | rev.5 반영 | **일치함.** `service_risk_level`·`hazard_signs`·`destination` 이 이미 반영돼 있었다 |

## 4. 위생 상태 — 비밀정보와 대용량

| 확인 | 감사 시점 | 조치 |
|---|---|---|
| `secrets/seoul_openapi_key.txt` | `.gitignore` 로 제외됨 ✔ | 유지 |
| `data_unified.zip` (707MB) | 제외됨 ✔ | 유지 |
| `data_unified/raw/` (7.3GB) | 제외됨 ✔ | 유지 |
| `datasets/` (7.6GB) | 제외됨 ✔ | **삭제** — `data_unified/raw/` 와 바이트 단위 동일(MD5 확인) |
| `PoC1/02_모델링통합데이터.csv` (79MB) | **제외되지 않고 있었다** ⚠ | **삭제** — GitHub 권장 한도 50MB 초과. 어떤 스크립트도 참조하지 않음 |
| `data/` 침수흔적도 (52.8MB) | 제외됨 ✔ | 유지 (설계서 8.5.2 의 지도 레이어 원본) |
| Node·Python 빌드 산출물 | `.gitignore` 항목 없음 ⚠ | 항목 추가 |
| `.env` | `.env` 만 있고 `.env.*` 없음 ⚠ | 항목 추가 |

## 5. 이번 작업이 정리한 것

### 삭제 (7.7GB 회수)

| 대상 | 크기 | 왜 지웠나 |
|---|---|---|
| `datasets/` | 7,600MB | `data_unified/raw/` 와 바이트 동일한 중복 사본. 파이프라인은 `data_unified/raw/` 만 읽는다 (`config.py` 12~13행) |
| `PoC1/` | 82.5MB | 어떤 스크립트도 참조하지 않는 실험 산출물. 사용자 확인 후 삭제 |
| `.tmp-claude-artifact/` | 17.6MB | 도구가 남긴 Chromium 프로필 |
| `data_unified/processed/sewer_risk_modeling_2022/` | 8.2MB | `.gitignore` 가 "v2 로 대체된 구버전 산출물"로 명시한 산출물 |
| `scripts/**/__pycache__/` | 0.2MB | 재생성되는 바이트코드 |
| `reports/_기획서_extract.txt` | 5KB | 같은 폴더의 PDF 를 텍스트로 뽑아둔 중복본. **개인 전화번호가 들어 있어** 추적 대상에 두지 않는 편이 낫다 |

`data_unified.zip`(707MB)은 사용자 판단으로 **남겨두었다.**

### 추가

| 영역 | 파일 |
|---|---|
| 작업 규칙 | `CLAUDE.md`, `.editorconfig`, `.env.example`, `.gitignore`(보완) |
| 의존성 | `pyproject.toml`, `requirements-dev.txt`, `requirements-model.txt`, `web/package.json`, `web/package-lock.json` |
| 명령 | `make.ps1` (install·api·web·contracts·test·typecheck·build·check) |
| 계약 | `contracts/schema/safe_route.schema.json`, `assess_response.schema.json`, `official_info.schema.json` |
| 계약 | `contracts/schema/risk_assessment.schema.json` **최소 변경** — `risk_probability`·`ai_risk_level`·`threshold_version` 추가 |
| 검증 | `contracts/validate.py` |
| 픽스처 | `contracts/fixtures/demo/DS-S1`, `official/official_0808.json`(초안), `invalid/` 6종, `contracts/destinations.json`(초안) |
| 서비스 | `services/decision/`(enums·postprocess), `services/route/`(interface·fixture_provider) |
| API | `api/main.py`, `api/fixtures.py` |
| UI | `web/` 전체 (Vite + React + TS + Leaflet 모바일 단일 화면) |
| 테스트 | `tests/` 5개 파일 · 75건 (부트스트랩 시점. **현재는 8개 모듈 · 179건** — 6절 참조) |
| 문서 | `docs/` 5개 (RUNBOOK · DECISIONS · CHECKLIST · AUDIT · GITHUB_SETUP) |

### 기존 스키마를 교체하지 않고 최소 변경한 이유

`risk_assessment.schema.json` 에 `risk_probability`·`ai_risk_level`·`threshold_version` 을
**optional 로** 넣었다. `required` 로 올리면 기존 RF 픽스처 5개가 전부 깨지고,
다시 만들려면 `build_demo_fixtures.py` 로 모델을 재학습해야 한다.

대신 새 필드를 쓰는 쪽(`DS-*` 픽스처)에는 채워 넣었고, `required` 승격은
G0 에서 픽스처 생성기를 갱신할 때 하도록 [DECISIONS.md](./DECISIONS.md) O-14 에 남겼다.
`area_risk.score` 는 `DEPRECATED` 로 표시하고 호환을 위해 남겼다.

## 6. 지금 상태 — 구현됨 / STUB / 없음

**이 표가 이 문서의 핵심이다. 여기서 "구현됨"이 아닌 것을 완료로 말하지 않는다.**

> **갱신 2026-08-16 정합성 점검.** 이 표는 부트스트랩 직후 상태였다. G0 와
> 이후 정합성 점검에서 바뀐 부분을 반영했고, 새로 발견한 것은 7절 뒤의 **8절**에 적었다.
>
> **갱신 2026-08-16 최종 회의 반영.** 회의 확정사항(DECISIONS 2.3)을 계약·코드·화면에
> 반영하면서 다시 손봤다. 이 시점의 검증 규모는
> **스키마 5개 · 픽스처 20건 · Python 179건(8개 모듈) · 프론트 15건**이다.
>
> **갱신 2026-08-16 검사 보강.** 반영 결과를 감사하다 사각지대 둘을 찾아 메웠다.
> 둘 다 **일부러 깨뜨려 실패를 확인한 뒤** 되돌렸다 — 8절의 교훈을 이번에도 먼저 적용했다.
> 같은 감사에서 CLAUDE.md 를 현재 상태 기준으로 다시 썼고(10절 → 12절), 재번호로 깨진
> 상호참조 18곳을 옮겼다.
>
> **회의로 닫힌 것과 여전히 없는 것을 섞지 않는다.** 예를 들어 프로필 수치는
> 확정됐지만(M-37) 적용하는 코드는 없고, 시설 상태 전환은 픽스처로 시연될 뿐
> 선택 로직이 없다(M-32). 아래 표에서 그렇게 구분해 적었다.

| 구성 | 상태 | 비고 |
|---|---|---|
| 4대 계약 스키마 | **구현됨** | 검증 통과. 잘못된 조합 6종 거부 확인. **G0 에서 4대 계약이 전부 픽스처로 검증되도록 고쳤다**(C-12) |
| 계약 검증 명령 | **구현됨** | `.\make.ps1 contracts` — 픽스처 20건 (유효 10 + 거부 예제 10) |
| `ActionDecision` 픽스처 | **있음 (G0 신설)** | `contracts/fixtures/decision/DS-S1.action_decision.json`. decision 블록은 **STUB** |
| 경로 후처리 | **구현됨** | 행동을 바꾸는 규칙 1건(`MOVE + NO_SAFE_ROUTE → WAIT`) + **행동을 유지하고 사유만 붙이는 규칙 5건**(M-15·M-16). 계약도 유지에서 벗어나는 응답을 거부한다 |
| **공식정보 가시성 필터 (M-36)** | **구현됨** | `services/decision/official.py`. `available_time <= 재생시각` 인 항목만 남기고, 공개시각이 `null` 이면 쓰지 않는다. `tests/test_official_visibility.py` |
| **데이터 신선도 2단계 (M-08)** | **부분 구현** | 계약(`clock` 네 시각 + `stale`·`expired`)과 등급 쪽 제외(`service_risk.EXPIRED_SEC`)는 **구현됨**. **`MOVE → WAIT` 전환은 행동 판정 본체에 속하며 아직 없다** |
| **수동 재판단 (M-18)** | **구현됨** | `/api/scenarios` + `web/src/components/ReassessBar.tsx`. 재생 시각 전환만 하고 자동 감지는 없다 |
| **시설 상태 후보 전환 (M-32)** | **픽스처만** | `DS-S7`·`DS-S8` 로 흐름을 보여준다. **시설 값은 전부 합성이고 선택 로직은 없다** |
| **지역 집계 TH-04 (O-01)** | **구현됨** | `scripts/mareungil/area_risk.py` `compute()`. 범위 내 TH-03 초과 비율, 지역 임계 `0.5`. **임계는 `TEAM_AGREED`** |
| **등급 진동 억제 (O-08 → C-18)** | **구현됨** | 같은 파일 `step()`·`stabilize()`·`DwellState`. 진입 즉시 / 해제 3스텝. `tests/test_area_risk.py` 가 고정 |
| enum 3중 동기화 검사 | **구현됨** | `tests/test_enum_sync.py` 16건. 핵심 9축 3중 일치 + **필드 이름으로 묶은 스키마 사본 교차 검사** + **TS 라벨 표 커버리지**. 뒤의 둘은 검사 보강에서 추가했다 — 그 전에는 `closures.kind` 사본을 어긋나게 두거나 `VERIFICATION_LABEL` 에서 `DEMO_FIXTURE` 를 지워도 전부 통과했다 |
| 금칙어 검사 | **구현됨** | `tests/test_forbidden_wording.py` 35건. `web/src` **와 데모 픽스처의 렌더링 문자열**을 함께 본다 — 화면에 찍히는 문장의 상당수가 계약을 타고 오기 때문이다. 양쪽 위반 0건 |
| **공식정보 주입 (C-11 → C-21)** | **구현됨** | `official_0808.json` 을 두 소비자 블록에 **그대로** 주입 가능. 회귀 테스트가 파일을 손대지 않고 넣는다 |
| 통합 API | **구현됨 (픽스처 기반)** | 응답 전 계약 검증. `source_kind: FIXTURE` |
| 모바일 단일 화면 | **구현됨 (픽스처 기반)** | 지도 실패해도 5요소 유지 |
| `DS-S1` | **있음** | risk 블록은 **실제 모델 출력**(RF-S1), decision·route 는 **STUB** |
| **판단 엔진 (우선순위 1~10)** | **없음** | T+3:00~6:00 |
| **경로 엔진 (후보 30개 비교)** | **STUB** | 인터페이스만. T+6:00~8:00 |
| **`DS-S2` ~ `DS-S6`** | **없음** | T+6:00~8:00 |
| **공식정보 픽스처 값** | **없음** | 형식만. `verification: DRAFT_UNVERIFIED` |
| **지정 지점 목록 확정** | **초안** | 5개, 좌표 `APPROX_UNVERIFIED` |
| **데이터 품질 규칙 DQ-01~05** | **없음** | T+3:00~6:00 |
| **대피시설 안전거점 선택** | **없음** | T+6:00~8:00 |
| **프로필 P1/P2 적용** | **없음** | **값은 확정됐다**(M-37: 1.15 · 1.5 · 60분/30분). 적용할 경로 비교 엔진이 아직 STUB 이라 코드에 반영된 곳이 없다 |
| **분 단위 급등 감시** | **범위 밖** | G2 이후 별도 브랜치 |

## 7. 남은 위험

| 위험 | 영향 | 대응 |
|---|---|---|
| `official_0808.json` 이 비어 있다 | `DS-S3`·`DS-S6` 를 만들 수 없고 데모 시각이 안 정해진다 | **G0 최우선.** 못 채우면 공식정보 없는 서사로 전환 |
| ~~TH-04 가 OPEN 인데 행동 규칙 6~8이 여기 의존한다~~ | — | **G0 에서 닫았다**(O-01 → C-17). 다만 위험이 사라진 것은 아니다 — 아래 줄을 본다 |
| **지역 임계 `0.5` 가 검증값이 아니라 팀 합의값이다** | 행동 규칙 6~8 의 근거가 여전히 약하다. TH-03(0.33)의 val 검증은 **센서 단위**이고 지역으로 옮긴 근거는 없다 | 판단 엔진은 `ai_risk_level` 을 그대로 받아 쓰고 임계를 다시 적용하지 않는다. 발표에서 `TEAM_AGREED` 임을 그대로 말한다 |
| ~~경로 범위 안의 센서 수를 모른다~~ | — | **G0 에서 닫았다** — 1km 안 등록 6개, 재생 시점 실제 **5개**. `23-0016` 은 2022-06-05 에 데이터가 끊겨 사건 구간에 행이 없다 (DECISIONS 3.0.2) |
| 범위 안 센서가 5개뿐이라 지역 집계가 거칠다 | 어떤 비율 규칙을 쓰든 값이 6단계로만 움직인다 | 한계를 인정하고 발표에서 말한다. 범위를 넓히면 목적지 지정 지점(RT-15)과 어긋난다 |
| `modelable=True` 를 "이 데모에 쓸 수 있다"로 읽을 위험 | `23-0016` 처럼 사건 기간에 데이터가 없는 센서가 섞인다 | 스크리닝은 수위 변동폭만 본다. 사건 커버리지는 `includes_event_hour` 로 따로 확인한다 |
| `services/route` 구현 보고와 체크아웃 불일치 | 있다고 믿고 기다리면 시간을 잃는다 | **없는 것으로 간주하고 계획했다.** 실제 코드가 나타나면 그때 통합 |
| 지정 지점 좌표가 미검증이다 | 지도 위치가 틀릴 수 있다 | 차단 근거로 쓰지 않는다(RT-05). 시각화까지만 |
| **`services/route` 가 `services/decision/enums` 를 import 한다** | CLAUDE.md 4절(enum 정본은 `services/decision/enums.py`)과 10절(route → decision 금지)이 그대로는 동시에 성립하지 않는다 | **10절에 예외를 명시했다** — enum 모듈 하나만 허용하고 `postprocess`·`service_risk`·`official` 은 금지다. enum 을 중립 위치로 옮기면 예외가 사라지지만 계약 주변 변경이라 G3 이후로 미뤘다 |
| **회의 확정이 코드보다 앞서 있다** | 프로필 수치(M-37)와 시설 상태 전환(M-32)은 확정됐는데 적용할 엔진이 없다. 문서만 보면 동작하는 것처럼 읽힌다 | 위 6절 표에서 **확정 / 구현**을 나눠 적었다. 발표에서도 그렇게 말한다 |

## 8. G0 에서 새로 발견한 것

부트스트랩 감사 때는 보지 못했고 **G0 계약 대조 과정에서 드러난 것**들이다.
전부 "조용히 틀리는" 종류라 따로 적어 둔다. 상세는 [DECISIONS.md](./DECISIONS.md) 2.1 절.

| 발견 | 감사 시점 표기 | 실제 |
|---|---|---|
| `action_decision.schema.json` | "구현됨"으로 셌다 | **어떤 픽스처도 이 스키마로 검증되지 않았다.** 스키마 파일이 존재하는 것과 그것이 강제되는 것은 다르다 |
| `ActionDecision.official` | 언급 없음 | `official_0808.json` 을 **받지 못하는 상태**였다. `blocks_destination_ids`·`label`·`alerts[].source` 가 거부됐고 `confirmed_flooding` 은 없었다 |
| `data_quality` | 언급 없음 | 최상위와 `risk` 양쪽에 중복. 어느 쪽이 정본인지 계약에 없었다 |
| `.\make.ps1 check` | "구현됨 · 이것만 통과하면 된다" | **실패를 통과로 보고했다.** `Invoke-Step` 반환값에 출력이 섞여 배열이 됐고 PowerShell 에서 빈 배열이 아니면 참이다 |

### 감사 방법에 대한 교훈

3절에서 "문서상 vs 실제"를 대조했지만 **"파일이 있다" 와 "그 파일이 지켜지고 있다"** 를
구분하지 않았다. `action_decision.schema.json` 은 존재했고 내용도 옳았지만 아무도
검증하지 않았으므로 실질적으로는 없는 것과 같았다.

이후 감사에서는 각 계약에 대해 **"이것을 깨뜨리면 무엇이 빨개지는가"** 를 함께 적는다.
답이 없으면 그 계약은 `구현됨` 이 아니다.

## 9. 정합성 점검에서 새로 발견한 것 (2026-08-16)

`.\make.ps1 check` 가 **전부 통과하는 상태에서** 문서·코드·계약을 대조해 찾은 것들이다.
**테스트가 통과한다는 것과 테스트가 무언가를 지킨다는 것은 다르다** — 아래 셋 다 그 차이에서 나왔다.

| 발견 | 그때까지의 표기 | 실제 | 처리 |
|---|---|---|---|
| `AssessResponse.official` | 체크리스트에 `[x] C-11 완료` | **C-11 이 절반만 닫혀 있었다.** `official_info` 는 `asof` 를 required 로 두므로 규격에 맞는 문서는 **언제나** 그 필드를 갖는데, 두 소비자 블록 모두 `asof`·`verification`·`source_url`·`^_` 를 몰랐고 `AssessResponse` 는 `confirmed_flooding` 까지 없었다. **어떤 정상 픽스처도 주입할 수 없었다** | C-21 |
| 그 회귀 테스트 | "픽스처를 그대로 받는지 확인한다" | 손으로 만든 값에서 `asof`·`verification` 을 **빼고** 넣고 있었다. 생성기도 `official` 을 4개 키만 하드코딩해서 **실제 파일이 계약을 한 번도 통과해본 적이 없었다** | C-21 |
| `DS-S1.action_decision.json` | C-20 이 "`DS-S1` 의 이유를 맞췄다" | 폐기값 `0.1086`(상위 25% 평균)과 센서 임계 `0.33` 이 그대로 남아 있었다. **C-20 의 수정이 생성기를 통해 이뤄졌는데 이 파일만 생성기가 없다** | C-22 |
| `tests/test_enum_sync.py` | "enum 3중 동기화 검사 구현됨" | `UserContext` 축이 **아예 빠져 있었고**, `basis`(3곳)·`action`·`service_risk_level`(각 2곳) 사본을 **한 곳만 읽고 있었다.** 나머지 사본을 고쳐도 아무것도 빨개지지 않았다 | 교차검사 추가 |
| TH-04 상태 표기 | O-01 은 G0 에서 닫힘 | 설계서·런북·체크리스트·이 문서까지 **9군데가 아직 "미확정 / G2 확정 대상"** 이라고 적고 있었다. 발표 슬라이드 생성기는 **폐기된 "상위 25% 평균"을 그대로 출력**하고 있었다 | 문서 통일 |

### 이번에 추가한 검사 기준

8절의 교훈("이것을 깨뜨리면 무엇이 빨개지는가")을 이번에는 **먼저 확인했다.**
새로 만든 두 보장은 실제로 깨뜨려 보고 실패를 확인했다.

| 보장 | 깨뜨려 본 방법 | 결과 |
|---|---|---|
| 공식정보 주입 (C-21) | 스키마 수정을 되돌림 | `Additional properties are not allowed ('asof', 'verification')` 로 **2건 실패** |
| enum 사본 일치 | `safe_route` 의 `basis` 에 값 하나 추가 | 파일·경로·차이를 짚으며 **1건 실패** |

**여기서 얻은 세 번째 교훈:** 테스트가 입력을 **정제해서** 넣으면 그 테스트는
정제한 만큼을 증명하지 못한다. 픽스처를 검증하는 테스트는 픽스처를 **손대지 않고**
넣어야 한다. 한 필드라도 골라 담기 시작하면 그 순간 아무것도 증명하지 않는다.
