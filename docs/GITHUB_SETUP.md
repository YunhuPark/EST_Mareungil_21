# GitHub 저장소 만들기와 5인 공유

> 이 문서의 `git push` 는 **아직 실행하지 않았다.** 명령만 적어 두었고, 실행은 저장소 주인이 판단한다.

## 1. 결론부터 — 새 폴더를 만들지 않는다

**지금 `C:\2026_Mareungil` 을 그대로 올린다.** 새 폴더를 파서 옮기는 편이 나은 상황이 아니다.

| 판단 근거 | 확인한 사실 |
|---|---|
| Git 이력이 이미 있다 | 커밋 2개(`0ad0765`, `e3f7f8c`)에 데이터셋·모델 파이프라인 구축 이력이 들어 있다. 새 폴더로 옮기면 이 이력이 사라진다 |
| 커밋 대상 용량이 작다 | 추적 파일 55개 · **8.4MB**. GitHub 에 올리기에 아무 문제가 없다 |
| `.gitignore` 가 이 트리 구조에 맞춰져 있다 | `secrets/`, `data_unified/raw/`, `data_unified.zip` 이 이미 정확히 제외되고 있다. 폴더를 새로 파면 이 규칙을 다시 맞춰야 한다 |
| 문서가 상대경로로 서로를 참조한다 | `README.md` → `data_unified/processed/v2/README.md`, 설계서 → `./diagrams/*.png`, `config.py` → `data_unified/...`. 위치가 바뀌면 전부 깨진다 |
| 위험 요소는 이미 정리했다 | 유일한 문제였던 `PoC1/` 79MB CSV 는 이번에 삭제했다. 남은 대용량은 전부 `.gitignore` 안에 있다 |

즉 새 폴더가 해결해 줄 문제가 하나도 없고, 잃을 것(이력·경로·ignore 규칙)만 있다.

> **다만 `git push` 전에 반드시 확인한다.** 아래 4절의 안전 점검을 건너뛰지 않는다.
> 원본 데이터 7.5GB 와 API 키가 같은 트리 안에 있으므로, 실수로 한 번 올라가면
> 이력에서 지우는 데 시간이 든다.

## 2. 저장소 주인이 할 일 (1회, 약 5분)

```powershell
cd C:\2026_Mareungil

# 1) 무엇이 올라갈지 눈으로 확인한다 (아무것도 바꾸지 않는 명령)
git status --short
git ls-files | Measure-Object -Line

# 2) 대용량·비밀이 제외되는지 확인한다. 출력이 나오면 제외되고 있다는 뜻이다
git check-ignore -v secrets/ data_unified.zip data_unified/raw/ data/ web/node_modules/

# 3) 스테이징 후, 실제로 올라갈 목록을 마지막으로 본다
git add -A
git status --short
git diff --cached --stat | Select-Object -Last 5
```

`git diff --cached --stat` 의 합계가 **10MB 를 크게 넘으면 멈추고** 무엇이 들어갔는지 본다.

```powershell
# 4) 커밋
git commit -m "chore: bootstrap 11-hour hackathon workspace"

# 5) GitHub 저장소 생성 + 연결 + 첫 push
#    gh CLI 가 있으면 이 한 줄로 생성·연결·push 가 끝난다.
gh repo create mareungil --private --source=. --remote=origin --push
```

`gh` 가 없다면 GitHub 웹에서 **빈** 저장소를 만든 뒤(README·.gitignore 체크 해제):

```powershell
git remote add origin https://github.com/<계정>/mareungil.git
git branch -M main
git push -u origin main
```

> **Private 로 만든다.** 발표 전까지 공개할 이유가 없고, 원본 데이터 출처·좌표
> 품질 등급이 정리되기 전에 공개되면 잘못 인용되기 쉽다.

## 3. 팀원 4명 초대

저장소 → **Settings → Collaborators and teams → Add people** 에서 GitHub 계정으로 초대한다.
권한은 **Write** 를 준다. Admin 은 주인 1명만 갖는다.

초대받은 사람이 하는 일은 이게 전부다.

```powershell
git clone https://github.com/ayj9665-wq/EST_Mareungil_21.git
cd EST_Mareungil_21
.\make.ps1 setup       # 사전 확인 + 설치 + 검증까지 한 번에
```

`setup` 이 **"환경 준비 완료"** 를 출력하지 않으면 개발을 시작하지 말고 먼저 해결한다.
여기서 막히는 사람이 있으면 그 시간이 11시간에서 그대로 빠진다.

### 여기서 걸리는 두 가지

| 증상 | 원인 | 해결 |
|---|---|---|
| `이 시스템에서 스크립트를 실행할 수 없으므로` | PowerShell 실행 정책 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 한 번만 |
| `python`·`npm` 을 찾을 수 없다고 나온다 | PATH 에 없음 | `setup` 이 무엇을 설치해야 하는지 알려준다. 설치 후 **PowerShell 창을 새로 연다** — PATH 변경은 열려 있는 창에 반영되지 않는다 |

