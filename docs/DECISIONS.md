# 결정 기록

> 이 파일은 **무엇을 정했고 무엇을 아직 안 정했는지**를 한 곳에서 본다.
> "아직 안 정함"을 지우지 않는 것이 이 문서의 목적이다.
> 최초 작성: 2026-08-15 (부트스트랩)

## 1. 이번 부트스트랩에서 내린 기술 선택

| ID | 결정 | 대안 | 왜 이걸 골랐나 |
|---|---|---|---|
| D-01 | **저장소를 새로 만들지 않고 기존 `C:\2026_Mareungil` 을 그대로 쓴다** | 새 폴더에 정리해서 올리기 | 커밋 2개의 데이터·모델 이력이 있고, 추적 용량이 8.4MB 로 작으며, `.gitignore` 와 문서 상대경로가 이 트리에 맞춰져 있다. 유일한 위험이던 `PoC1/` 79MB CSV 는 삭제했다. 자세한 근거는 [GITHUB_SETUP.md](./GITHUB_SETUP.md) 1절 |
| D-02 | **백엔드는 FastAPI + uvicorn** | Flask, Django, Node/Express | 저장소 자산이 전부 Python(pandas·scikit-learn·jsonschema)이라 판단 엔진을 같은 언어로 붙일 수 있다. 자동 `/docs` 로 다섯 명이 계약을 눈으로 확인할 수 있는 것도 11시간에서는 실질적 이득이다. Node 로 가면 예측 결과를 프로세스 경계 너머로 넘겨야 한다 |
| D-03 | **DB 를 두지 않는다** | SQLite, Postgres | 재생 모드는 상태가 없다. 픽스처 파일이 곧 데이터이고, 상태가 없어야 데모 중 백엔드를 재시작해도 즉시 복구된다 |
| D-04 | **Docker 를 쓰지 않는다** | docker-compose | 다섯 명 전원 Windows 로컬 개발이다. 이미지 빌드 시간이 11시간에서 그대로 빠진다 |
| D-05 | **계약 합성 검증** — `AssessResponse` 안의 `risk`·`route` 를 각 스키마로 따로 검증한다 | 스키마 간 `$ref` | 기존 `$id` 가 `mareungil/risk_assessment@v1` 같은 상대 URI 라 `$ref` 해석이 도구마다 달라진다. 합성 검증은 각 계약 파일을 독립적으로 열 수 있게 두면서 같은 보장을 준다. 소유 관계는 `contracts/validate.py` 의 `COMPOSED_BLOCKS` 한 곳에 적혀 있다 |
| D-06 | **`react-leaflet` 대신 `leaflet` 직접 사용** | react-leaflet | 의존성 하나와 React 버전 결합을 줄인다. 지도는 실패해도 되는 블록이라 `useEffect` + `try/catch` 20줄이 오히려 실패 처리를 명시적으로 만든다 |
| D-07 | **CSS 프레임워크를 넣지 않는다** | Tailwind, MUI | 화면이 하나다. 빌드 설정과 학습 비용이 산출물보다 크다 |
| D-08 | **의존성을 앱용/모델용으로 나눈다** | 하나의 requirements | 앱 개발자 3명은 pandas·scikit-learn 이 필요 없다. 설치 시간도 11시간의 일부다 |
| D-09 | **enum 을 세 곳에 두고 테스트로 묶는다** | 코드 생성 | 생성기를 만들 시간에 `tests/test_enum_sync.py` 가 같은 일을 한다. 어긋나면 CI 가 아니라 로컬 `check` 에서 즉시 잡힌다 |
| D-10 | **`AssessResponse` 에 `primary_action` 과 `action` 을 함께 싣는다** | `action` 하나 | `DS-S5`(`MOVE`+`NO_SAFE_ROUTE`→`WAIT`)에서 경로 도달 대상은 1차 행동이 정한 것이고 화면에 보이는 행동은 후처리 결과다. 하나로 합치면 `route_target=USER_DESTINATION` 인데 `action=WAIT` 인 상태를 계약으로 설명할 수 없다 |
| D-11 | **`source_kind` 필드로 픽스처/실제를 구분한다** | 없음 | mock 을 실제 모델 결과처럼 보이지 않게 하는 장치다. UI 가 이 값으로 배지를 띄운다 |

## 2. 확정 사항 (문서에서 이미 결정된 것 중 코드에 반영한 것)

