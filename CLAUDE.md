# CLAUDE.md — 마른길 저장소 작업 규칙

이 파일은 사람과 Claude Code가 **같은 규칙으로** 이 저장소를 고치기 위한 기준이다.
코드를 고치기 전에 이 문서를 먼저 읽는다.

## 1. 프로젝트 한 문장

마른길은 2022년 8월 8일 강남 집중호우를 재생해, 사용자가 침수 상황에서
**지금 위험한가**와 **지금 무엇을 해야 하는가**를 한 화면에서 확인하는 모바일 웹 MVP다.

**교육·시연용이며 공식 재난안전 판단 도구가 아니다.** 이 고지는 화면에 항상 노출한다.

## 2. 문서 및 계약 우선순위

충돌하면 위에서부터 이긴다.

1. **현재 재현 가능한 데이터 산출물과 `contracts/schema/`의 실제 스키마**
2. [요구사항 정의서](docs/마른길_요구사항_정의서.md) · [MVP 설계서](docs/마른길_MVP_설계서.md)
3. [문서 정합성 평가서](docs/마른길_문서_정합성_평가.md)의 최종 결정
4. 그 밖의 과거 계획·발표·보고 자료

낮은 우선순위 자료를 폐기하라는 뜻이 아니라, **수치·enum·범위를 덮어쓰지 않는다**는 뜻이다.

## 3. 구현 완료와 목표 설계의 구분

> **문서에 적혀 있다는 이유만으로 구현 완료로 간주하지 않는다.**

- 문서는 대부분 **목표 설계**다. 현재 체크아웃에서 실제로 확인한 것만 "구현됨"이라고 쓴다.
- 코드·문서·응답에서 mock / stub / fixture는 **명시적으로 그렇게 표시**한다.
- mock 값을 실제 모델 결과나 완성된 기능처럼 표현하지 않는다.
- 현재 상태는 [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md)에 기록한다.

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
| 경로 도달 대상 | `SafeRoute.route_target` | `USER_DESTINATION` `SAFE_POINT` `null` |
| 근거 | `reasons[].basis` | `OFFICIAL_GUIDANCE` `AI_PREDICTION` `TEAM_RULE` |

### 계약에 두지 않는 것

- 이름이 **그냥 `risk_level`인 필드**. 두 위험 축은 항상 `ai_risk_level` / `service_risk_level`로 구분한다.
- `UNKNOWN`, `EMERGENCY_ASSIST`, `AVAILABLE`, `WITHHELD`
- `WHEELCHAIR`, `WITH_PET` (검증 데이터 부족으로 MVP 제외)
- `SafeRoute.status`의 `UNAVAILABLE` — 경로 단절은 `DATA_UNAVAILABLE`이다

### 사용자 화면 금지 표현

`tests/test_forbidden_wording.py`가 `web/src/`를 검사한다.

| 금지 | 대신 쓸 표현 |
|---|---|
| 안전 경로, 최적 경로, 검증된 경로 | 공식 대피경로 기준 · 상대적으로 위험이 낮은 후보 |
| 실시간 | 2022년 과거 기록 재생 |
| 자동 신고, 자동 위치 전송 | 전화 앱 연결과 위치 문구 복사 |
| 길안내, 내비게이션 | 목적지까지 · 추천 후보 경로 |
| 도로 침수 예측 | 하수관로 고수위 확률 |
| m / cm / 충만율 | 단위 미확인(`UNCONFIRMED`) |

## 5. 로컬 실행·검증 명령

Windows PowerShell 기준. 전부 저장소 루트에서 실행한다.

```powershell
.\make.ps1 install     # Python .venv + 프론트 의존성 설치 (최초 1회)
.\make.ps1 api         # 백엔드 개발 서버  http://127.0.0.1:8000
.\make.ps1 web         # 프론트 개발 서버  http://127.0.0.1:5173
.\make.ps1 contracts   # 모든 계약 픽스처 검증
.\make.ps1 test        # Python 테스트
.\make.ps1 typecheck   # TypeScript 검사
.\make.ps1 webtest     # 프론트 smoke test
.\make.ps1 build       # 프론트 production build
.\make.ps1 check       # 위 검증 전부 (커밋·PR 전에 이것만 통과하면 된다)
```

**PR을 올리기 전에 `.\make.ps1 check`가 통과해야 한다.**

## 6. 비밀정보와 대용량 데이터

- `secrets/`는 **절대 커밋하지 않는다.** 서울시 OpenAPI 키는 `secrets/seoul_openapi_key.txt`에서만 읽는다.
- 키·토큰·좌표 원문을 로그, 픽스처, 커밋 메시지, 이슈에 남기지 않는다.
- `.env`는 커밋하지 않는다. 새 환경변수는 **`.env.example`에 이름과 설명만** 추가한다.
- 원본 데이터(약 7.5GB)와 `data/` 침수흔적도는 커밋하지 않는다. 공식 포털에서 각자 내려받는다.
- 산출물은 `data_unified/processed/v2/`에만 쓴다. **원본(raw)은 절대 수정하지 않는다.**
- 새 데이터 파일을 추가하기 전에 `git check-ignore -v <path>`로 제외되는지 먼저 확인한다.

