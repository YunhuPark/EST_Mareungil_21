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
    # context 는 $defs 가 아니라 user_state 안에 인라인으로 박혀 있다. 그래도 3중
    # 동기화 대상이므로 여기서 함께 본다 - 빠져 있던 유일한 축이었다.
    (
        ("action_decision.schema.json", "properties", "user_state", "properties", "context"),
        py.UserContext,
        "USER_CONTEXTS",
    ),
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


# --- 스키마 사이의 중복 정의 -------------------------------------------------
#
# 위 CASES 는 각 enum 을 **한 곳에서만** 읽는다. 그런데 실제로는 같은 enum 이
# 여러 스키마에 복사돼 있다 - `basis` 는 3곳, `action`·`service_risk_level` 은
# 2곳, `profile`·`hazard_sign`·`context` 는 $defs 와 인라인에 흩어져 있다.
# 그래서 CASES 가 보지 않는 사본을 고치면 **아무것도 빨개지지 않는다.**
# 여기서 모든 사본을 훑어 정본과 대조한다.

#: 계약 enum 의 정본 값. enums.py 가 이미 스키마와 묶여 있으므로(CASES) 여기서
#: 파생시키면 정본이 두 개가 되지 않는다.
CANONICAL = {
    "action": [m.value for m in py.Action],
    "service_risk_level": [m.value for m in py.ServiceRiskLevel],
    "ai_risk_level": [m.value for m in py.AiRiskLevel],
    "user_context": [m.value for m in py.UserContext],
    "hazard_sign": [m.value for m in py.HazardSign],
    "profile": [m.value for m in py.Profile],
    "route_status": [m.value for m in py.RouteStatus],
    "route_target": [m.value for m in py.RouteTarget],
    "basis": [m.value for m in py.Basis],
    # enums.py 에 없는 계약 전용 enum. C-21 로 official 블록이 3개 스키마에
    # 복사되면서 이 값도 3곳이 됐으므로 함께 묶어둔다.
    # M-24·M-36 에서 DEMO_FIXTURE 를 더했다 - 시연용으로 만든 값을 실제 정보와
    # 구분해 표시하기 위한 것이며, 화면은 셋을 각각 다르게 쓴다.
    "verification": ["VERIFIED_SOURCE", "DRAFT_UNVERIFIED", "DEMO_FIXTURE"],
}

#: 부분집합을 선언하는 자리. `if/then` 가지는 "이 조합만 허용"을 뜻하므로
#: enum 을 다시 선언하는 것이 아니다. 여기를 정본과 비교하면 거짓 실패가 난다.
SUBSET_KEYWORDS = {"allOf", "anyOf", "oneOf", "if", "then", "else", "not"}


def full_enum_declarations() -> list[tuple[str, str, list[str]]]:
    """스키마 안의 **완전한** enum 선언을 전부 모은다. (파일, 경로, 값)"""
    found: list[tuple[str, str, list[str]]] = []

    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))

        def walk(node, trail: tuple[str, ...] = ()) -> None:
            if isinstance(node, dict):
                if isinstance(node.get("enum"), list) and not (
                    SUBSET_KEYWORDS & set(trail)
                ):
                    values = [v for v in node["enum"] if isinstance(v, str)]
                    if values:
                        found.append((path.name, "/".join(trail), values))
                for key, value in node.items():
                    walk(value, trail + (key,))
            elif isinstance(node, list):
                for i, item in enumerate(node):
                    walk(item, trail + (str(i),))

        walk(schema)

    return found


#: 경로에서 걷어낼 JSON Schema 구조 키워드. 남는 것이 "필드 이름 경로"다.
STRUCTURE_KEYS = {"properties", "items", "$defs", "patternProperties"}

#: 소비자 블록 접두. `AssessResponse.official.closures` 와 `OfficialInfo.closures` 는
#: **같은 필드**이므로 같은 이름으로 묶어야 사본 비교가 성립한다.
CONSUMER_PREFIXES = ("official",)


