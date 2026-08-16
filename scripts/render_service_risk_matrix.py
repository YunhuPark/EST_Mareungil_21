"""서비스 위험등급 × 행동 조합표를 PNG 로 그린다 (C-23 / docs/diagrams).

    python scripts/render_service_risk_matrix.py

산출물: docs/diagrams/service_risk_action_matrix.png

**등급 열은 `services/decision/service_risk.classify()` 를 실제로 호출해 채운다.**
표를 손으로 적지 않는 이유는 그림과 코드가 조용히 어긋나는 것을 막기 위해서다.
행동 열은 설계서 9장 우선순위 1~10 을 옮겨 적은 것이며 **판단 엔진 구현이
아니다** (본체는 아직 미구현 - services/decision/__init__.py 참조).

양식은 `docs/diagrams/route_status_matrix.png` 를 따른다 - 같은 팔레트·같은
카드 레이아웃이다.

실행 환경
---------
Pillow 가 필요하다. 앱 venv 에는 없으므로(11시간 계획에서 뺀 의존성) 시스템
Python 으로 돌린다. 렌더 전용이며 앱·테스트는 이 모듈을 import 하지 않는다.

저장소 루트에서 실행한다. 경로를 손으로 적지 않는다.

    # Windows (PowerShell)
    $env:PYTHONPATH = $PWD; python scripts/render_service_risk_matrix.py

    # macOS · Linux
    PYTHONPATH=$PWD python3 scripts/render_service_risk_matrix.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.decision.enums import AiRiskLevel, UserContext  # noqa: E402
from services.decision.service_risk import (  # noqa: E402
    RAIN_60M_MM,
    RiskSignals,
    classify,
)

OUT = ROOT / "docs" / "diagrams" / "service_risk_action_matrix.png"

# --- 팔레트. route_status_matrix.png 에서 그대로 뽑은 값 ----------------------

PAGE = "#F4F7FA"
CARD = "#FFFFFF"
CARD_ALT = "#F8FAFC"
HEADER = "#17324D"
ACCENT = "#177E89"
INK = "#203040"
INK_SOFT = "#5A6B7B"
LINE = "#E0E7ED"
LINE_GROUP = "#C8D4DE"
SHADOW = "#DEE6ED"

PILL = {
    "green": ("#E7F6ED", "#1B7A4B"),
    "blue": ("#E8F1FB", "#2C5F9E"),
    "gray": ("#EDF1F4", "#5A6B7B"),
    "amber": ("#FFF3D6", "#AD5B00"),
    "red": ("#FDEBEC", "#B23A48"),
    "solid": ("#B23A48", "#FFFFFF"),
}

RISK_STYLE = {"SAFE": "green", "CAUTION": "amber", "DANGER": "red", "SEVERE": "solid"}
ACTION_STYLE = {
    "MOVE": "blue",
    "WAIT": "amber",
    "EVACUATE": "red",
    "EMERGENCY": "solid",
    "UNAVAILABLE": "gray",
}

# --- 행동 근거. 설계서 9장 우선순위를 자연어로 옮긴 것 ------------------------
#
# 숫자만 적으면 표를 읽는 사람이 매번 설계서를 다시 펴야 한다.

WHY = {
    1: ("고립 신고가 모든 신호를 이긴다.", "자력 이동이 불가능하므로 즉시 구조를 요청한다."),
    2: ("지하로 물이 들어오는 중이다.", "위험도 계산에 앞서 대피를 부른다."),
    3: ("서비스 범위 밖이다.", "이 지역의 판단을 적용하지 않는다."),
    4: ("가장 권위 있는 공식 지시가 있다.", "내부 데이터가 끊겨도 이 판단은 덮이지 않는다."),
    5: ("같은 재생 시각의 필수 자료가 없다.", "모른다는 사실을 그대로 말한다."),
    6: ("실외에는 물러설 곳이 없다.", "위험이 높으면 안전거점으로 옮긴다."),
    7: ("안전한 실내가 이미 대피처다.", "무리한 이동이 오히려 더 위험하다."),
    8: ("지하지만 현장 징후는 아직 없다.", "이동 대신 상황을 지켜본다."),
    9: ("60분 누적 강우가 팀 기준값을 넘었다.", "강우만으로는 대기까지다 — 대피를 부르지 않는다."),
    91: ("자료가 30분 넘게 늦었다.", "지금 상황을 안다고 말할 수 없어 이동을 권하지 않는다."),
    10: ("걸리는 조건이 하나도 없다.", "기본값으로 이동해도 되는 상태다."),
    # 우선순위 10 이지만 사연이 다르다. AI 값이 없는데도 기본값으로 떨어지는
    # 자리이며, 등급이 CAUTION 인 것과 행동이 MOVE 인 것이 여기서 갈린다.
    101: ("AI 값이 없지만 강우 자료는 살아 있다.", "우선순위 5 에 걸리지 않아 기본값으로 떨어진다."),
}

STALE_30M = 1800  # DQ-02


def action_of(s: RiskSignals) -> tuple[str, int]:
    """설계서 9장 우선순위 1~10. 첫 일치가 이긴다. (행동, 규칙 번호)"""
    if s.trapped:
        return "EMERGENCY", 1
    if s.context is UserContext.UNDERGROUND and s.hazard_signs:
        return "EVACUATE", 2
    if not s.in_service_area:
        return "UNAVAILABLE", 3
    if s.evacuation_order:
        return "EVACUATE", 4
    if s.ai_risk_level is None and not s.rain_available:
        return "UNAVAILABLE", 5
    if s.ai_risk_level is AiRiskLevel.HIGH:
        if s.context is UserContext.OUTDOOR:
            return "EVACUATE", 6
        return ("WAIT", 7) if s.context is UserContext.INDOOR else ("WAIT", 8)
    if s.rain_past_60m_mm is not None and s.rain_past_60m_mm >= RAIN_60M_MM:
        return "WAIT", 9
    if s.data_age_sec > STALE_30M:
        return "WAIT", 91
    return "MOVE", 101 if s.ai_risk_level is None else 10


BASE = RiskSignals(
    context=UserContext.OUTDOOR,
    official_present=True,
    observed_rate=1.0,
    rain_available=True,
    rain_past_60m_mm=0.0,
    data_age_sec=0,
)

CTX = {"실내": UserContext.INDOOR, "실외": UserContext.OUTDOOR, "지하": UserContext.UNDERGROUND}
AI_COL = {
    "LOW": {"ai_risk_level": AiRiskLevel.LOW},
    "HIGH 단독": {"ai_risk_level": AiRiskLevel.HIGH},
    "HIGH + 추가신호": {"ai_risk_level": AiRiskLevel.HIGH, "rain_past_60m_mm": RAIN_60M_MM},
}


def build_rows() -> list[dict]:
    """(공식정보, AI, 위치) 조합을 돌며 등급·행동을 계산한다."""
    rows: list[dict] = []

    def add(group, official_label, ai_label, ctx_label, **change):
        ctx = CTX.get(ctx_label, UserContext.OUTDOOR)
        s = replace(BASE, context=ctx, **change)
        r = classify(s)
        act, rule = action_of(s)
        rows.append(
            {
                "group": group,
                "official": official_label,
                "ai": ai_label,
                "ctx": ctx_label,
                "risk": r.level.value,
                "action": act,
                "why": WHY[rule],
            }
        )

    # A. 부재 · 통제 · 해제 — 셋의 결과가 같아 한 묶음으로 낸다.
    for ai_label, ai_change in AI_COL.items():
        if ai_label == "LOW":
            add("A", "부재 · 통제 · 해제", ai_label, "실내 · 실외 · 지하", **ai_change)
        else:
            for ctx_label in CTX:
                add("A", "부재 · 통제 · 해제", ai_label, ctx_label, **ai_change)

    # B. 공식정보 지연 (30분 초과)
    for ai_label, ai_change in AI_COL.items():
        if ai_label == "LOW":
            add("B", "지연 (30분 초과)", ai_label, "실내 · 실외 · 지하",
                data_age_sec=STALE_30M + 1, **ai_change)
        else:
            for ctx_label in CTX:
                add("B", "지연 (30분 초과)", ai_label, ctx_label,
                    data_age_sec=STALE_30M + 1, **ai_change)

    # C. 직접 안전신호 — AI 와 무관하게 이긴다.
    add("C", "공식 대피지시", "LOW · HIGH · 산출불가", "실내 · 실외 · 지하", evacuation_order=True)
    add("C", "고립 신고", "무관", "무관", trapped=True)
    add("C", "지하 + 현장 징후", "무관", "지하", hazard_signs=("WATER_INFLOW",))

    # D. AI 산출 불가
    add("D", "AI 산출불가", "null · 강우자료 있음", "실내 · 실외 · 지하", ai_risk_level=None)
    add("D", "AI 산출불가", "null · 강우자료 없음", "실내 · 실외 · 지하",
        ai_risk_level=None, rain_available=False)

    return rows


# --- 그리기 ------------------------------------------------------------------

S = 2  # 2배 해상도. route_status_matrix.png 와 같다.

#: 한글 글꼴 후보. (일반, 굵게) 순서이며 **플랫폼별로 이름이 다르다.**
#: 예전에는 `C:\Windows\Fonts` 를 박아서 macOS 에서 이 스크립트가 죽었다.
#: 그림은 코드를 실제로 호출해 표를 채우므로(CLAUDE.md 10절) 렌더가 안 되면
#: 문서와 코드가 조용히 어긋난다 — 글꼴 하나 때문에 그렇게 되지 않도록 한다.
FONT_CANDIDATES = [
    # Windows
    (Path(r"C:\Windows\Fonts") / "malgun.ttf", Path(r"C:\Windows\Fonts") / "malgunbd.ttf"),  # portability-ok: OS 표준 글꼴 경로를 나열하는 것이 이 목록의 목적이다
    # macOS — AppleSDGothicNeo 는 하나의 파일에 굵기가 들어 있다.
    (Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),) * 2,
    (Path("/Library/Fonts/AppleGothic.ttf"),) * 2,
    # Linux (Noto CJK)
    (
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    ),
]


def _font_pair() -> tuple[Path, Path]:
    for regular, bold in FONT_CANDIDATES:
        if regular.exists() and bold.exists():
            return regular, bold
    tried = "\n  ".join(str(r) for r, _ in FONT_CANDIDATES)
    raise SystemExit(
        "한글 글꼴을 찾지 못했다. 아래를 확인했다:\n  " + tried + "\n"
        "다른 경로에 있으면 FONT_CANDIDATES 에 추가한다."
    )


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    regular, bold_path = _font_pair()
    return ImageFont.truetype(str(bold_path if bold else regular), size * S)


COLS = [
    ("공식정보", 210, "left"),
    ("AI 위험", 190, "left"),
    ("위치", 130, "left"),
    ("service_risk_level", 160, "center"),
    ("action", 150, "center"),
    ("행동 근거 (설계서 9장 우선순위)", 420, "left"),
]

PAD = 18
ROW_H = 64
HEAD_H = 62
CARD_X = 60
TITLE_H = 150


def text_w(draw, s, f) -> int:
    return draw.textbbox((0, 0), s, font=f)[2]


def pill(draw, x, y, label, style, f, *, center_in=None):
    bg, fg = PILL[style]
    tw = text_w(draw, label, f)
    w, h = tw + 22 * S, 32 * S
    px = x + (center_in - w) // 2 if center_in else x
    draw.rounded_rectangle([px, y, px + w, y + h], radius=8 * S, fill=bg)
    draw.text((px + 11 * S, y + h // 2), label, font=f, fill=fg, anchor="lm")


def render() -> Path:
    rows = build_rows()

    card_w = sum(c[1] for c in COLS)
    img_w = (card_w + 2 * CARD_X) * S
    img_h = (TITLE_H + HEAD_H + ROW_H * len(rows) + 70) * S

    img = Image.new("RGB", (img_w, img_h), PAGE)
    d = ImageDraw.Draw(img)

    f_title = font(26, True)
    f_sub = font(11)
    f_head = font(11, True)
    f_cell = font(11)
    f_cell_b = font(11, True)
    f_pill = font(10, True)
    f_why = font(10)

    # 제목
    d.text((CARD_X * S, 40 * S), "서비스 위험등급과 행동 조합표", font=f_title, fill=HEADER)
    d.text(
        (CARD_X * S, 84 * S),
        "공식정보 상태 × AI 위험 × 사용자 위치  ·  등급과 행동은 1:1 이 아니다 (C-23)",
        font=f_sub,
        fill=INK_SOFT,
    )
    d.rectangle([CARD_X * S, 112 * S, (CARD_X + 60) * S, 115 * S], fill=ACCENT)

    top = TITLE_H * S
    left = CARD_X * S
    right = left + card_w * S
    bottom = top + (HEAD_H + ROW_H * len(rows)) * S

    # 카드 그림자와 바닥
    d.rectangle([left + 3 * S, top + 4 * S, right + 3 * S, bottom + 4 * S], fill=SHADOW)
    d.rectangle([left, top, right, bottom], fill=CARD)

    # 헤더 바
    d.rectangle([left, top, right, top + HEAD_H * S], fill=HEADER)
    x = left
    for title, w, align in COLS:
        cx = x + (w * S) // 2 if align == "center" else x + PAD * S
        d.text(
            (cx, top + (HEAD_H * S) // 2),
            title,
            font=f_head,
            fill="#FFFFFF",
            anchor="mm" if align == "center" else "lm",
        )
        x += w * S

    # 본문
    y = top + HEAD_H * S
    for i, row in enumerate(rows):
        prev = rows[i - 1] if i else None
        new_group = prev is None or row["group"] != prev["group"]
        same_official = prev is not None and not new_group and row["official"] == prev["official"]

        if i % 2:
            d.rectangle([left, y, right, y + ROW_H * S], fill=CARD_ALT)

        if new_group and i:
            d.rectangle([left, y - 2 * S, right, y], fill=LINE_GROUP)
        elif i:
            d.rectangle([left, y - 1 * S, right, y], fill=LINE)

        mid = y + (ROW_H * S) // 2
        x = left

        # 공식정보 — 같은 값이 이어지면 첫 줄에만 쓴다(병합처럼 보이게).
        if not same_official:
            emphasize = row["group"] == "C"
            d.text(
                (x + PAD * S, mid),
                row["official"],
                font=f_cell_b if emphasize else f_cell,
                fill=HEADER if emphasize else INK,
                anchor="lm",
            )
        x += COLS[0][1] * S

        d.text((x + PAD * S, mid), row["ai"], font=f_cell, fill=INK, anchor="lm")
        x += COLS[1][1] * S

        d.text((x + PAD * S, mid), row["ctx"], font=f_cell, fill=INK, anchor="lm")
        x += COLS[2][1] * S

        pill(d, x, mid - 16 * S, row["risk"], RISK_STYLE[row["risk"]], f_pill,
             center_in=COLS[3][1] * S)
        x += COLS[3][1] * S

        pill(d, x, mid - 16 * S, row["action"], ACTION_STYLE[row["action"]], f_pill,
             center_in=COLS[4][1] * S)
        x += COLS[4][1] * S

        head, tail = row["why"]
        d.text((x + PAD * S, mid - 11 * S), head, font=f_why, fill=INK, anchor="lm")
        d.text((x + PAD * S, mid + 11 * S), tail, font=f_why, fill=INK_SOFT, anchor="lm")

        y += ROW_H * S

    # 꼬리말
    d.text(
        (left, bottom + 24 * S),
        "등급은 services/decision/service_risk.py 의 classify() 를 실제로 호출해 채웠다. "
        "행동은 설계서 9장 우선순위를 적용한 값이며 판단 엔진은 아직 미구현이다.  "
        "교육·시연용이며 공식 재난안전 판단 도구가 아니다.",
        font=f_sub,
        fill=INK_SOFT,
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    return OUT


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    path = render()
    print(f"저장: {path}  ({Image.open(path).size[0]}x{Image.open(path).size[1]})")