### 데이터는 clone 에 들어 있지 않다

- 모델링용 `data_unified/processed/v2/*.parquet` 는 **포함돼 있다.** 평가·모델 스크립트는 바로 돈다.
- 원본 약 7.5GB(`data_unified/raw/`)와 침수흔적도(`data/`)는 포함돼 있지 않다.
  필요한 사람만 공식 포털에서 받는다 — 출처는 `README.md` 참조.
- **앱 개발자(프론트·백엔드)는 원본 데이터가 전혀 필요 없다.** 픽스처만으로 끝까지 만들 수 있다.

## 4. push 전 안전 점검 (매번)

| 확인 | 명령 | 통과 기준 |
|---|---|---|
| 비밀정보 | `git check-ignore -v secrets/ .env` | 두 줄 다 출력된다 |
| 대용량 | `git ls-files \| ForEach-Object { (Get-Item $_).Length } \| Measure-Object -Sum` | 합계가 10MB 근처 |
| 키 문자열 | `git diff --cached -S "seoul_openapi" --stat` | 출력 없음 |
| 빌드 산출물 | `git status --short` | `web/dist`, `node_modules`, `__pycache__` 가 안 보인다 |
| 검증 | `.\make.ps1 check` | 전부 통과 |

**`git add -A` 를 습관적으로 쓰지 않는다.** 이 저장소에는 추적하지 않는 대용량 파일이
같은 트리에 있다. 바꾼 파일을 이름으로 지정해 stage 하는 편이 안전하다.

## 5. 11시간용 브랜치 규칙

30시간짜리 정식 흐름을 만들 시간이 없다. 아래 정도가 적당하다.

```
main                      항상 .\make.ps1 check 가 통과하는 상태로 유지
  feat/decision-engine    담당자별 작업 브랜치
  feat/route-candidates
  feat/ui-states
  feat/contracts-g0
```

- 브랜치 이름은 `feat/<담당영역>` 으로 통일한다.
- **하루에 여러 번 `main` 을 받아온다.** 하루 끝에 한 번 합치면 그때 통합이 터진다.

  ```powershell
  git fetch origin
  git rebase origin/main      # 충돌이 작을 때 자주 처리한다
  ```
- PR 은 만들되 리뷰로 막지 않는다. **`.\make.ps1 check` 통과가 유일한 머지 조건**이다.
- G0(T+1:30) 이후 계약을 바꾸는 PR 은 계약 소유자가 직접 올리거나 승인한다.

### 브랜치 보호는 걸지 않는다

11시간 안에 required review 를 걸면 사람이 잠들거나 자리를 비운 순간 팀 전체가 멈춘다.
대신 `main` 이 깨지면 즉시 되돌린다.

```powershell
git revert <커밋해시>       # reset --hard 로 지우지 않는다. 남의 작업이 사라진다
```

## 6. 동시 수정 충돌을 막는 유일한 방법 — 단일 소유자

통합이 깨지는 원인의 대부분은 로직이 아니라 **같은 파일을 두 사람이 동시에 고치는 것**이다.
아래 파일은 **한 사람만** 고친다. 다른 사람은 필요하면 그 사람에게 말한다.

| 파일 | 단일 소유자 | 왜 |
|---|---|---|
| `contracts/schema/*.json` | 계약 오너 | 4대 계약의 정본 |
| `services/decision/enums.py` | 계약 오너 | enum Python 사본 |
| `web/src/contracts/enums.ts` · `types.ts` | 계약 오너 | enum·타입 TS 사본 |
| `contracts/fixtures/official/official_0808.json` | 기획 PM | 공식정보·데모 시각 |
| `contracts/destinations.json` | 경로·데이터 담당 | 지정 지점 목록 |
| `api/main.py` | 백엔드 담당 | 통합 응답 조립 |

세 곳의 enum 이 어긋나면 `tests/test_enum_sync.py` 가 실패하므로 조용히 넘어가지는 않는다.
자세한 담당 배치는 [HACKATHON_11H_RUNBOOK.md](./HACKATHON_11H_RUNBOOK.md) 참조.

## 7. 사고가 났을 때

| 상황 | 대응 |
|---|---|
| 비밀 키를 커밋했다 (push 전) | `git reset --soft HEAD~1` 후 파일 제외하고 다시 커밋 |
| 비밀 키를 push 했다 | **먼저 서울시 포털에서 키를 재발급한다.** 이력 정리는 그 다음이다. 이미 노출된 키는 지워도 노출된 것이다 |
| 대용량 파일을 push 했다 | `git rm --cached <파일>` + `.gitignore` 추가 후 커밋. 이력에서 완전히 빼야 하면 `git filter-repo` 를 쓰되 팀 전원이 다시 clone 해야 한다 |
| `main` 이 깨졌다 | `git revert`. 되돌린 뒤에 원인을 본다 |
