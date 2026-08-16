"""플랫폼 이식성 — Windows·macOS 를 섞어 쓰는 팀에서 조용히 깨지는 것들.

여기서 막는 것은 넷이다. 넷 다 **한쪽 기계에서는 멀쩡하고 다른 쪽에서만** 터지는
종류라, 만든 사람은 끝까지 모른다.

1. 절대경로를 코드에 박는 것 — `C:\\2026_Mareungil\\...` 는 남의 기계에 없다.
2. 줄바꿈 규칙이 없는 것 — `.sh` 가 CRLF 로 저장되면 Mac 에서 실행이 죽는다.
3. 두 실행 스크립트가 어긋나는 것 — `make.ps1` 에만 태스크가 생기면 Mac 팀원은
   그 명령을 쓸 수 없다.
4. Node 기준이 두 곳에서 다른 것 — `.nvmrc` 와 `package.json` 이 다르면
   "표준을 맞췄다"가 거짓이 된다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

#: 검사할 소스. 생성물·의존성·로그는 뺀다.
SKIP_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
    "logs", "dist", "data_unified", "data", "reports", "secrets",
}
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".json", ".ps1", ".sh", ".toml", ".css", ".html"}


#: 이 파일은 검사 대상에서 뺀다. 금지하는 모양을 **예시로 적어 두는 곳**이라
#: 스스로를 검사하면 항상 걸린다. 금칙어 검사(test_forbidden_wording.py)가 자기
#: BANNED 목록을 검사하지 않는 것과 같은 이유다.
SELF = Path(__file__).resolve()


def source_files() -> list[Path]:
    out = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        if path.resolve() == SELF:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        out.append(path)
    return sorted(out)


SOURCES = source_files()


def test_검사할_소스가_있다():
    assert len(SOURCES) > 50, f"소스를 {len(SOURCES)}개만 찾았다. SKIP_DIRS 가 너무 넓은지 보라"


# --- 1. 절대경로 ------------------------------------------------------------

#: 남의 기계에 존재하지 않는 경로 모양.
ABSOLUTE_PATH_PATTERNS = [
    (re.compile(r"[A-Za-z]:[\\/]{1,2}(?!\s)"), "Windows 드라이브 절대경로 (예: C:\\2026_Mareungil)"),
    (re.compile(r"/Users/[A-Za-z0-9._-]+/"), "macOS 홈 절대경로"),
    (re.compile(r"/home/[A-Za-z0-9._-]+/"), "Linux 홈 절대경로"),
]

#: 절대경로처럼 보이지만 경로가 아닌 것. 좁게 둔다 — 넓히면 검사가 조용히 무력해진다.
ABSOLUTE_PATH_ALLOW = re.compile(r"https?://")

#: 주석 시작. **주석 안의 절대경로는 실행을 깨뜨리지 않는다.** 오히려 "예전에는
#: 이랬다"를 적어두는 것이 다음 사람에게 필요하다.
COMMENT_PREFIXES = ("#", "//", "<#", "*", '"""', "'''")

#: 일부러 둔 플랫폼별 경로에 붙이는 표시. **사유를 함께 적는다.**
#: 글꼴 후보처럼 "여러 OS 경로를 나열하는 것이 곧 이식성"인 자리가 있다.
PORTABILITY_OK = "portability-ok:"


