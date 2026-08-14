"""계약 픽스처 일괄 검증.

    python -m contracts.validate          # 전체 검사
    python -m contracts.validate --list   # 무엇을 어떤 스키마로 검사하는지만 출력

무엇을 하는가
-------------
1. `contracts/fixtures/` 아래의 **유효** 픽스처가 해당 스키마를 통과하는지 본다.
2. `contracts/fixtures/invalid/` 아래의 픽스처가 **반드시 실패**하는지 본다.
   통과해버리면 그건 스키마가 잘못된 조합을 막지 못한다는 뜻이므로 에러다.
3. `AssessResponse` 는 합성 검증한다 - 본문을 assess_response 로 검사한 뒤
   `.risk` 를 risk_assessment 로, `.route` 를 safe_route 로 다시 검사한다.

왜 합성 검증인가
----------------
스키마 사이의 `$ref` 는 `$id` 가 상대 URI 라 해석기마다 다르게 풀린다. 계약
파일을 각각 독립적으로 열 수 있게 두는 편이 다섯 명이 동시에 만지는 상황에서
덜 깨진다. 대신 "누가 어느 블록을 소유하는가"를 여기 한곳에 적어둔다.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "contracts" / "schema"
FIXTURE_DIR = ROOT / "contracts" / "fixtures"

# AssessResponse 안에서 다른 계약이 소유하는 블록.
COMPOSED_BLOCKS = {"risk": "risk_assessment", "route": "safe_route"}


@dataclass(frozen=True)
class Case:
    path: Path
    schema: str
    expect_valid: bool
    note: str = ""

    @property
    def rel(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_schemas() -> dict[str, Draft202012Validator]:
    out: dict[str, Draft202012Validator] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        name = path.name.removesuffix(".schema.json")
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        out[name] = Draft202012Validator(schema)
    return out


def discover() -> list[Case]:
    """디렉터리 규칙으로 픽스처와 스키마를 짝짓는다.

    RF-* (모델 위험 스냅샷) 와 DS-* (통합 데모) 는 이름 공간이 다르다.
    자세한 규칙은 contracts/fixtures/README.md 참조.
    """
    cases: list[Case] = []

    # RF-*: 기존 모델 픽스처. fixtures/ 바로 아래의 risk_*.json 이다.
    for path in sorted(FIXTURE_DIR.glob("risk_*.json")):
        cases.append(Case(path, "risk_assessment", True, "RF 모델 위험 스냅샷"))

    # DS-*: 통합 데모. UI 가 실제로 받는 응답이다.
    for path in sorted((FIXTURE_DIR / "demo").glob("*.json")):
        cases.append(Case(path, "assess_response", True, "DS 통합 데모"))

    # 공식정보 픽스처.
    for path in sorted((FIXTURE_DIR / "official").glob("*.json")):
        cases.append(Case(path, "official_info", True, "공식정보"))

    # 반드시 거부되어야 하는 조합. 파일이 스스로 대상 스키마를 선언한다.
    for path in sorted((FIXTURE_DIR / "invalid").glob("*.json")):
        meta = load_json(path).get("_expect_invalid", {})
        cases.append(
            Case(path, meta.get("schema", "assess_response"), False, meta.get("why", ""))
        )

    return cases


def errors_for(validators: dict[str, Draft202012Validator], case: Case) -> list[str]:
    """이 픽스처에서 나온 계약 위반을 전부 모은다."""
    payload = load_json(case.path)
    validator = validators.get(case.schema)
    if validator is None:
        return [f"알 수 없는 스키마: {case.schema}"]

    found = [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
             for e in validator.iter_errors(payload)]

    # AssessResponse 합성 검증.
    if case.schema == "assess_response":
        for block, schema_name in COMPOSED_BLOCKS.items():
            body = payload.get(block)
            if not isinstance(body, dict):
                continue
            sub = validators[schema_name]
            found += [
                f"{block}/{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
                for e in sub.iter_errors(body)
            ]

    return found


def main(argv: list[str]) -> int:
    validators = load_schemas()
    cases = discover()

    if "--list" in argv:
        for c in cases:
            mark = "valid  " if c.expect_valid else "INVALID"
            print(f"  {mark}  {c.schema:<17}  {c.rel}   {c.note}")
        return 0

    if not cases:
        print("!! 검사할 픽스처가 없다. contracts/fixtures/ 를 확인하라.")
        return 1

    print(f"스키마 {len(validators)}개, 픽스처 {len(cases)}개")
    failures: list[str] = []

    for case in cases:
        found = errors_for(validators, case)

        if case.expect_valid and found:
            failures.append(f"{case.rel} ({case.schema})")
            print(f"  FAIL  {case.rel}")
            for msg in found[:5]:
                print(f"          {msg}")
            if len(found) > 5:
                print(f"          ... 외 {len(found) - 5}건")
        elif not case.expect_valid and not found:
            failures.append(f"{case.rel} (거부되어야 하는데 통과함)")
            print(f"  FAIL  {case.rel}  통과하면 안 되는 조합이 통과했다 - {case.note}")
        else:
            verb = "ok    " if case.expect_valid else "거부됨"
            print(f"  {verb}  {case.rel}")

    print()
    if failures:
        print(f"실패 {len(failures)}건")
        return 1
    print(f"전부 통과 ({len(cases)}건)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
