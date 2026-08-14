"""enum 이 세 곳에서 어긋나지 않는지 본다.

    contracts/schema/*.json   (정본)
    services/decision/enums.py
    web/src/contracts/enums.ts

해커톤에서 통합이 깨지는 흔한 이유가 "백엔드는 새 값을 보내는데 UI 는 모른다"이다.
그걸 런타임이 아니라 여기서 잡는다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from services.decision import enums as py

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "contracts" / "schema"
TS_ENUMS = ROOT / "web" / "src" / "contracts" / "enums.ts"


def ts_arrays() -> dict[str, list[str]]:
    """`export const NAME = ['A', 'B'] as const;` 를 뽑아낸다."""
    text = TS_ENUMS.read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    for name, body in re.findall(
        r"export const ([A-Z_]+)\s*=\s*\[(.*?)\]\s*as const", text, re.DOTALL
    ):
        out[name] = re.findall(r"'([A-Z_]+)'", body)
    return out


def schema_enum(file: str, *path: str) -> list[str]:
    node = json.loads((SCHEMA_DIR / file).read_text(encoding="utf-8"))
    for key in path:
        node = node[key]
    return node["enum"]


# (정본 위치, Python StrEnum, TypeScript 상수명)
CASES = [
    (("assess_response.schema.json", "$defs", "action"), py.Action, "ACTIONS"),
    (
        ("assess_response.schema.json", "$defs", "service_risk_level"),
        py.ServiceRiskLevel,
        "SERVICE_RISK_LEVELS",
    ),
    (("assess_response.schema.json", "$defs", "basis"), py.Basis, "BASES"),
    (("safe_route.schema.json", "$defs", "route_status"), py.RouteStatus, "ROUTE_STATUSES"),
    (("safe_route.schema.json", "$defs", "route_target"), py.RouteTarget, "ROUTE_TARGETS"),
    (("action_decision.schema.json", "$defs", "profile"), py.Profile, "PROFILES"),
    (("action_decision.schema.json", "$defs", "hazard_sign"), py.HazardSign, "HAZARD_SIGNS"),
]


@pytest.mark.parametrize("path,py_enum,ts_name", CASES, ids=[c[2] for c in CASES])
def test_스키마와_python과_typescript가_같다(path, py_enum, ts_name):
    expected = schema_enum(*path)
    assert [m.value for m in py_enum] == expected, (
        f"services/decision/enums.py 의 {py_enum.__name__} 이 스키마와 다르다"
    )
    assert ts_arrays()[ts_name] == expected, (
        f"web/src/contracts/enums.ts 의 {ts_name} 이 스키마와 다르다"
    )


def test_ai_위험등급도_세곳이_같다():
    """축 2. risk_assessment 스키마에는 null 이 함께 들어 있으므로 걸러서 비교한다."""
    node = json.loads((SCHEMA_DIR / "risk_assessment.schema.json").read_text(encoding="utf-8"))
    expected = [v for v in node["properties"]["area_risk"]["properties"]["ai_risk_level"]["enum"] if v]
    assert [m.value for m in py.AiRiskLevel] == expected
    assert ts_arrays()["AI_RISK_LEVELS"] == expected


def test_UI가_모든_행동과_위험등급에_라벨을_갖는다():
    """계약 값이 늘었는데 화면 문구가 없으면 빈 카드가 나온다."""
    text = TS_ENUMS.read_text(encoding="utf-8")
    for member in py.Action:
        assert f"{member.value}:" in text, f"ACTION_LABEL 에 {member.value} 가 없다"
    for member in py.ServiceRiskLevel:
        assert f"{member.value}:" in text, f"RISK_LABEL 에 {member.value} 가 없다"
    for member in py.RouteStatus:
        assert f"{member.value}:" in text, f"ROUTE_STATUS_LABEL 에 {member.value} 가 없다"