def test_절대경로를_코드에_박지_않는다():
    """경로는 `Path(__file__)` 기준 상대경로로 만든다.

    이 검사를 처음 넣었을 때 **실제로 네 곳이 걸렸다.**
    `scripts/mareungil/config.py` 와 `scripts/build_sewer_sensor_metadata.py` 의
    `ROOT = Path(r"C:\\2026_Mareungil")`, 렌더 스크립트의 docstring 예시와
    `C:\\Windows\\Fonts`. 앞의 둘은 **그 기계 밖에서는 아무도 파이프라인을 돌릴
    수 없게** 만들고 있었다.

    두 가지는 통과시킨다.

    - **주석**: 주석 안의 경로는 실행을 깨뜨리지 않는다. "예전에는 이랬다"를
      적어두는 것이 오히려 필요하다.
    - **`portability-ok:` 표시가 붙은 줄**: 글꼴 후보처럼 여러 OS 경로를
      나열하는 것이 곧 이식성인 자리가 있다. 사유를 함께 적게 한다.
    """
    hits = []
    for path in SOURCES:
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith(COMMENT_PREFIXES) or PORTABILITY_OK in line:
                continue
            for pattern, what in ABSOLUTE_PATH_PATTERNS:
                for m in pattern.finditer(line):
                    fragment = line[max(0, m.start() - 20):m.end() + 40]
                    if ABSOLUTE_PATH_ALLOW.search(fragment):
                        continue
                    rel = path.relative_to(ROOT).as_posix()
                    hits.append(f"{rel}:{lineno}  ({what})\n      {line.strip()[:100]}")
    assert not hits, (
        "절대경로가 소스에 있다. Path(__file__) 기준 상대경로로 바꾼다.\n"
        "일부러 둔 플랫폼별 경로라면 그 줄에 `portability-ok: <사유>` 를 적는다.\n  "
        + "\n  ".join(hits)
    )


# --- 2. 줄바꿈 --------------------------------------------------------------

GITATTRIBUTES = ROOT / ".gitattributes"


def test_gitattributes가_줄바꿈을_고정한다():
    """개인 `core.autocrlf` 에 맡기지 않는다.

    개인 설정은 사람마다 다르고, 다른 사람 화면에서만 재현되는 diff 를 만든다.
    """
    assert GITATTRIBUTES.exists(), ".gitattributes 가 없다"
    text = GITATTRIBUTES.read_text(encoding="utf-8")

    assert re.search(r"^\*\s+text=auto", text, re.MULTILINE), (
        "`* text=auto` 가 없다. 저장소 기본 정규화가 걸리지 않는다"
    )
    # 줄바꿈이 틀리면 **실행이 깨지는** 두 종류는 명시적으로 못박혀 있어야 한다.
    assert re.search(r"^\*\.sh\s+.*eol=lf", text, re.MULTILINE), (
        "`*.sh eol=lf` 가 없다. CRLF 로 저장되면 macOS 에서 "
        r"`$'\r': command not found` 로 죽는다"
    )
    assert re.search(r"^\*\.bat\s+.*eol=crlf", text, re.MULTILINE), (
        "`*.bat eol=crlf` 가 없다. cmd.exe 가 LF 만 있는 배치를 잘못 읽는다"
    )


def test_셸_스크립트가_LF로_저장돼_있다():
    """규칙만 적어두고 파일이 이미 CRLF 면 아무것도 지켜지지 않는다."""
    hits = []
    for path in ROOT.glob("*.sh"):
        if b"\r\n" in path.read_bytes():
            hits.append(path.name)
    assert not hits, f"셸 스크립트에 CRLF 가 있다: {hits}. macOS 에서 실행이 죽는다"


# --- 3. 두 실행 스크립트 ----------------------------------------------------

MAKE_PS1 = ROOT / "make.ps1"
MAKE_SH = ROOT / "make.sh"


def ps1_tasks() -> set[str]:
    """`make.ps1` 의 ValidateSet 에 적힌 태스크 이름."""
    text = MAKE_PS1.read_text(encoding="utf-8-sig")
    m = re.search(r"\[ValidateSet\((.*?)\)\]", text, re.DOTALL)
    assert m, "make.ps1 에서 ValidateSet 을 찾지 못했다"
    return set(re.findall(r"'([a-z-]+)'", m.group(1)))


def sh_tasks() -> set[str]:
    """`make.sh` 의 case 분기에 적힌 태스크 이름.

    `setup)` 처럼 줄 끝에서 끝나는 분기와 `contracts) assert_venv; ...` 처럼
    같은 줄에 본문이 붙는 분기가 섞여 있으므로 `)` 뒤를 요구하지 않는다.
    """
    text = MAKE_SH.read_text(encoding="utf-8")
    body = text.split('case "$TASK" in', 1)[1]
    found: set[str] = set()
    for line in body.splitlines():
        m = re.match(r"\s{2}([a-z|_-]+)\)", line)
        if not m:
            continue
        for name in m.group(1).split("|"):
            if re.fullmatch(r"[a-z-]+", name):
                found.add(name)
    return found


