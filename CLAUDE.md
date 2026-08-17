# CLAUDE.md — 마른길 저장소 작업 규칙

이 파일은 사람과 Claude Code가 **같은 규칙으로** 이 저장소를 고치기 위한 기준이다.
코드를 고치기 전에 이 문서를 먼저 읽는다.

> 최종 갱신: 2026-08-17 · O-16(DQ-03 관측률 지표)과 C-32(안전거점 후보 집합 7곳)를
> 닫으면서 다시 썼다. 그 전날에는 최종 회의 확정사항(M-01~M-39)과 O-11(공식정보 실제 값)·
> O-12(데모 시각 21:40)·O-15(`DANGER` 추가 위험신호)를 반영했다.
> 검증 규모는 **계약 픽스처 23건 · Python 236건 · 프론트 25건**이다.

## 1. 프로젝트 한 문장

마른길은 2022년 8월 8일 강남 집중호우를 재생해, 사용자가 침수 상황에서
**지금 위험한가**와 **지금 무엇을 해야 하는가**를 한 화면에서 확인하는 모바일 웹 MVP다.

**교육·시연용이며 공식 재난안전 판단 도구가 아니다.** 이 고지는 화면에 항상 노출한다.

## 2. 문서 및 계약 우선순위

충돌하면 위에서부터 이긴다.

1. **현재 재현 가능한 데이터 산출물과 `contracts/schema/`의 실제 스키마**
2. [최종 회의 확정사항](docs/마른길_최종_회의_확정사항.md) · [확인완료 팀원 답변](docs/마른길_확인완료_팀원답변.md)
   — 팀 전원이 확정한 것이며 `docs/DECISIONS.md` 2.3에 `M-<안건번호>` ID로 정리돼 있다
3. [요구사항 정의서](docs/마른길_요구사항_정의서.md) · [MVP 설계서](docs/마른길_MVP_설계서.md)
4. [문서 정합성 평가서](docs/마른길_문서_정합성_평가.md)의 최종 결정
5. 그 밖의 과거 계획·발표·보고 자료

낮은 우선순위 자료를 폐기하라는 뜻이 아니라, **수치·enum·범위를 덮어쓰지 않는다**는 뜻이다.
실제로 회의(2위)가 정합성 평가서(4위)의 C-24·C-31을 대체했고, 그 두 행은 지우지 않고
"대체됨"으로 표시했다 — 그때 무엇을 근거로 그렇게 정했는지가 그 문서의 목적이기 때문이다.

## 3. 구현 완료와 목표 설계의 구분

> **문서에 적혀 있다는 이유만으로 구현 완료로 간주하지 않는다.**

- 문서는 대부분 **목표 설계**다. 현재 체크아웃에서 실제로 확인한 것만 "구현됨"이라고 쓴다.
- 코드·문서·응답에서 mock / stub / fixture는 **명시적으로 그렇게 표시**한다.
- mock 값을 실제 모델 결과나 완성된 기능처럼 표현하지 않는다.
- **"확정됐다"와 "구현됐다"도 다르다.** 프로필 수치 1.15·1.5는 확정됐지만 적용하는 코드가
  없고, 시설 상태 전환은 픽스처로 시연될 뿐 선택 로직이 없다. 그렇게 나눠 적는다.
- **"확정됐다"와 "검증됐다"도 다르다.** 지역 임계 0.5와 프로필 수치는 팀 합의값이며
  근거 데이터로 튜닝한 값이 아니다. 발표에서 그대로 말한다.
- **"구현됐다"와 "호출된다"도 다르다.** `classify()`·`apply()`·`visible_at()` 은 구현돼 있고
  테스트가 53건 붙어 있지만 **`api/main.py` 는 셋 중 아무것도 부르지 않는다.** 로직이 있는 것과
  런타임에 그 로직이 도는 것을 나눠 적는다.
