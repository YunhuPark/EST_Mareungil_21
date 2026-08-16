#!/usr/bin/env bash
#
# 마른길 개발 명령 모음 — macOS · Linux 용.
#
# 깨끗한 clone 에서 시작할 때, 이 한 줄이면 끝난다:
#
#     ./make.sh setup
#
# Windows 는 `.\make.ps1 setup` 을 쓴다. **두 파일의 태스크 이름은 같다** —
# `tests/test_portability.py` 가 목록이 어긋나면 실패시킨다. 한쪽에만 태스크가
# 생기면 다른 플랫폼 팀원이 그 명령을 쓸 수 없기 때문이다.
#
# 이 파일은 반드시 LF 로 저장한다(.gitattributes 가 `*.sh text eol=lf` 로 고정).
# CRLF 면 `$'\r': command not found` 로 죽는다.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
WEB_DIR="$ROOT/web"
LOG_DIR="$ROOT/logs"

# 색은 터미널일 때만 쓴다. 로그 파일로 리다이렉트하면 제어문자가 섞인다.
if [ -t 1 ]; then
  C_STEP=$'\033[36m'; C_OK=$'\033[32m'; C_BAD=$'\033[31m'
  C_HINT=$'\033[33m'; C_DIM=$'\033[90m'; C_OFF=$'\033[0m'
else
  C_STEP=''; C_OK=''; C_BAD=''; C_HINT=''; C_DIM=''; C_OFF=''
fi

step() { printf '\n%s=== %s ===%s\n' "$C_STEP" "$1" "$C_OFF"; }
ok()   { printf '%s  OK  %s%s\n' "$C_OK" "$1" "$C_OFF"; }
bad()  { printf '%s  !!  %s%s\n' "$C_BAD" "$1" "$C_OFF"; }
hint() { printf '%s%s%s\n' "$C_HINT" "$1" "$C_OFF"; }

assert_venv() {
  if [ ! -x "$PY" ]; then
    bad "Python 가상환경이 없다. 먼저 실행: ./make.sh install"
    exit 1
  fi
}

assert_node() {
  if [ ! -d "$WEB_DIR/node_modules" ]; then
    bad "프론트 의존성이 없다. 먼저 실행: ./make.sh setup"
    exit 1
  fi
}

# 설치 전에 python3·node 가 실제로 실행되는지 본다. 없는 상태로 install 을 돌리면
# `command not found` 만 남아서, 처음 clone 한 사람은 무엇을 깔아야 하는지 모른다.
assert_prereq() {
  step '사전 확인'
  local missing=0

  if command -v python3 >/dev/null 2>&1; then
    local major minor
    major="$(python3 -c 'import sys;print(sys.version_info[0])')"
    minor="$(python3 -c 'import sys;print(sys.version_info[1])')"
    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 11 ]; }; then
      bad "Python $major.$minor - 3.11 이상이 필요하다 (pyproject.toml requires-python)."
      missing=$((missing + 1))
    else
      ok "Python $major.$minor"
    fi
  else
    bad 'python3 가 PATH 에 없다. https://www.python.org 또는 `brew install python@3.13`'
    missing=$((missing + 1))
  fi

  if command -v npm >/dev/null 2>&1; then
    check_node_version
  else
    bad 'npm 이 PATH 에 없다. https://nodejs.org 또는 `brew install node`'
    missing=$((missing + 1))
  fi

  if [ "$missing" -gt 0 ]; then
    printf '\n%s위 %s 건을 설치한 뒤 터미널을 새로 열고 다시 실행한다.%s\n' "$C_BAD" "$missing" "$C_OFF"
    hint 'PATH 변경은 이미 열려 있는 창에 반영되지 않는다.'
    exit 1
  fi
}

# Node 버전을 두 단계로 본다.
#   하한(package.json engines) 미만 -> 실패. 여기 아래로는 Vite 7 이 실제로 안 돈다.
#   팀 표준(.nvmrc) 과 다름         -> 경고만. 패치 차이로 설치를 막지 않는다.
check_node_version() {
  local current standard
  current="$(node --version | sed 's/^v//')"
  standard="$(tr -d ' \t\r\n' < "$ROOT/.nvmrc")"

  local cur_major floor_major floor_minor cur_minor
  cur_major="${current%%.*}"
  floor_major=22
  floor_minor=12
  cur_minor="$(printf '%s' "$current" | cut -d. -f2)"

  if [ "$cur_major" -lt "$floor_major" ] ||
     { [ "$cur_major" -eq "$floor_major" ] && [ "$cur_minor" -lt "$floor_minor" ]; }; then
    bad "Node $current - 22.12 이상이 필요하다 (web/package.json engines · Vite 7 요구사항)."
    hint "  nvm install $standard && nvm use"
    exit 1
  fi

  if [ "$current" = "$standard" ]; then
    ok "Node v$current (팀 표준) / npm $(npm --version)"
  else
    ok "Node v$current / npm $(npm --version)"
    hint "  팀 표준은 v$standard 다 (.nvmrc). 맞추려면: nvm install && nvm use"
  fi
}