def field_path(trail: str) -> tuple[str, ...]:
    """`/properties/official/properties/closures/items/properties/kind` -> `('closures','kind')`.

    구조 키워드와 소비자 블록 접두를 걷어내 **필드 이름만** 남긴다. 이렇게 해야
    서로 다른 스키마에 흩어진 같은 필드를 한 그룹으로 볼 수 있다.
    """
    parts = tuple(p for p in trail.split("/") if p and p not in STRUCTURE_KEYS)
    while parts and parts[0] in CONSUMER_PREFIXES:
        parts = parts[1:]
    return parts


def test_이름이_같은_필드의_enum은_스키마마다_같아야_한다():
    """CANONICAL 목록 **밖의** enum 까지 사본 일치를 강제한다.

    이 테스트가 없을 때 실제로 무엇이 통과했는지 적어둔다 — `action_decision` 의
    `closures.kind` 에만 값을 하나 더해도 **전체 테스트가 통과했다.** 위
    `test_같은_enum의_모든_사본이...` 는 CANONICAL 과 값이 겹칠 때만 비교하므로
    `ROAD/UNDERPASS/...` 처럼 목록에 없는 enum 은 아예 보지 않았기 때문이다.

    값이 겹치는지로 묶지 않고 **필드 이름**으로 묶는 이유가 있다. `excluded_by` 와
    `hazards.kind` 는 `OFFICIAL_CLOSURE`·`CONFIRMED_FLOODING` 을 공유하지만 서로
    다른 축이라 값이 달라야 한다. 겹침으로 묶으면 그 둘이 거짓 실패한다.
    """
    groups: dict[tuple[str, ...], list[tuple[str, list[str]]]] = {}
    for file, trail, values in full_enum_declarations():
        groups.setdefault(field_path(trail), []).append((file, values))

    mismatches: list[str] = []
    for field, copies in sorted(groups.items()):
        if len(copies) < 2:
            continue
        first = set(copies[0][1])
        if any(set(values) != first for _file, values in copies[1:]):
            lines = "\n".join(f"      {f}: {sorted(v)}" for f, v in copies)
            mismatches.append(f"{'/'.join(field)}\n{lines}")

    assert not mismatches, (
        "같은 필드의 enum 이 스키마마다 다르다. 계약을 바꿀 때 사본을 전부 고쳐야 한다"
        " (CLAUDE.md 8절):\n  " + "\n  ".join(mismatches)
    )


def test_사본이_여러_곳에_있는_필드를_실제로_찾는다():
    """위 테스트가 **정말 여러 사본을 보고 있는지** 확인한다.

    `field_path()` 정규화가 잘못되면 모든 그룹이 크기 1이 되어 위 테스트가
    아무것도 검사하지 않으면서 통과한다.
    """
    groups: dict[tuple[str, ...], set[str]] = {}
    for file, trail, _values in full_enum_declarations():
        groups.setdefault(field_path(trail), set()).add(file)

    multi = {k: v for k, v in groups.items() if len(v) >= 2}
    assert ("closures", "kind") in multi, "closures.kind 사본을 두 스키마에서 찾지 못했다"
    assert ("closures", "mode") in multi, "closures.mode 사본을 두 스키마에서 찾지 못했다"
    assert ("verification",) in multi, "verification 사본을 여러 스키마에서 찾지 못했다"


#: 스키마 enum -> 화면 문구를 잇는 TypeScript 표.
#: 값이 늘었는데 표에 없으면 화면에 **코드가 그대로** 보인다.
TS_LABEL_MAPS = [
    (
        "EXCLUDED_BY_LABEL",
        ("safe_route.schema.json", "properties", "candidates", "items", "properties", "excluded_by"),
    ),
    (
        "VERIFICATION_LABEL",
        ("official_info.schema.json", "properties", "verification"),
    ),
]