| ID | 내용 | 근거 | 코드 위치 |
|---|---|---|---|
| C-01 | 경로 후처리는 `MOVE + NO_SAFE_ROUTE → WAIT` **하나뿐** | F-10, C-31 | `services/decision/postprocess.py` |
| C-02 | `NO_SAFE_POINT` 는 `EVACUATE` 전용, `DESTINATION_BLOCKED` 은 `MOVE` 전용 | RT-13 | `assess_response.schema.json` `allOf` |
| C-03 | `no_safe_route=true` 는 `route_attempted=true` 일 때만 | RT-09b | `safe_route.schema.json` `allOf` |
| C-04 | 목적지는 필수. `null` 은 계약 검증 실패 | F-19, R13 | `assess_response.schema.json` |
| C-05 | 이름만 `risk_level` 인 필드를 두지 않는다 | AI-10 | `tests/test_contracts.py` |
| C-06 | 경로 상태에 `UNAVAILABLE` 을 쓰지 않는다 | RT-09, C-08 | `safe_route.schema.json` |
| C-07 | `WHEELCHAIR`·`WITH_PET` 은 계약 enum 에서 제외 | C-14 | `tests/test_contracts.py` |
| C-08 | `trapped=true` 는 최우선 | F-05, C-28 | `assess_response.schema.json` `allOf` |
| C-09 | 이유는 최대 3개 | F-03 | `assess_response.schema.json` `maxItems` |
| C-10 | 분 단위 급등 감시는 MVP 범위 밖 | 확장계획 8장 | `CLAUDE.md` 10절 |

## 3. 미확정 (OPEN) — **코드로 확정하지 않는다**

각 항목의 담당자와 기한은 **G0(T+1:30)에서 채운다.** 지금은 비어 있다.

| ID | 미확정 항목 | 왜 못 정했나 | 임시값 사용 여부 | 결정 기한 | 담당 |
|---|---|---|---|---|---|
| **O-01** | **TH-04 지역 집계 규칙과 지역 단위 임계값** | TH-03(0.33)은 **센서 단위**로만 검증됐다. 지역에 그대로 옮긴 근거가 없다. 현재 "상위 25% 평균"은 회복 국면을 못 따라간다 — 피크 `RF-S3` 0.9995 인데 회복 `RF-S4` 도 0.964다 | **예.** `DS-S1` 은 센서 임계 0.33 을 지역에 임시 적용했다. 확률 0.1086 은 임계와 0.22 떨어져 있어 집계 규칙이 바뀌어도 `LOW` 가 뒤집힐 가능성은 낮다. 픽스처의 `_open_th04` 에 표시됨 | G2 | E |
| **O-02** | `EVACUATE` + `NO_SAFE_POINT` 의 최종 행동 | 안전정책이다. 대피하라고 했는데 갈 곳이 없을 때 무엇을 말할지는 팀이 임의로 정할 수 없다 | 아니오. 1차 행동을 그대로 둔다 | G2 | 기획 PM |
| **O-03** | `EVACUATE` + `NO_SAFE_ROUTE` / `DATA_UNAVAILABLE` 의 최종 행동 | 위와 같음. **`EMERGENCY` 로 자동 전환하지 않는다**(C-31) | 아니오 | G2 | 기획 PM |
| **O-04** | `MOVE` + `DESTINATION_BLOCKED` 의 최종 행동 | 목적지 변경 안내 외에 행동을 바꿀지 미정 | 아니오 | G2 | 기획 PM |
| **O-05** | `MOVE` + `DATA_UNAVAILABLE` 의 최종 행동 | 경로 판단 불가일 때 `MOVE` 를 유지할지 미정 | 아니오 | G2 | 기획 PM |
| **O-06** | P1/P2 프로필 수치 (우회 상한 1.15, 경사 가중 1.5, 무가중 5%) | 초안이며 검증되지 않았다 | **예.** 초안값이 문서에 있으나 코드에 넣지 않았다 | G2 | 기획 PM |
| **O-07** | 목적지 차단 판정 기준 | "공식 통제 + 확인된 침수"까지는 정했으나 판정 세부(버퍼 거리 등)가 없다 | 아니오. `official_0808.json` 의 `blocks_destination_ids` 로 명시 지정만 한다 | G2 | C |
| **O-08** | 서비스 상태에 적용할 히스테리시스 | 현재 `HIGH_LEVEL_MARGIN=0.05` 는 모델 평가에서 `AMBIGUOUS` 를 빼는 데만 쓰이고 서비스가 보는 상태에는 적용되지 않는다 | 아니오 | G2 | E |
| **O-09** | 경로 범위 안에 들어오는 센서 수 | 아직 세지 않았다. 범위를 넓힐지 지역 위험을 다시 계산할지가 여기 달렸다 | 아니오 | G1 | C, E |
| **O-10** | 그래프 라우팅 채택 여부 (RT-08) | G1 에서 **1회만** 판단한다. 실패 시 재시도 없이 후보 방식 고정 | 아니오 | G1 | C |
| **O-11** | 공식정보 픽스처의 실제 값 | 2022-08-08 경보·통제 원출처를 아직 확인하지 않았다 | **아니오 — 값을 지어내지 않았다.** 형식만 만들고 `verification: DRAFT_UNVERIFIED` 로 표시했다 | G0 | 기획 PM |
| **O-12** | 데모 시각 확정 | 20:00·20:10·20:20·20:40·20:55 는 초안이다. `official_0808.json` 의 `asof` 가 확정한다 | **아니오.** UI 는 항상 `clock.label` 을 쓴다 | G0 | 기획 PM |
| **O-13** | 지정 지점 목록 확정 | 현재 5개는 초안이고 좌표가 수동 검증 전이다(`APPROX_UNVERIFIED`) | **예.** 초안 5개를 넣었고 파일에 `_status: DRAFT` 로 표시했다 | T+12h → 11h 계획에서는 G2 | C |
| **O-14** | `threshold_basis` 를 `TEAM_AGREED` 로 전환 | 기존 픽스처는 `val_events@fpr_0.05`(모델 평가 근거)를 쓰고 있다. 서비스 운영 임계는 팀 합의값이어야 한다 | 아니오. 스키마에 목표를 적어두고 기존 값을 통과시킨다 | G0 | E |