install_all() {
  step 'Python 가상환경'
  if [ ! -x "$PY" ]; then
    python3 -m venv "$VENV"
  fi
  "$PY" -m pip install --upgrade pip --quiet
  "$PY" -m pip install -r "$ROOT/requirements-dev.txt"
  ok '앱 의존성 설치 완료'

  step '프론트엔드 의존성'
  if [ -f "$WEB_DIR/package-lock.json" ]; then
    (cd "$WEB_DIR" && npm ci)
  else
    (cd "$WEB_DIR" && npm install)
  fi
  ok '프론트 의존성 설치 완료'
}

# OPS-02. 창을 닫으면 traceback 이 사라진다. 화면에 그대로 보여주면서 logs/ 에도 남긴다.
# logs/ 는 .gitignore 로 제외된다 - 요청 경로에 목적지 id 가 실리므로 커밋하지 않는다.
new_log() {
  mkdir -p "$LOG_DIR"
  local log="$LOG_DIR/$1.log"
  # 덮어쓰지 않고 이어 붙인다. 덮어쓰면 "죽어서 다시 띄웠다" 는 순간 원인이 지워진다.
  printf '\n===== %s  %s =====\n' "$1" "$(date '+%Y-%m-%d %H:%M:%S')" >> "$log"
  printf '%s' "$log"
}

# 한 단계 실행하고 성패를 기록한다. 실패해도 즉시 멈추지 않고 끝까지 돌린 뒤
# 마지막에 요약한다 - 한 번에 무엇이 깨졌는지 다 보는 편이 빠르다.
CHECK_FAILED=0
CHECK_NAMES=()
CHECK_RESULTS=()

run_step() {
  local name="$1" log="$2"; shift 2
  step "$name"
  printf '\n--- %s ---\n' "$name" >> "$log"
  # set -e 가 걸려 있으므로 실패를 직접 받는다. `|| rc=$?` 없이 두면 첫 실패에서
  # 스크립트가 죽어 나머지 단계를 못 돌린다.
  local rc=0
  { "$@" 2>&1 || rc=$?; } | tee -a "$log"
  # 파이프라인이라 "$@" 의 종료코드는 PIPESTATUS 에 있다. rc 는 서브셸 것이라 못 쓴다.
  rc="${PIPESTATUS[0]}"
  if [ "$rc" -eq 0 ]; then
    ok "$name"; printf 'OK   %s\n' "$name" >> "$log"
    CHECK_RESULTS+=("ok")
  else
    bad "$name"; printf 'FAIL %s\n' "$name" >> "$log"
    CHECK_RESULTS+=("fail")
    CHECK_FAILED=$((CHECK_FAILED + 1))
  fi
  CHECK_NAMES+=("$name")
}

# 각 단계를 함수로 둔다. `env -C` 를 쓰지 않는 이유는 **macOS 의 BSD env 에 -C 가
# 없기** 때문이다 - 리눅스에서만 돌고 정작 이 파일이 필요한 Mac 에서 죽는다.
_c_contracts() { (cd "$ROOT" && "$PY" -m contracts.validate); }
_c_pytest()    { (cd "$ROOT" && "$PY" -m pytest); }
_c_typecheck() { (cd "$WEB_DIR" && npm run typecheck); }
_c_webtest()   { (cd "$WEB_DIR" && npm run test); }
_c_build()     { (cd "$WEB_DIR" && npm run build); }

run_check() {
  local log; log="$(new_log check)"
  CHECK_FAILED=0; CHECK_NAMES=(); CHECK_RESULTS=()

  run_step '계약 검증'       "$log" _c_contracts
  run_step 'Python 테스트'   "$log" _c_pytest
  run_step 'TypeScript 검사' "$log" _c_typecheck
  run_step '프론트 테스트'    "$log" _c_webtest
  run_step '프론트 빌드'      "$log" _c_build

  step '요약'
  printf '\n--- 요약 ---\n' >> "$log"
  local i
  for i in "${!CHECK_NAMES[@]}"; do
    if [ "${CHECK_RESULTS[$i]}" = 'ok' ]; then
      ok "${CHECK_NAMES[$i]}"; printf 'OK   %s\n' "${CHECK_NAMES[$i]}" >> "$log"
    else
      bad "${CHECK_NAMES[$i]}"; printf 'FAIL %s\n' "${CHECK_NAMES[$i]}" >> "$log"
    fi
  done
  printf '%s  로그: %s%s\n' "$C_DIM" "$log" "$C_OFF"
}