- 현재 상태는 [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md) **6절과 10절**이 정본이다.
  **`docs/마른길_MVP_설계서.md` 8.5.4 와 `docs/HACKATHON_11H_RUNBOOK.md` 의 T+ 일정표는
  구현 상태·일정의 근거로 쓰지 않는다** — 부트스트랩 직전 상태에서 멈춰 있다.

## 4. 핵심 enum (단일 출처)

정본은 `contracts/schema/*.json`이고, 언어별 사본은 아래 두 파일뿐이다.

| 언어 | 파일 |
|---|---|
| Python | `services/decision/enums.py` |
| TypeScript | `web/src/contracts/enums.ts` |

세 곳이 어긋나면 `tests/test_enum_sync.py`가 실패한다. **새 enum 값을 이 세 곳 밖에서 만들지 않는다.**

| 축 | 필드 | 값 |
|---|---|---|
| 최종 서비스 위험 | `ActionDecision.service_risk_level` | `SAFE` `CAUTION` `DANGER` `SEVERE` |
| AI 예측 위험 | `RiskAssessment.area_risk.ai_risk_level` | `LOW` `HIGH` |
| 행동 | `action` | `MOVE` `WAIT` `EVACUATE` `EMERGENCY` `UNAVAILABLE` |
| 상황 | `user_state.context` | `INDOOR` `OUTDOOR` `UNDERGROUND` |
| 현장 위험 징후 | `user_state.hazard_signs[]` | `WATER_INFLOW` `SEWER_BACKFLOW` `STAIR_INFLOW` |
| 프로필 | `user_state.profiles[]` | `ELDERLY` `WITH_CHILD` |
| 경로 상태 | `SafeRoute.status` | `VERIFIED_ROUTE` `FALLBACK_CANDIDATE` `NOT_REQUIRED` `NO_SAFE_POINT` `NO_SAFE_ROUTE` `DESTINATION_BLOCKED` `DATA_UNAVAILABLE` |
| 경로 도달 대상 | `SafeRoute.route_target` | `USER_DESTINATION` `SAFE_POINT` |
| 근거 | `reasons[].basis` | `OFFICIAL_GUIDANCE` `AI_PREDICTION` `TEAM_RULE` |

### 위 표 밖의 계약 enum

Python이 소비하지 않아 `enums.py` 사본이 없는 값들이다. **사본이 없다고 검사도 없는 것은
아니다** — 같은 필드가 여러 스키마에 복사돼 있으면 `test_enum_sync.py`가 필드 이름으로 묶어
사본 일치를 강제하고, 화면 문구가 필요한 값은 라벨 표가 빠짐없이 덮는지 함께 본다.

| 필드 | 값 | 어디서 지키나 |
|---|---|---|
| `official.verification` | `VERIFIED_SOURCE` `DRAFT_UNVERIFIED` `DEMO_FIXTURE` | 스키마 3곳 사본 일치 + `VERIFICATION_LABEL` 커버리지 |
| `candidates[].excluded_by` | `OFFICIAL_CLOSURE` `CONFIRMED_FLOODING` `PROFILE_CONSTRAINT` `OUT_OF_SCOPE` `SHELTER_FULL` `SHELTER_CLOSED` `SHELTER_INACCESSIBLE` | `EXCLUDED_BY_LABEL` 커버리지 |
| `closures[].kind` · `closures[].mode` | `ROAD` `UNDERPASS` `RIVERSIDE` `SUBWAY` / `VEHICLE` `PEDESTRIAN` `BOTH` | 스키마 2곳 사본 일치 + `CLOSURE_KIND_LABEL`·`CLOSURE_MODE_LABEL` 커버리지 |
| `hazards[].kind` · `target.kind` · `source_kind` | — | 사본이 하나뿐. TypeScript union 타입이 컴파일러로 잡는다 |

**여기에 값을 더하면 라벨 표도 같이 채운다.** 채우지 않으면 화면에 enum 코드가 그대로 보인다.

### 계약에 두지 않는 것