## 7. 계약 변경 규칙

계약을 바꿀 때는 **네 곳을 같은 커밋에서** 함께 고친다. 하나라도 빠지면 통합이 깨진다.

1. `contracts/schema/<name>.schema.json`
2. `contracts/fixtures/**` — 영향받는 픽스처 전부
3. `tests/` — 계약 테스트와 거부 케이스
4. `web/src/contracts/types.ts` + `enums.ts` — UI 타입

그리고:

- 스키마는 **JSON Schema Draft 2020-12**를 쓴다.
- 기존 스키마를 통째로 교체하지 말고 **먼저 비교한 뒤 최소 변경**한다. 기존 픽스처가 깨지는지 반드시 확인한다.
- 계약을 바꿨으면 `docs/DECISIONS.md`에 한 줄 남긴다.
- **enum과 required 필드 변경은 G3 이후 금지한다.**
- 계약 스키마·공용 enum·정책 설정·통합 응답 타입은 **단일 소유자만 수정한다**
  ([docs/HACKATHON_11H_RUNBOOK.md](docs/HACKATHON_11H_RUNBOOK.md) 소유권 표 참조).

## 8. 미확정 정책을 코드로 확정하지 않는다

> **임의의 안전정책을 만들어 넣지 않는다.**

현재 `OPEN`인 항목은 [docs/DECISIONS.md](docs/DECISIONS.md)에 목록으로 있다. 대표적으로:

- TH-04 지역 집계 규칙과 지역 단위 임계값
- `EVACUATE` + 경로 실패(`NO_SAFE_POINT` / `NO_SAFE_ROUTE` / `DATA_UNAVAILABLE`)의 최종 행동
- `MOVE` + `DESTINATION_BLOCKED` / `DATA_UNAVAILABLE`의 최종 행동
- P1/P2 프로필 수치(우회 상한 1.15, 경사 가중치 1.5)

규칙:

- **현재 확정된 경로 후처리는 `MOVE + NO_SAFE_ROUTE → WAIT` 하나뿐이다.** 후처리는 정확히 한 번만 수행하고 경로 엔진을 재호출하지 않는다.
- `EVACUATE` 경로 실패를 `EMERGENCY`로 자동 전환하지 **않는다.**
- 미확정 항목은 스키마 `description`과 코드 주석에 `OPEN:` 접두사로 표시한다.
- 값이 필요해서 임시로 골랐다면 `OPEN` + 결정 기한 + 임시값임을 함께 적는다. 조용히 확정하지 않는다.
- 강우 기준값(TH-01/TH-02)이 만드는 결과는 **`WAIT`까지**다. 강우량만으로 `EVACUATE`를 반환하지 않는다.

## 9. 모듈 책임과 의존 방향

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
| `services/route/` | 후보 경로 비교 인터페이스 | `contracts` | `services/decision` |
| `api/` | 세 계약을 묶어 `AssessResponse` 하나를 제공 | `services/*`, `contracts` | UI 로직, 정책 판정 |
| `web/` | 모바일 단일 화면 렌더링 | HTTP API 응답만 | 정책 재구현, 임계값 하드코딩 |
| `scripts/` | 데이터·모델 파이프라인 (기존 자산) | `scripts/mareungil` | `api`, `web` |
| `tests/` | 계약·정책·API 통합 테스트 | 전부 | — |

추가 규칙:

- `services/decision/`은 **순수 함수**만 둔다. 같은 입력이면 항상 같은 출력이어야 한다(N-04 재현성).
- UI는 `Date.now()`로 시각을 만들지 않는다. **항상 `clock.label`을 그대로 표시한다.**
- UI는 임계값을 다시 적용하지 않는다. 등급·행동은 API 응답을 그대로 쓴다.
- 런타임에 예측·판정을 위한 외부 API를 호출하지 않는다. 유일한 런타임 외부 의존은 지도 타일이며, **타일이 실패해도 위험·행동·시각·119는 보여야 한다.**
- `scripts/mareungil/config.py`의 값은 데이터 계약이다. 바꾸면 데이터셋을 전부 다시 만들어야 한다.

## 10. 범위 밖 (이번 MVP에 넣지 않는다)

- **분 단위 급등 감시** — G2 이후 별도 브랜치. [분단위 해상도 확장계획](docs/마른길_분단위_해상도_확장계획.md) 참조
- 실시간 외부 API 연동, 로그인·설정·이력·온보딩
- 데이터베이스, 인증, 마이크로서비스 분리, Docker 의무화
- 자유 좌표·자유 텍스트 목적지 입력
- 도로 침수 여부의 직접 예측, 물리 단위(m·cm·충만율) 표시