usage() {
  cat <<'EOF'
마른길 개발 명령 (macOS · Linux)

  ./make.sh setup           clone 직후 이것 하나. 사전 확인 + 설치 + 검증까지
  ./make.sh install         설치만 (검증은 따로 check)
  ./make.sh install-model   모델 파이프라인 의존성 (AI·데이터 담당만)

  ./make.sh api             백엔드 개발 서버   http://127.0.0.1:8000
  ./make.sh web             프론트 개발 서버   http://127.0.0.1:5173

  ./make.sh contracts       모든 계약 픽스처 검증
  ./make.sh fixtures        DS 픽스처 재생성
  ./make.sh test            Python 테스트
  ./make.sh webtest         프론트 smoke test
  ./make.sh typecheck       TypeScript 검사
  ./make.sh build           프론트 production build
  ./make.sh check           위 검증 전부 (커밋·PR 전에 이것만 통과하면 된다)

Windows 는 같은 이름으로 .\make.ps1 <task> 를 쓴다.
EOF
}

TASK="${1:-help}"

case "$TASK" in

  # clone 직후 한 줄로 끝내는 명령. 사전 확인 -> 설치 -> 검증까지 이어서 한다.
  # install 과 check 를 따로 치게 두면 검증을 건너뛴 사람이 반드시 나온다.
  setup)
    assert_prereq
    install_all
    step '검증'
    run_check
    if [ "$CHECK_FAILED" -gt 0 ]; then
      printf '\n%s설치는 됐지만 검증 %s 건이 실패했다. 개발을 시작하기 전에 위 메시지를 본다.%s\n' \
        "$C_BAD" "$CHECK_FAILED" "$C_OFF"
      exit 1
    fi
    printf '\n%s환경 준비 완료. 바로 시작해도 된다.%s\n' "$C_OK" "$C_OFF"
    hint '  ./make.sh api    백엔드  http://127.0.0.1:8000'
    hint '  ./make.sh web    프론트  http://127.0.0.1:5173'
    ;;

  install)
    assert_prereq
    install_all
    printf '\n'; hint '다음: ./make.sh check'
    ;;

  install-model)
    assert_venv
    step '모델 파이프라인 의존성 (pandas·scikit-learn·pyarrow)'
    "$PY" -m pip install -r "$ROOT/requirements-model.txt"
    ok '설치 완료'
    ;;

  api)
    assert_venv
    step '백엔드 개발 서버'
    API_HOST="${MAREUNGIL_API_HOST:-127.0.0.1}"
    API_PORT="${MAREUNGIL_API_PORT:-8000}"
    hint "  http://${API_HOST}:${API_PORT}/docs"
    # OPS-02. api/main.py 는 픽스처를 import 시점에 읽는다. 픽스처가 깨지면 요청할
    # 때가 아니라 서버가 아예 안 뜨고, 그 traceback 이 이 창에만 있었다.
    LOG="$(new_log api)"
    printf '%s  로그: %s%s\n' "$C_DIM" "$LOG" "$C_OFF"
    # -u : 출력이 파이프로 가면 파이썬이 버퍼링해서 로그가 뭉텅이로 늦게 나온다.
    (cd "$ROOT" && "$PY" -u -m uvicorn api.main:app --reload --host "$API_HOST" --port "$API_PORT" 2>&1) | tee -a "$LOG"
    ;;

  web)
    assert_node
    step '프론트엔드 개발 서버'
    hint '  http://127.0.0.1:5173'
    (cd "$WEB_DIR" && npm run dev)
    ;;

  fixtures)
    assert_venv
    step 'DS 픽스처 재생성'
    (cd "$ROOT" && "$PY" scripts/build_demo_assess_fixtures.py)
    ;;

  contracts) assert_venv; (cd "$ROOT" && "$PY" -m contracts.validate) ;;
  test)      assert_venv; (cd "$ROOT" && "$PY" -m pytest) ;;
  typecheck) assert_node; (cd "$WEB_DIR" && npm run typecheck) ;;
  webtest)   assert_node; (cd "$WEB_DIR" && npm run test) ;;
  build)     assert_node; (cd "$WEB_DIR" && npm run build) ;;

  check)
    assert_venv
    assert_node
    run_check
    if [ "$CHECK_FAILED" -gt 0 ]; then
      printf '\n%s실패 %s 건. 고치고 다시 실행하라.%s\n' "$C_BAD" "$CHECK_FAILED" "$C_OFF"
      exit 1
    fi
    printf '\n%s전부 통과. 커밋해도 된다.%s\n' "$C_OK" "$C_OFF"
    ;;

  help|--help|-h) usage ;;
  *) bad "알 수 없는 태스크: $TASK"; printf '\n'; usage; exit 1 ;;
esac