def test_두_실행_스크립트가_같은_태스크를_제공한다():
    """한쪽에만 태스크가 생기면 다른 플랫폼 팀원은 그 명령을 쓸 수 없다.

    이 검사가 없으면 `make.ps1` 에 태스크를 더한 사람은 아무 경고도 받지 못하고,
    Mac 쪽에서 `알 수 없는 태스크` 가 뜰 때까지 아무도 모른다.

    `help` 별칭(`--help`·`-h`)은 `make.sh` 에만 있고 PowerShell 은 `-?` 로 받으므로
    비교에서 뺀다.
    """
    ps1 = ps1_tasks()
    sh = sh_tasks() - {"--help", "-h"}  # bash 관용 별칭. PowerShell 은 -? 로 받는다.

    assert ps1 == sh, (
        "make.ps1 과 make.sh 의 태스크가 다르다.\n"
        f"  make.ps1 에만: {sorted(ps1 - sh)}\n"
        f"  make.sh 에만:  {sorted(sh - ps1)}"
    )


def test_두_실행_스크립트가_같은_검증_단계를_돈다():
    """`check` 가 플랫폼마다 다른 것을 돌면 '통과했다'가 서로 다른 뜻이 된다."""
    steps = ["계약 검증", "Python 테스트", "TypeScript 검사", "프론트 테스트", "프론트 빌드"]
    ps1 = MAKE_PS1.read_text(encoding="utf-8-sig")
    sh = MAKE_SH.read_text(encoding="utf-8")
    for step in steps:
        assert step in ps1, f"make.ps1 의 check 에 '{step}' 단계가 없다"
        assert step in sh, f"make.sh 의 check 에 '{step}' 단계가 없다"


# --- 4. Node 버전 기준 ------------------------------------------------------

NVMRC = ROOT / ".nvmrc"
PACKAGE_JSON = ROOT / "web" / "package.json"


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])


def test_팀_표준_Node_버전이_한_곳에_적혀_있다():
    assert NVMRC.exists(), ".nvmrc 가 없다. 팀 표준 Node 버전을 적는 곳이다"
    version = NVMRC.read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
        f".nvmrc 는 정확한 버전 하나여야 한다 (예: 24.19.0). 지금: {version!r}"
    )


def test_nvmrc가_package_json_하한을_만족한다():
    """두 파일이 어긋나면 '표준을 맞췄다'가 거짓이 된다.

    역할이 다르다는 점이 핵심이다.
    `engines` 는 **이 아래로는 실제로 깨진다**는 하한이고(Vite 7 요구사항),
    `.nvmrc` 는 **다 같이 이걸 쓰자**는 팀 표준이다. 표준이 하한을 어기면
    `npm ci` 가 경고를 뱉거나 막는다.
    """
    engines = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["engines"]["node"]
    floor = parse_version(engines)
    standard = parse_version(NVMRC.read_text(encoding="utf-8"))
    assert standard >= floor, (
        f".nvmrc({'.'.join(map(str, standard))}) 가 "
        f"package.json engines({engines}) 하한보다 낮다"
    )


@pytest.mark.parametrize("script", [MAKE_PS1, MAKE_SH], ids=["make.ps1", "make.sh"])
def test_두_스크립트가_Node_버전을_확인한다(script: Path):
    """설치 전에 확인하지 않으면, 버전이 낮은 사람은 빌드 단계에서야 알게 된다."""
    text = script.read_text(encoding="utf-8-sig")
    assert ".nvmrc" in text, f"{script.name} 이 .nvmrc 를 읽지 않는다"
    assert "22.12" in text, f"{script.name} 에 Node 하한 검사가 없다"
