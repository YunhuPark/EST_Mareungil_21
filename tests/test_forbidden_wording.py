"""사용자 화면 금칙어 검사 (설계서 16장, RT-03, F-15, AI-01, AI-08).

`web/src/` 전체를 본다 — 주석도 포함한다. 주석만 예외로 두면 "주석이니까
괜찮다"가 슬금슬금 문구로 넘어온다. 금지된 표현은 아예 쓰지 않고, 왜 쓰면
안 되는지는 이 파일과 CLAUDE.md 에만 적는다.

발표 자료와 문서는 이 검사 대상이 아니다. 여기서 막는 것은 **사용자 화면**이다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "web" / "src"

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