- 이름이 **그냥 `risk_level`인 필드**. 두 위험 축은 항상 `ai_risk_level` / `service_risk_level`로 구분한다.
- `UNKNOWN`, `EMERGENCY_ASSIST`, `AVAILABLE`, `WITHHELD`
- `WHEELCHAIR`, `WITH_PET` (검증 데이터 부족으로 MVP 제외)
- `SafeRoute.status`의 `UNAVAILABLE` — 경로 단절은 `DATA_UNAVAILABLE`이다
- 시설 접근 불가도 `UNAVAILABLE`이 아니라 `SHELTER_INACCESSIBLE`이다 — 경로 데이터 단절과
  시설 접근 불가는 다른 사건이다

**"확인되지 않음"은 `null`로 표현한다.** 회의는 센서 없는 구간과 시설 상태를 UNKNOWN이라
불렀지만(M-05·M-24), 계약에는 `UNKNOWN` 값을 만들지 않고 `null`을 쓰며 화면 문구로만
"확인되지 않음"이라고 적는다. `ai_risk_level: null`이 이미 "판단할 근거가 없다"를 뜻하고,
그것을 `LOW`로 채우면 데이터가 끊긴 지역을 안전하다고 말하게 된다.

## 5. 사용자 화면 금지 표현

`tests/test_forbidden_wording.py`가 검사한다. **검사 대상이 두 곳이다.**

- `web/src/` 전체 (주석 포함)
- `contracts/fixtures/demo/`의 **렌더링되는 문자열** — `route.limit`·`notice.*`·
  `reasons[].text`·`target.reason`은 계약을 타고 화면에 그대로 찍힌다. `_`로 시작하는
  개발 주석 필드는 제외한다

| 금지 | 대신 쓸 표현 |
|---|---|
| 안전 경로, 최적 경로, 검증된 경로 | 공식 대피경로 기준 · 상대적으로 위험이 낮은 후보 |
| 검증 완료 | 검증하지 않았다는 사실을 그대로 표시 |
| 실시간 | 2022년 과거 기록 재생 |
| 자동 신고, 자동 위치 전송 | 전화 앱 연결과 위치 문구 복사 |
| 길안내, 내비게이션 | 목적지까지 · 추천 후보 경로 |
| 도로 침수 예측 | 하수관로 고수위 확률 |
| 112 | **119 만 사용한다** (정합성 평가 C-04) |
| m / cm / 충만율 | 단위 미확인(`UNCONFIRMED`) |

띄어쓰기를 뺀 형태(`안전경로`·`최적경로`·`자동신고`)도 같이 막는다.
**픽스처 검사에서** `112`는 한글이 든 문장에서만 본다 — 숫자 문자열에서 부분 일치가
나기 때문이다(`distance_m`이 문자열이었다면 `1120`이 걸린다). `web/src` 쪽은 그대로 본다.
**이 표와 `BANNED` 목록이 어긋나면 표를 고친다** — 검사하는 쪽이 테스트다.

## 6. 로컬 실행·검증 명령

전부 저장소 루트에서 실행한다. **Windows는 `make.ps1`, macOS·Linux는 `make.sh`이며
태스크 이름과 검증 단계가 같다.**

```powershell
.\make.ps1 setup       # clone 직후 이것 하나 — 사전 확인 + 설치 + 검증
.\make.ps1 install     # 설치만 (검증은 따로 check)
.\make.ps1 install-model  # 모델·데이터 파이프라인 의존성 (pandas·scikit-learn·pyarrow)
                          # 앱 실행에는 필요 없다. 픽스처를 다시 만들 때만 쓴다
.\make.ps1 api         # 백엔드 개발 서버  http://127.0.0.1:8000
.\make.ps1 web         # 프론트 개발 서버  http://127.0.0.1:5173
.\make.ps1 fixtures    # DS-* 데모 픽스처·거부 예제 + 안전거점 후보 목록 재생성
.\make.ps1 contracts   # 모든 계약 픽스처 검증
.\make.ps1 test        # Python 테스트
.\make.ps1 typecheck   # TypeScript 검사
.\make.ps1 webtest     # 프론트 smoke test
.\make.ps1 build       # 프론트 production build
.\make.ps1 check       # 위 검증 전부 (커밋·PR 전에 이것만 통과하면 된다)
```

