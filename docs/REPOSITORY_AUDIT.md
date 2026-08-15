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
| 테스트 | `tests/` 5개 파일 · 75건 (**G0 이후 78건**) |
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

> **갱신 2026-08-15 G0.** 이 표는 부트스트랩 직후 상태였다. G0 에서 바뀐 부분을
> 아래에 반영했고, G0 에서 새로 발견한 것은 7절 뒤의 **8절**에 적었다.

| 구성 | 상태 | 비고 |
|---|---|---|
| 4대 계약 스키마 | **구현됨** | 검증 통과. 잘못된 조합 6종 거부 확인. **G0 에서 4대 계약이 전부 픽스처로 검증되도록 고쳤다**(C-12) |
| 계약 검증 명령 | **구현됨** | `.\make.ps1 contracts` — 픽스처 14건 |
| `ActionDecision` 픽스처 | **있음 (G0 신설)** | `contracts/fixtures/decision/DS-S1.action_decision.json`. decision 블록은 **STUB** |
| 경로 후처리 (확정 1건) | **구현됨** | `MOVE + NO_SAFE_ROUTE → WAIT` |
| enum 3중 동기화 검사 | **구현됨** | `tests/test_enum_sync.py` |
| 금칙어 검사 | **구현됨** | `tests/test_forbidden_wording.py` |
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
| **프로필 P1/P2 적용** | **없음** | 값이 OPEN |
| **분 단위 급등 감시** | **범위 밖** | G2 이후 별도 브랜치 |

## 7. 남은 위험

| 위험 | 영향 | 대응 |
|---|---|---|
| `official_0808.json` 이 비어 있다 | `DS-S3`·`DS-S6` 를 만들 수 없고 데모 시각이 안 정해진다 | **G0 최우선.** 못 채우면 공식정보 없는 서사로 전환 |
| TH-04 가 OPEN 인데 행동 규칙 6~8이 여기 의존한다 | 지역 위험 등급의 근거가 약하다 | 판단 엔진은 `ai_risk_level` 을 그대로 받아 쓴다. 임계를 다시 적용하지 않는다 |
| ~~경로 범위 안의 센서 수를 모른다~~ | — | **G0 에서 닫았다** — 1km 안 6개. 단 RF 픽스처에는 5개뿐이고 `23-0016` 의 누락 사유가 미확인이다 (DECISIONS 3.0.1) |
| 범위 안 센서가 6개뿐이라 지역 집계가 거칠다 | 어떤 비율 규칙을 쓰든 값이 6~7단계로만 움직인다 | 한계를 인정하고 발표에서 말한다. 범위를 넓히면 목적지 지정 지점(RT-15)과 어긋난다 |
| `services/route` 구현 보고와 체크아웃 불일치 | 있다고 믿고 기다리면 시간을 잃는다 | **없는 것으로 간주하고 계획했다.** 실제 코드가 나타나면 그때 통합 |
| 지정 지점 좌표가 미검증이다 | 지도 위치가 틀릴 수 있다 | 차단 근거로 쓰지 않는다(RT-05). 시각화까지만 |

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
