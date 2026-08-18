"""기존 픽스처의 `area_risk` 블록과 센서별 판정만 다시 계산한다. **모델을 다시 학습하지 않는다.**

    python scripts/refresh_area_risk.py            # 미리보기
    python scripts/refresh_area_risk.py --write    # 실제로 저장

왜 별도 스크립트인가
--------------------
`build_demo_fixtures.py` 는 모델을 **재학습**한다. 지역 집계 규칙(TH-04)만 바꿨는데
재학습을 돌리면 센서별 확률까지 다시 만들어지고, 그건 픽스처 README 가 "실제 모델
출력"이라고 보증한 값이다. 집계 규칙은 그 확률을 **입력으로 받는 후처리**이므로
확률을 건드리지 않고 다시 계산하는 것이 맞다.

두 경로 모두 `mareungil/area_risk.py` 의 같은 함수를 쓴다.
`tests/test_area_risk.py` 가 픽스처와 규칙이 어긋나지 않는지 계속 확인한다.

센서별 `in_area_scope` · `exceeds_sensor_threshold` 도 여기서 찍는다(`annotate()`).
`area_risk` 비율을 만든 판정과 **같은 호출에서** 나와야 지도의 점 개수와
`basis` 의 "n/m" 이 어긋나지 않는다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from mareungil import area_risk

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "contracts" / "fixtures"

GRADE_NOTE = (
    "area_risk.ai_risk_level 은 LOW/HIGH 두 값뿐이며 TH-04(O-01) 규칙으로 여기서 매긴다. "
    "②(의사결정)는 이 값을 그대로 받아 쓰고 확률에 임계를 다시 적용하지 않는다. "
    "최종 서비스 등급(SAFE/CAUTION/DANGER/SEVERE)은 별개 축이며 ②가 정한다."
)


def targets() -> list[tuple[Path, list[str]]]:
    """(파일, `RiskAssessment` 본문까지의 경로) 목록."""
    found: list[tuple[Path, list[str]]] = [
        (path, []) for path in sorted(FIXTURES.glob("risk_*.json"))
    ]
    found += [(path, ["risk"]) for path in sorted((FIXTURES / "demo").glob("*.json"))]
    return found


def dig(payload: dict, path: list[str]) -> dict:
    for key in path:
        payload = payload[key]
    return payload


def main(argv: list[str]) -> int:
    write = "--write" in argv
    scope = area_risk.load_scope()
    print(f"경로 범위: {scope['label']} 반경 {int(scope['radius_m'])}m "
          f"({scope['lat']}, {scope['lon']})")
    print(f"센서 임계 {area_risk.SENSOR_THRESHOLD} · 지역 임계 {area_risk.AREA_THRESHOLD}\n")

    changed = 0
    for path, inner in targets():
        payload = json.loads(path.read_text(encoding="utf-8"))
        body = dig(payload, inner)
        sensors = body.get("sensors")
        if sensors is None:
            continue

        before = body.get("area_risk", {})
        after = area_risk.compute(sensors, scope)

        # 센서별 판정도 같은 호출에서 찍는다. 지도가 임계를 다시 적용하지 않게
        # 하려면(CLAUDE.md 10절) 비율을 만든 그 판정이 응답에 실려야 한다.
        body["sensors"] = area_risk.annotate(sensors, scope)
        # basis 의 "n/m" 과 같은 수를 센다. 두 조건을 함께 봐야 한다 -
        # 범위 안이면서 확률이 없는 센서는 분모에 들어가지 않는다.
        judged = [x for x in body["sensors"]
                  if x["in_area_scope"] and x["exceeds_sensor_threshold"] is not None]
        over = sum(1 for x in judged if x["exceeds_sensor_threshold"])

        # O-01 이 닫혔으므로 미확정 표시를 뗀다.
        for stale in ("_open_th04", "_open"):
            after.pop(stale, None)
            before.pop(stale, None)

        body["area_risk"] = after
        if "_note" in body:
            body["_note"] = GRADE_NOTE
        model = body.get("model")
        if isinstance(model, dict) and "threshold" in model:
            model["threshold_version"] = (
                f"sensor-{model['threshold']}+area-{area_risk.AREA_THRESHOLD}"
            )

        rel = path.relative_to(ROOT).as_posix()
        print(f"  {rel}")
        print(f"      전: score={before.get('score')!r} basis={before.get('basis')!r}")
        print(f"      후: risk_probability={after['risk_probability']!r} "
              f"ai_risk_level={after['ai_risk_level']!r}")
        print(f"      센서: 전체 {len(sensors)}개 중 범위 안 판정 {len(judged)}개, "
              f"임계 초과 {over}개 -> {over}/{len(judged)}")

        if write:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        changed += 1

    print(f"\n{'저장함' if write else '미리보기'} — 대상 {changed}건")
    if not write:
        print("실제로 쓰려면 --write 를 붙인다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