**PR을 올리기 전에 `.\make.ps1 check`(또는 `./make.sh check`)가 통과해야 한다.**
`api`와 `check`는 출력을 `logs/`에 남긴다. 장애 대응은 [docs/OPERATIONS.md](docs/OPERATIONS.md).

### 두 실행 스크립트를 함께 고친다

`make.ps1`에 태스크를 더하면 `make.sh`에도 더한다. 하나만 고치면
`tests/test_portability.py`가 실패한다 — 한쪽에만 명령이 생기면 다른 플랫폼
팀원은 그 명령을 쓸 수 없고, 보통 아무도 그 사실을 모른다.

## 6.1 플랫폼 이식성 — 한쪽에서만 터지는 것들

Windows·macOS를 섞어 쓴다. 아래는 **만든 사람 기계에서는 멀쩡한** 종류라
사람이 눈으로 잡지 못한다. `tests/test_portability.py`가 지킨다.

| 규칙 | 정본 |
|---|---|
| 줄바꿈은 저장소가 정한다. **개인 `core.autocrlf`에 맡기지 않는다** | `.gitattributes` — `*.sh`는 LF, `*.ps1`·`*.bat`는 CRLF |
| Node 팀 표준은 **v24.19.0**, 하한은 **22.12** | `.nvmrc` / `web/package.json` `engines` |
| **절대경로를 코드에 박지 않는다** | 경로는 `Path(__file__)` 기준으로만 만든다 |

- `.sh`가 CRLF로 저장되면 macOS에서 `$'\r': command not found`로 죽는다. `.bat`은 반대다.
- 일부러 둔 플랫폼별 경로(글꼴 후보 등)는 그 줄에 **`portability-ok: <사유>`**를 적는다.
  사유 없이 예외를 만들지 않는다.
- 주석 안의 절대경로는 통과시킨다 — 실행을 깨뜨리지 않고, "예전에는 이랬다"를
  적어두는 것이 다음 사람에게 필요하다.

## 7. 비밀정보와 대용량 데이터

- `secrets/`는 **절대 커밋하지 않는다.** 서울시 OpenAPI 키는 `secrets/seoul_openapi_key.txt`에서만 읽는다.
- 키·토큰·좌표 원문을 로그, 픽스처, 커밋 메시지, 이슈에 남기지 않는다.
- `.env`는 커밋하지 않는다. 새 환경변수는 **`.env.example`에 이름과 설명만** 추가한다.
- 원본 데이터(약 7.5GB)와 `data/` 침수흔적도는 커밋하지 않는다. 공식 포털에서 각자 내려받는다.
- 산출물은 `data_unified/processed/v2/`에만 쓴다. **원본(raw)은 절대 수정하지 않는다.**
- 새 데이터 파일을 추가하기 전에 `git check-ignore -v <path>`로 제외되는지 먼저 확인한다.

## 8. 계약 변경 규칙

계약을 바꿀 때는 **네 곳을 같은 커밋에서** 함께 고친다. 하나라도 빠지면 통합이 깨진다.

1. `contracts/schema/<name>.schema.json`
2. `contracts/fixtures/**` — 영향받는 픽스처 전부. 생성기가 있으면 `.\make.ps1 fixtures`
3. `tests/` — 계약 테스트와 **거부 케이스**
4. `web/src/contracts/types.ts` + `enums.ts` — UI 타입과 화면 문구

그리고:

- 스키마는 **JSON Schema Draft 2020-12**를 쓴다.
- 기존 스키마를 통째로 교체하지 말고 **먼저 비교한 뒤 최소 변경**한다. 기존 픽스처가 깨지는지 반드시 확인한다.
- **소비자 블록을 잊지 않는다.** `official` 블록은 `official_info`·`action_decision`·
  `assess_response` 세 곳에 복사돼 있다. 생산자에만 필드를 더하면 소비자가
  `additionalProperties: false`로 거부한다 — 실제로 두 번 밟았다(C-11 · C-21).
