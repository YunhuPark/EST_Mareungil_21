# 모듈별 운영 담당과 장애 대응

> 작성: 2026-08-15 · [HACKATHON_11H_RUNBOOK.md](./HACKATHON_11H_RUNBOOK.md) 1절의 **코드 소유권**을
> **운영 책임**으로 확장한 것이다. 코드를 고치는 사람과 장애를 처리하는 사람을 같게 둔다.
>
> **전제: 이 프로젝트에는 배포가 없다.** CI(`.github/`)도 없다. 전원 Windows 로컬에서
> `.\make.ps1 api` / `.\make.ps1 web` 두 창으로 돌린다(D-03·D-04).
> 따라서 "모니터링"은 자동 감시가 아니라 **사람이 정해진 명령을 정해진 시점에 치는 것**이다.
>
> 로그는 `api` 와 `check` 만 `logs\` 에 남긴다(OPS-02). `logs\` 는 `.gitignore` 로 제외된다.

## 1. 대응 표

| 모듈 | 운영자 | 정상 확인 방법 | 오류 로그 위치 | 복구 순서 |
|---|---|---|---|---|
| **계약·픽스처** `contracts/` | **A · 안윤지** | `.\make.ps1 contracts` 통과 | `logs\check.log` | ① 위반 경로 확인 → ② 스키마가 아니라 **픽스처를 고친다** → ③ `.\make.ps1 fixtures` 로 재생성 → ④ 안 되면 `git checkout -- contracts/fixtures/` |
| **API 서버** `api/` | **B · 유진희** | `curl http://127.0.0.1:8000/api/health` → `{"status":"ok"}` · `/docs` 열림 | **`logs\api.log`** (창을 닫아도 남는다) | ① `logs\api.log` 끝을 본다 → ② 창 재실행 → ③ 그래도 안 뜨면 아래 2.2 |
| **결정 엔진** `services/decision/` | **B · 유진희** | `.\make.ps1 test` — `tests/test_postprocess.py` 통과 | `logs\check.log` | ① 실패 테스트 이름 확인 → ② `git log --oneline -10` → ③ `git revert <해시>`. **`reset --hard` 를 쓰지 않는다** |
| **경로 엔진** `services/route/` | **C · 박윤후** | `.\make.ps1 contracts` 에서 `route` 블록이 `safe_route` 스키마를 통과 | API 500 응답의 `contract_violations` · `logs\check.log` | ① `route_target`·`status` 조합이 C-02/C-03 을 어겼는지 본다 → ② 픽스처 되돌림 → ③ 후처리는 **재호출하지 않는다**(C-01) |
| **AI · 예측** `scripts/` | **E · 안윤지** (A 겸임) | `.\make.ps1 fixtures` 후 `.\make.ps1 contracts` + `tests/test_area_risk.py` 통과 | 스크립트 stdout · `logs\check.log` | ① 재생성 결과와 커밋본을 `git diff` 로 대조 → ② 등급이 뒤집혔으면 `AREA_THRESHOLD`(0.5) 비교인지 확인(C-20) → ③ `git checkout -- contracts/fixtures/` |
| **UI** `web/` | **D · 정예지** | 5173 화면에 **위험·위치·행동·재생시각·119** 다섯이 보인다 · `.\make.ps1 typecheck` `webtest` `build` | 브라우저 콘솔 + `.\make.ps1 web` 창(vite) · 빌드·테스트는 `logs\check.log` | ① 화면의 오류 문구를 읽는다([App.tsx:50-60](../web/src/App.tsx#L50-L60) 이 백엔드 주소까지 알려준다) → ② vite 창 재시작 → ③ `Remove-Item -Recurse -Force web\node_modules; .\make.ps1 setup` |
| **지도 타일** (외부) | **D · 정예지** | 타일이 안 떠도 위 다섯이 남는지 | 브라우저 Network 탭 | **대응 불필요.** [MapPanel.tsx:84-88](../web/src/components/MapPanel.tsx#L84-L88) 이 이미 안내 문구로 대체한다. 발표에서 "지도는 외부 타일이라 없어도 판단은 보입니다"라고 말한다 |
| **공식정보 픽스처** | **PM · 안려현** | `official_0808.json` 의 `verification` 값 | — | 값이 없으면 비운 채로 간다(런북 G0 실패 시 절차) |

## 2. 알아차리는 순서 — 지금은 자동이 아무것도 없다

### 2.1 누가 먼저 보나

| 시점 | 누가 | 무엇을 |
|---|---|---|
| 커밋·PR 전 | **본인** | `.\make.ps1 check` (CLAUDE.md 6절) |
| 각 구간 경계 | **A · 안윤지** | `.\make.ps1 check` 를 `main` 에서 한 번. **통합이 깨진 걸 아는 유일한 지점이다** |
| 데모 중 | **D** 화면 / **B** api 창 | D 는 다섯 요소, B 는 uvicorn 창의 500 |

**A 가 계약·AI·통합 감시 셋을 동시에 든다**(OPS-01 확정). 부하가 몰리는 배치라는 점은
그대로이므로, 구간 경계의 `check` 를 거르면 통합이 깨진 걸 아무도 모르는 상태가 된다.

### 2.2 API 가 안 뜰 때 — 가장 자주 만날 장애

[api/main.py:55-58](../api/main.py#L55-L58) 이 픽스처와 스키마를 **import 시점에** 읽는다.
즉 픽스처 하나가 깨지면 **요청할 때가 아니라 서버가 아예 안 뜬다.**
traceback 은 `logs\api.log` 끝에 남는다 — 창을 이미 닫았어도 여기서 본다.

```
증상: .\make.ps1 api 가 traceback 을 내고 멈춘다 / health 가 연결 거부
  ↓
0. logs\api.log 의 마지막 traceback 을 읽는다   ← 대개 여기서 파일 이름까지 나온다
1. .\make.ps1 contracts     ← 여기서 잡히면 계약 문제다. 운영자를 A 로 넘긴다
2. 통과하는데도 안 뜨면      ← 파이썬·의존성 문제다. 운영자는 B
   Remove-Item -Recurse -Force .venv; .\make.ps1 setup
```

**BOM 이 붙은 픽스처는 서버를 죽인다.** [api/fixtures.py:24](../api/fixtures.py#L24) 는
`encoding="utf-8"` 로 읽는데, PowerShell 5.1 의 `Set-Content -Encoding utf8` 과 메모장은
UTF-8 **BOM** 을 붙인다. 전원 Windows 라 실제로 밟는다.

```
json.decoder.JSONDecodeError: Unexpected UTF-8 BOM (decode using utf-8-sig)
```

이 메시지가 나오면 픽스처 내용이 아니라 **저장 인코딩** 문제다. BOM 없는 UTF-8 로 다시
저장한다. `.\make.ps1 contracts` 도 같은 이유로 함께 실패하므로 계약 문제로 오인하기 쉽다.

응답이 계약을 어기면 500 에 `contract_violations` 가 실린다([api/main.py:133-135](../api/main.py#L133-L135)).
**화면이 아니라 여기서 잡히는 게 정상이다.** 이 500 을 UI 문제로 오해하지 않는다.

### 2.3 판단이 안 서면 넘기는 방향

```
화면이 이상하다  → D 가 본다
  └ 화면에 "응답을 불러오지 못했습니다" → B (API)
      └ .\make.ps1 contracts 가 실패 → A (계약)
          └ risk 블록이 원인 → E
          └ route 블록이 원인 → C
```

## 2.4 장애 리허설 3종 (M-35)

최종 회의에서 **MVP 통합 후 각각 1회씩** 하기로 정했다. 리허설은 "되는지 보는 것"이 아니라
**실패했을 때 화면에 무엇이 남는지 확인하는 것**이다. 세 경우 모두에서 **119 버튼과 기본
행동카드가 남아야 한다** — 그것이 통과 조건이다.

| # | 만드는 상황 | 어떻게 만드나 | 통과 조건 | 담당 |
|---|---|---|---|---|
| 1 | **네트워크 OFF → 백업화면 → 복구** | `api` 창을 닫는다 (또는 Wi-Fi 끔) | 화면이 "응답을 불러오지 못했습니다"를 보이고, 이미 받은 응답이 있으면 그것을 유지하며 "갱신에 실패해 이전 응답을 표시하고 있습니다"를 띄운다. 119 와 면책 문구가 남는다. 서버를 다시 띄우면 복구된다 | **D · 정예지** |
| 2 | **AI timeout** → 공식정보·사용자 상태 기반 판단 또는 `DATA_UNAVAILABLE` | `risk` 블록이 없거나 `ai_risk_level: null` 인 픽스처(`RF-E1` 계열)로 요청 | 등급이 `SAFE` 로 떨어지지 않고 `CAUTION` 이상이며 사유에 "지역 위험을 산출할 센서 자료가 없습니다"가 실린다. 고립 신고·공식 대피 지시는 그대로 작동한다 | **E · 안윤지** + **B · 유진희** |
| 3 | **경로 API 실패** → 경로 중단·대체안내 | `route.status` 를 `DATA_UNAVAILABLE` 로 둔 픽스처로 요청 | 임의 경로나 가상 선을 그리지 않는다. 경로 카드가 사유를 표시하고 행동은 1차 행동을 유지한다. `EVACUATE` 였다면 119 강조가 켜진다 | **C · 박윤후** |

**기록할 것.** 장애 발생시각부터 감지 → 백업 전환 → 사용자 안내 → 정상 복구까지를 로그로
남긴다. 장애 시에는 `status`, `scenario_id`, 데이터·정책 버전을 함께 적는다(M-33).

**준비된 고정 픽스처.** 정상 후보(`DS-S1`·`DS-S7`) · `NO_SAFE_POINT`(`DS-S8`) ·
`DESTINATION_BLOCKED`(`DS-S6`).
**리허설 3(경로 실패)은 `DS-S8` 로 지금 그대로 수행할 수 있다.**
`NO_SAFE_ROUTE`(`DS-S5`)와 `DATA_UNAVAILABLE` 은 아직 미작성이며 거부 예제만 있다 —
[fixtures/README](../contracts/fixtures/README.md) 의 상태 표를 본다.

### 담당 (M-33)

**전체 앱의 통합·실행과 개발 세션 종료 후 정상 작동 확인은 안윤지**가 맡는다.
모듈별 오류 확인은 1절 표와 같다: 안윤지=AI, 유진희=결정엔진, 박윤후=경로, 정예지=UI.

## 3. 결정 기록

| ID | 내용 | 상태 |
|---|---|---|
| OPS-01 | **통합 감시 당번은 A · 안윤지.** 계약·예측·감시를 겸임한다 | **확정** 2026-08-15 |
| OPS-02 | **`api` 와 `check` 는 화면 출력을 `logs\` 에 남긴다** | **확정 · 구현됨** `make.ps1` |
| OPS-03 | **CI 를 넣을 것인가** — `.\make.ps1 check` 를 GitHub Actions 로 올리면 push 마다 자동으로 잡힌다 | **OPEN.** 11시간 안에서 그 시간을 쓸지는 별개다 |

OPS-03 을 정하지 않은 상태로 두는 것도 선택이다. 다만 정한 척하지 않는다.

### OPS-02 구현 메모

`make.ps1` 의 `Invoke-Tee` 하나가 `api` 와 `check` 양쪽을 처리한다. 세 가지가 **전부**
있어야 동작하며 하나라도 빠지면 조용히 쓸모없어진다.

| 요소 | 없으면 |
|---|---|
| `2>&1` | uvicorn·pytest 는 진단 출력을 stderr 로 낸다. **정작 필요한 traceback 만 파일에서 빠진다** |
| `$ErrorActionPreference = 'Continue'` | PowerShell 5.1 이 네이티브 stderr 를 `NativeCommandError` 로 승격해 스크립트를 죽인다. uvicorn 은 시작 로그부터 stderr 라 첫 줄에서 끝난다 |
| `Add-Content -Encoding utf8` | `Tee-Object` 는 5.1 에 `-Encoding` 이 없고 기본값이 환경마다 다르다. 다섯 명이 같은 파일을 읽어야 한다 |

`python -u` 도 함께 넣었다. 출력이 파이프로 가면 파이썬이 버퍼링해서 로그가 뭉텅이로 늦게 나온다.

**확인한 것**(추측이 아니라 실제로 돌려봤다):

- `check` 가 성공을 성공으로, 실패를 실패로 보고한다 — 픽스처를 일부러 깨뜨려 `실패 2건` · 종료코드 1 확인.
  **C-16 이 이 함수에서 났으므로 반환값이 Boolean 인 것까지 확인했다**
- 정상 기동 시 uvicorn 기동줄과 `/api/health` 요청이 `logs\api.log` 에 남는다
- 픽스처를 깨뜨려 **서버가 아예 안 뜨는 경우에도** 전체 traceback 이 남는다
- 로그 파일은 UTF-8(BOM) 이고 한글이 깨지지 않는다
- `git check-ignore` 로 `logs/` 가 제외되는 것을 확인했다 (CLAUDE.md 7절)

**`web` 은 일부러 넣지 않았다.** vite 는 출력을 파이프로 넘기면 TTY 기능(키 입력 단축키,
화면 갱신)이 죽는데, 프론트 오류는 브라우저 오버레이와 콘솔에도 그대로 남아서 창이
사라져도 증거가 없어지지 않는다. 필요해지면 `Invoke-Tee` 를 그대로 쓰면 된다.