### OPEN 항목을 다룰 때의 규칙

1. **임의로 값을 정해 코드에 넣지 않는다.** 임시값을 써야 하면 위 표의 "임시값 사용 여부"에 적고, 코드·스키마 주석에 `OPEN:` 을 남긴다.
2. 확정하면 이 표에서 3절 → 2절로 옮기고 근거를 적는다.
3. `services/decision/postprocess.py` 의 `OPEN_TRANSITIONS` 에 규칙을 추가하려면 **먼저 여기 해당 항목을 닫아야 한다.**
4. 발표에서 OPEN 을 숨기지 않는다. [11시간 실행계획](./HACKATHON_11H_RUNBOOK.md) G2-4 참조.

## 4. 문서 사이에서 발견한 불일치

| ID | 위치 | 내용 | 어떻게 처리했나 |
|---|---|---|---|
| X-01 | MVP 설계서 12장 (541~542행) | "목적지 선택 해제 가능", "목적지 선택 전" 안내 문구가 남아 있다. 그런데 같은 문서 5.3 과 요구사항 F-19·UI-10 은 **목적지가 필수이며 미선택 상태를 두지 않는다**고 한다 | **필수 선택으로 간다.** 근거 우선순위 1위인 `action_decision.schema.json` 이 이미 `destination` 을 `required` 로 두고 `null` 을 막고 있다. 12장 문구는 rev.5 이전의 잔재로 판단했다. 설계서 12장 수정은 A 가 G0 에서 처리 |
| X-02 | 문서 정합성 평가서 C-17 | `RiskAssessment.risk_level` 이라고 적혀 있으나, 같은 문서 C-08 과 요구사항 AI-10 은 이름만 `risk_level` 인 필드를 금지한다 | `ai_risk_level` 로 간다. `tests/test_contracts.py` 가 모든 스키마에서 `risk_level` 필드를 막는다 |
| X-03 | 요구사항 정의서 13.1 vs 10.1 | 규칙 시나리오가 `R1~R13` 과 `R1~R15` 로 다르게 적혀 있다 | `R1~R15` 로 본다(10.1 이 더 상세하고 최신) |

## 5. 이번 부트스트랩에서 하지 않은 것

문서에 있으나 **구현하지 않았다.** 완료로 표시하지 않는다.

- 행동 우선순위 1~10 판정 본체 (T+3:00~6:00)
- 공식 대피경로 30개 후보의 실제 비교 (T+6:00~8:00)
- `DS-S2` ~ `DS-S6` 픽스처 (T+6:00~8:00)
- 대피시설 107개 안전거점 선택 로직
- 데이터 품질 규칙 DQ-01~05 구현
- 프로필 P1/P2 의 후보 순서 조정
- 침수흔적 지도 레이어
