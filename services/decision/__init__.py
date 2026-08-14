"""판단 엔진 ② — 순수 결정 로직.

## 지금 구현된 것

- `enums.py` — 공용 enum 단일 출처
- `postprocess.py` — **확정된** 경로 후처리 1건 (`MOVE + NO_SAFE_ROUTE -> WAIT`)

## 아직 구현되지 않은 것 (T+3:00~6:00 구간)

행동 우선순위 1~10 판정 본체가 없다. 지금 API 가 돌려주는 행동은 픽스처에
들어 있는 값이고 이 모듈이 계산한 값이 아니다.

    1. trapped=true                                  -> EMERGENCY
    2. UNDERGROUND + hazard_signs >= 1               -> EVACUATE
    3. 범위 밖                                        -> UNAVAILABLE
    4. 공식 대피 지시                                  -> EVACUATE
    5. 같은 재생 시각의 필수 데이터 단절                  -> UNAVAILABLE
    6. ai_risk_level=HIGH + OUTDOOR                  -> EVACUATE
    7. ai_risk_level=HIGH + INDOOR                   -> WAIT
    8. ai_risk_level=HIGH + UNDERGROUND + 징후 없음    -> WAIT
    9. 강우 기준값 초과(TH-01·TH-02) 또는 품질 하향       -> WAIT
    10. 그 외                                         -> MOVE

첫 일치가 이긴다. 순서를 바꾸지 않는다 — 순서 자체가 합의 사항이다.
자기신고(1·2)와 공식 대피 지시(4)는 강우·하수·AI 데이터와 독립이므로
데이터 단절(5)이 이들을 UNAVAILABLE 로 덮지 않는다.

## 규칙

- 순수 함수만 둔다. I/O·HTTP·파일 읽기를 하지 않는다(N-04).
- `services/route` 를 import 하지 않는다.
- 미확정 정책을 임의로 확정하지 않는다. `docs/DECISIONS.md` 의 OPEN 목록 참조.
- 강우 기준값(TH-01·TH-02)이 만드는 결과는 `WAIT` 까지다. 강우량만으로
  `EVACUATE` 를 반환하지 않는다.
"""

from services.decision.enums import (
    Action,
    AiRiskLevel,
    Basis,
    HazardSign,
    Profile,
    RouteStatus,
    RouteTarget,
    ServiceRiskLevel,
    UserContext,
)
from services.decision.postprocess import ContractViolation, PostprocessResult, apply

__all__ = [
    "Action",
    "AiRiskLevel",
    "Basis",
    "ContractViolation",
    "HazardSign",
    "PostprocessResult",
    "Profile",
    "RouteStatus",
    "RouteTarget",
    "ServiceRiskLevel",
    "UserContext",
    "apply",
]
