"""사용자 화면 금칙어 검사 (설계서 16장, RT-03, F-15, AI-01, AI-08).

`web/src/` 전체를 본다 — 주석도 포함한다. 주석만 예외로 두면 "주석이니까
괜찮다"가 슬금슬금 문구로 넘어온다. 금지된 표현은 아예 쓰지 않고, 왜 쓰면
안 되는지는 이 파일과 CLAUDE.md 에만 적는다.

발표 자료와 문서는 이 검사 대상이 아니다. 여기서 막는 것은 **사용자 화면**이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "web" / "src"
DEMO_DIR = ROOT / "contracts" / "fixtures" / "demo"

# (금지 표현, 대신 쓸 표현)
BANNED = [
    ("안전 경로", "공식 대피경로 기준 · 상대적으로 위험이 낮은 후보"),
    ("안전경로", "공식 대피경로 기준 · 상대적으로 위험이 낮은 후보"),
    ("최적 경로", "추천 후보 경로"),
    ("최적경로", "추천 후보 경로"),
    ("검증된 경로", "추천 후보 경로 (route_verified=false)"),
    ("검증 완료", "검증하지 않았다는 사실을 그대로 표시"),
    ("실시간", "2022년 과거 기록 재생"),
    ("자동 신고", "전화 앱 연결"),
    ("자동신고", "전화 앱 연결"),
    ("자동 위치 전송", "위치 문구 복사"),
    ("길안내", "목적지까지 · 추천 후보 경로"),
    ("내비게이션", "목적지까지 · 추천 후보 경로"),
    ("도로 침수 예측", "하수관로 고수위 확률"),
    ("112", "119 만 사용한다"),
    ("충만율", "단위 미확인(UNCONFIRMED)"),
]

SOURCES = sorted(
    p for p in WEB_SRC.rglob("*") if p.suffix in {".ts", ".tsx", ".css", ".html"}
)


def test_검사할_소스가_있다():
    assert SOURCES, "web/src 에 검사할 파일이 없다"


@pytest.mark.parametrize("banned,instead", BANNED, ids=[b[0] for b in BANNED])
def test_금칙어가_화면_소스에_없다(banned: str, instead: str):
    hits = []
    for path in SOURCES:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if banned in line:
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{lineno}  {line.strip()[:90]}")
    assert not hits, (
        f"금지 표현 '{banned}' 가 화면 소스에 있다. 대신: {instead}\n  " + "\n  ".join(hits)
    )


def test_물리단위를_화면에_붙이지_않는다():
    """AI-07 / 8.4. 관경·영점 미확보라 m·cm 로 환산할 수 없다.

    하수 수위 값에 단위를 붙이는 패턴만 본다. 거리(m)는 경로 표시에 쓰므로
    금지 대상이 아니다.
    """
    hits = []
    for path in SOURCES:
        text = path.read_text(encoding="utf-8")
        for token in ("predicted_level}m", "predicted_level}cm", "수위 ${", "충만"):
            if token in text:
                hits.append(f"{path.relative_to(ROOT).as_posix()}  ({token})")
    assert not hits, "하수 수위에 물리 단위를 붙이고 있다: " + ", ".join(hits)


# --- 픽스처에서 오는 문구 ----------------------------------------------------
#
# 위 검사는 `web/src` 만 본다. 그런데 **화면에 찍히는 문장의 상당수는 픽스처에서
# 온다** - `route.limit`, `notice.*`, `reasons[].text`, `target.reason` 은 전부
# API 응답이 실어 보내는 값이고 컴포넌트는 그대로 렌더링한다. 그래서 위 검사만
# 통과시키면 금칙어가 계약을 타고 화면에 들어올 수 있다.


def rendered_strings(payload) -> list[tuple[str, str]]:
    """UI 가 실제로 렌더링할 수 있는 문자열만 모은다. (경로, 값)

    `_` 로 시작하는 키는 개발 주석이라 건너뛴다. 계약이 `patternProperties: ^_`
    로 허용하는 자리이고 어떤 컴포넌트도 읽지 않는다.
    """
    out: list[tuple[str, str]] = []

    def walk(node, trail: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.startswith("_"):
                    continue
                walk(value, f"{trail}/{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{trail}[{i}]")
        elif isinstance(node, str):
            out.append((trail, node))

    walk(payload)
    return out


def has_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


DEMO_FIXTURES = sorted(DEMO_DIR.glob("*.assess_response.json"))


def test_검사할_데모_픽스처가_있다():
    assert DEMO_FIXTURES, "contracts/fixtures/demo 에 검사할 응답이 없다"


@pytest.mark.parametrize("banned,instead", BANNED, ids=[b[0] for b in BANNED])
def test_금칙어가_픽스처_문구에도_없다(banned: str, instead: str):
    """화면으로 나가는 계약 값에도 같은 금칙어 규칙을 적용한다.

    **`112` 는 한글이 있는 문장에서만 본다.** 숫자 문자열에서 부분 일치가 나기
    때문이다 - `distance_m` 이 문자열이었다면 `1120` 이 `112` 로 걸린다. 지금은
    숫자라 안전하지만, 규칙이 우연한 자료형에 기대게 두지 않는다.
    """
    hits = []
    for path in DEMO_FIXTURES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for where, text in rendered_strings(payload):
            if banned == "112" and not has_hangul(text):
                continue
            if banned in text:
                hits.append(f"{path.name}{where}\n      {text[:100]}")

    assert not hits, (
        f"금지 표현 '{banned}' 가 화면으로 나가는 픽스처 값에 있다. 대신: {instead}\n  "
        + "\n  ".join(hits)
    )


def test_픽스처_검사가_실제로_문자열을_보고_있다():
    """`rendered_strings()` 가 조용히 빈 리스트를 내면 위 검사가 아무것도 지키지 않는다."""
    payload = json.loads(DEMO_FIXTURES[0].read_text(encoding="utf-8"))
    found = rendered_strings(payload)
    paths = {where for where, _ in found}

    assert "/route/limit" in paths, "경로 제한 문구를 수집하지 못했다"
    assert "/notice/disclaimer" in paths, "면책 문구를 수집하지 못했다"
    assert any(p.startswith("/decision/reasons[") and p.endswith("/text") for p in paths), (
        "판단 사유 문장을 수집하지 못했다"
    )
    # 개발 주석은 반드시 빠져야 한다 - 빠지지 않으면 오탐이 계속 난다.
    assert not any("_stub" in p or "_scenario" in p for p in paths)


def test_면책_문구를_컴포넌트가_지울_수_없다():
    """UI-07. App 이 notice.disclaimer 를 조건 없이 렌더링해야 한다."""
    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    assert "notice.disclaimer" in app
    # 조건부 렌더링(&&, ? :) 안에 들어가 있지 않은지 대략적으로 확인한다.
    for line in app.splitlines():
        if "notice.disclaimer" in line:
            assert "&&" not in line and "?" not in line, (
                "면책 문구가 조건부로 렌더링되고 있다: " + line.strip()
            )