- **거부 예제를 함께 만든다.** 계약이 무엇을 막는지는 통과 예제가 아니라 거부 예제가 증명한다.
  거부 예제는 **의도한 사유 하나로만** 실패해야 하며, 고치면 통과하는 것까지 확인한다.
- 계약을 바꿨으면 `docs/DECISIONS.md`에 한 줄 남긴다.
- **enum과 required 필드 변경은 G3 이후 금지한다.**
- 계약 스키마·공용 enum·정책 설정·통합 응답 타입은 **단일 소유자만 수정한다**
  ([docs/HACKATHON_11H_RUNBOOK.md](docs/HACKATHON_11H_RUNBOOK.md) 소유권 표 참조).

### 새로 만드는 보장에는 "이것을 깨뜨리면 무엇이 빨개지는가"를 답한다

답이 없으면 그 보장은 없는 것이다. 실제로 이 저장소에서 세 번 있었다.

- 스키마 파일은 있는데 아무 픽스처도 그것으로 검증되지 않았다 (C-12)
- 테스트가 픽스처를 **정제해서** 넣어 "그대로 받는다"를 증명하지 못했다 (C-21)
- enum 사본을 한 곳만 읽어 나머지를 고쳐도 아무것도 빨개지지 않았다

**새 검사를 넣었으면 일부러 깨뜨려 실패를 확인하고 되돌린다.**

## 9. 미확정 정책을 코드로 확정하지 않는다

> **임의의 안전정책을 만들어 넣지 않는다.**

**2026-08-16 최종 회의가 OPEN 7개를 닫았고, 같은 날 O-11·O-12·O-15 가 닫혔다.
2026-08-17 실사가 O-16 을 열었고 같은 날 팀장 승인으로 닫았다(C-28). C-32(안전거점 후보
집합)도 소유자 결정으로 닫혔다.** 남은 것은 하나이며 목록은
[docs/DECISIONS.md](docs/DECISIONS.md) 3절에 있다.

- O-13 목적지 지정 지점 목록 확정 (좌표 `APPROX_UNVERIFIED`)

**C-32 는 안전거점 후보 집합만 닫았다.** 대피시설 107곳을 경로 범위 1km 로 걸러 7곳으로
고정했을 뿐이며(`contracts/safe_points.json`), 후보 순위·`relative_risk` 산식·수용인원
반영·시설 상태 연동은 그대로 열려 있다. 기준을 새로 만든 것이 아니라 RT-15·O-09 에서
이미 닫힌 범위를 적용한 것이라 이 절에 걸리지 않는다. **그 경계를 넘어 순위를 코드에
넣지 않는다** — `tests/test_safe_points.py` 가 후보에 `rank`·`relative_risk` 가 섞이면 실패한다.

규칙:

- **행동을 바꾸는 경로 후처리는 `MOVE + NO_SAFE_ROUTE → WAIT` 하나뿐이다.** 후처리는 정확히 한 번만 수행하고 경로 엔진을 재호출하지 않는다.
- 나머지 실패 조합은 **1차 행동을 유지하고 실패 사유만 표시**한다(M-15·M-16). 유지도 확정된 규칙이며 "아직 안 정함"이 아니다. 계약이 유지에서 벗어난 응답을 거부한다.
- `EVACUATE` 경로 실패를 `EMERGENCY`로 자동 전환하지 **않는다.** 실제 고립 신고만 `EMERGENCY`로 간다. 119 강조는 안내 문구 한 줄이며 `EMERGENCY` 레이아웃으로 승격하는 것이 아니다.
- 위험값이 낮아졌다는 이유로 `WAIT → MOVE` 자동 복귀시키지 **않는다**(M-17·M-39). 진동 완화는 AI 예측 단계에만 있다.
- **데이터 신선도 단계는 10분과 30분 둘뿐이다**(M-08). 20분 단계를 두지 않는다. 30분을 넘겨도 무조건 `WAIT`이 아니며 고립 신고·지하 현장 징후·공식 대피 지시가 먼저 이긴다.
- 미확정 항목은 스키마 `description`과 코드 주석에 `OPEN:` 접두사로 표시한다.
- 값이 필요해서 임시로 골랐다면 `OPEN` + 결정 기한 + 임시값임을 함께 적는다. 조용히 확정하지 않는다.
- 강우 기준값(TH-01/TH-02)이 만드는 결과는 **`WAIT`까지**다. 강우량만으로 `EVACUATE`를 반환하지 않는다. 강우는 등급 축에서 AI `HIGH`와 함께 `DANGER`를 만들 수 있지만 **단독으로는 `CAUTION`을 넘지 못한다.**
- **두 기준값이 두 축에서 다르게 쓰인다**(O-15 → C-27). 행동 축(규칙 9 → `WAIT`)은 `TH-01 OR TH-02`이고, **등급 축의 `DANGER` 추가 신호는 TH-02 하나뿐**이다. TH-01은 강우 사건 22개 중 14개에서 걸려 너무 흔해서, 등급에 넣으면 `DANGER`가 `AI HIGH`와 같아진다. 그래서 화면에 **`CAUTION` + `WAIT`이 함께 나오는 것은 의도된 조합**이다.

## 10. 모듈 책임과 의존 방향

의존은 **한 방향으로만** 흐른다. 화살표를 거스르는 import를 만들지 않는다.

```
contracts/  (스키마·픽스처 — 아무것도 import 하지 않음)
    ↑            ↑            ↑
services/    services/       api/  ────→  web/  (HTTP 로만 연결)
 decision      route
    ↑____________↑
         api/
```

| 모듈 | 책임 | import 해도 되는 것 | 하면 안 되는 것 |
|---|---|---|---|
| `contracts/` | JSON Schema·픽스처·계약 검증 | 없음 | 서비스 코드 import |
| `services/decision/` | **순수** 결정 로직. 입력→출력 함수만 | `contracts` | I/O, HTTP, 파일 읽기, `services/route` |
| `services/route/` | 후보 경로 비교 인터페이스 | `contracts`, **`services.decision.enums` (아래 예외)** | `services/decision`의 그 밖의 모듈 |
| `api/` | 세 계약을 묶어 `AssessResponse` 하나를 제공 | `services/*`, `contracts` | UI 로직, 정책 판정 |
| `web/` | 모바일 단일 화면 렌더링 | HTTP API 응답만 | 정책 재구현, 임계값 하드코딩 |
| `scripts/` | 데이터·모델 파이프라인, 문서용 렌더 (기존 자산) | `scripts/mareungil`, **읽기 전용으로 `services/*`** | `api`, `web` |
| `tests/` | 계약·정책·API 통합 테스트 | 전부 | — |

### 예외 하나 — `services/route` → `services/decision/enums`

경로 엔진은 `Action`·`RouteStatus`·`RouteTarget`·`Profile`을 쓸 수밖에 없는데, 4절이
Python enum 정본을 `services/decision/enums.py` 하나로 못 박았다. 두 규칙이 그대로는
동시에 성립하지 않으므로 **`services/route`가 `services.decision.enums`만 import하는 것을
허용한다.** 현재 유일한 사용처는 `services/route/interface.py`다.

허용 범위는 **enum 모듈 하나**다. `postprocess`·`service_risk`·`official`은 여전히 금지다 —
막으려던 것은 **정책 판정이 두 방향으로 흐르는 것**이지 값 이름을 공유하는 것이 아니다.
enum을 중립 위치로 옮기면 이 예외는 사라지지만, 그건 계약 주변을 건드리는 변경이라
G3 이후로 미뤘다.

### `scripts/`가 `services/`를 읽는 것은 허용이다