def ts_record_keys(name: str) -> list[str]:
    """`export const NAME: Record<...> = { A: '...', B: '...' }` 의 키를 뽑는다."""
    text = TS_ENUMS.read_text(encoding="utf-8")
    match = re.search(rf"export const {name}[^=]*=\s*\{{(.*?)\n\}};", text, re.DOTALL)
    assert match, f"enums.ts 에 {name} 이 없다"
    return re.findall(r"^\s*([A-Z_]+):", match.group(1), re.MULTILINE)


@pytest.mark.parametrize("ts_name,schema_path", TS_LABEL_MAPS, ids=[m[0] for m in TS_LABEL_MAPS])
def test_계약에_있는_값은_화면_문구를_갖는다(ts_name: str, schema_path: tuple[str, ...]):
    """이 테스트가 없을 때 실제로 무엇이 통과했는지 적어둔다 — `VERIFICATION_LABEL`
    에서 `DEMO_FIXTURE` 를 지워도 **enum 동기화 테스트가 전부 통과했다.**
    `Record<string, string>` 은 TypeScript 도 누락을 잡지 못한다.

    `excluded_by` 는 `null` 을 포함하므로 문자열만 비교한다.
    """
    file, *path = schema_path
    expected = {v for v in schema_enum(file, *path) if isinstance(v, str)}
    missing = expected - set(ts_record_keys(ts_name))
    assert not missing, (
        f"enums.ts 의 {ts_name} 에 화면 문구가 없는 계약 값이 있다: {sorted(missing)}. "
        "그대로 두면 화면에 enum 코드가 노출된다."
    )


def test_같은_enum의_모든_사본이_스키마_사이에서_일치한다():
    """C-21 계열 회귀 방지.

    한 스키마의 사본만 고치고 나머지를 두면 통합이 조용히 깨진다. 값이 겹치는
    선언은 **정확히 같아야** 한다 - 하나라도 더하거나 빼면 여기서 잡힌다.
    """
    canonical_sets = {name: set(values) for name, values in CANONICAL.items()}
    mismatches: list[str] = []

    for file, where, values in full_enum_declarations():
        seen = set(values)
        for name, expected in canonical_sets.items():
            if not (seen & expected):
                continue
            if seen != expected:
                mismatches.append(
                    f"{file} /{where}\n"
                    f"      정본({name}): {sorted(expected)}\n"
                    f"      여기        : {sorted(seen)}"
                )

    assert not mismatches, (
        "같은 enum 의 사본이 스키마마다 다르다. 계약을 바꿀 때 사본을 전부 고쳐야 한다"
        " (CLAUDE.md 8절):\n  " + "\n  ".join(mismatches)
    )


def test_중복_정의된_enum이_실제로_여러_곳에_있다():
    """위 테스트가 **정말로 여러 사본을 보고 있는지** 확인한다.

    walk 가 조용히 아무것도 못 찾으면 위 테스트는 통과하면서 아무것도 지키지
    않는다. 최소한 basis 3곳·action 2곳은 잡혀야 한다.
    """
    declarations = full_enum_declarations()
    assert declarations, "스키마에서 enum 선언을 하나도 찾지 못했다"

    def copies(name: str) -> int:
        expected = set(CANONICAL[name])
        return sum(1 for _, _, values in declarations if set(values) == expected)

    assert copies("basis") >= 3, "basis 사본을 3곳에서 찾지 못했다"
    assert copies("action") >= 2, "action 사본을 2곳에서 찾지 못했다"
    assert copies("user_context") >= 2, "context 사본을 2곳에서 찾지 못했다"


def test_UI가_모든_행동과_위험등급에_라벨을_갖는다():
    """계약 값이 늘었는데 화면 문구가 없으면 빈 카드가 나온다."""
    text = TS_ENUMS.read_text(encoding="utf-8")
    for member in py.Action:
        assert f"{member.value}:" in text, f"ACTION_LABEL 에 {member.value} 가 없다"
    for member in py.ServiceRiskLevel:
        assert f"{member.value}:" in text, f"RISK_LABEL 에 {member.value} 가 없다"
    for member in py.RouteStatus:
        assert f"{member.value}:" in text, f"ROUTE_STATUS_LABEL 에 {member.value} 가 없다"