문서용 그림은 **코드를 실제로 호출해** 표를 채운다. `render_service_risk_matrix.py`가
`classify()`를 불러 등급 열을 만드는 것이 그 예다 — 손으로 옮겨 적으면 그림과 코드가
조용히 어긋나기 때문이다. 금지는 반대 방향이다.

- `scripts/`는 `api`·`web`을 import하지 않는다.
- **앱과 테스트는 렌더 스크립트를 import하지 않는다.** 렌더 전용 의존(Pillow 등)이
  앱 `.venv`로 새어 들어오면 설치 시간이 늘고 clone 직후 실행이 깨진다.

추가 규칙:

- `services/decision/`은 **순수 함수**만 둔다. 같은 입력이면 항상 같은 출력이어야 한다(N-04 재현성).
  `datetime.now()`·`today()`·파일 읽기·네트워크를 쓰지 않는다. 시각은 **입력으로 받는다.**
- UI는 `Date.now()`로 시각을 만들지 않는다. **항상 `clock.label`을 그대로 표시한다.**
- UI는 임계값을 다시 적용하지 않는다. 등급·행동은 API 응답을 그대로 쓴다.
- 런타임에 예측·판정을 위한 외부 API를 호출하지 않는다. 유일한 런타임 외부 의존은 지도 타일이며, **타일이 실패해도 위험·행동·시각·119는 보여야 한다.**
- 네트워크 호출은 `web/src/api.ts` 한 곳에만 둔다.
- `scripts/mareungil/config.py`의 값은 데이터 계약이다. 바꾸면 데이터셋을 전부 다시 만들어야 한다.

## 11. 범위 밖 (이번 MVP에 넣지 않는다)

- **분 단위 급등 감시** — 급변 감시규칙을 붙이지 않기로 확정했다(M-06). [분단위 해상도 확장계획](docs/마른길_분단위_해상도_확장계획.md) 참조
- **그래프 라우팅** — 새 경로를 만들지 않고 공식 대피경로 30개 후보를 상대 비교한다(M-20·M-22). 2020 보행망으로 2022년 경로를 생성하지 않는다
- **조기 고립 예측** — 도로정보와 정답 라벨이 없다. `trapped=true → EMERGENCY`만 쓴다(M-19)
- **자동 재탐색** — 통제·시설 변화를 감지해 스스로 다시 계산하지 않는다. 재판단은 **수동 버튼**이다(M-18)
- **민간건물 임시 안전거점** — 후속 실증에서 조건을 확인한 시설만 후보로 넣는다(M-25)
- **시설 상태 연동** — MVP는 고정 픽스처(`DS-S7`·`DS-S8`)로 흐름만 시연한다(M-32)
- 실시간 외부 API 연동, 로그인·설정·이력·온보딩
- 데이터베이스, 인증, 마이크로서비스 분리, Docker 의무화
- 자유 좌표·자유 텍스트 목적지 입력
- 도로 침수 여부의 직접 예측, 물리 단위(m·cm·충만율) 표시

## 12. 어디를 먼저 읽을 것인가

| 알고 싶은 것 | 파일 |
|---|---|
| 무엇을 정했고 무엇을 아직 안 정했나 | [docs/DECISIONS.md](docs/DECISIONS.md) — 회의 확정은 2.3, OPEN은 3절 |
| 지금 실제로 구현된 것 | [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md) 6절 |
| 계약이 무엇을 막는가 | `contracts/fixtures/invalid/` — 거부 예제가 답이다 |
| 목적지·안전거점으로 무엇을 고를 수 있나 | `contracts/destinations.json`(`MOVE`, 초안 5개) · `contracts/safe_points.json`(`EVACUATE`, 확정 7곳) |
| 장애가 나면 누가 무엇을 하나 | [docs/OPERATIONS.md](docs/OPERATIONS.md) |
| 발표에서 무엇을 숨기지 말아야 하나 | [docs/HACKATHON_CHECKLIST.md](docs/HACKATHON_CHECKLIST.md) |
