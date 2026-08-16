"""판단 엔진 ② — 순수 결정 로직.

## 지금 구현된 것

- `enums.py` — 공용 enum 단일 출처
- `service_risk.py` — **축 1** `service_risk_level` 판정 (C-23)
- `official.py` — 공식정보 가시성 필터 (M-36). 재생 시각에 **당시 알 수 있었던 것만** 남긴다
- `postprocess.py` — 경로 후처리. **행동이 바뀌는 규칙 1건**
  (`MOVE + NO_SAFE_ROUTE -> WAIT`) + **행동을 유지하고 사유만 붙이는 규칙 5건**(M-15·M-16)

## 두 축은 각각 산출한다

`service_risk_level` 과 `action` 을 1:1 로 잇지 않는다. 같은 입력에서 각각
계산하며, 같은 `DANGER` 라도 안전한 실내면 `WAIT` 이고 실외면 `EVACUATE` 다.
등급을 행동의 중간값으로 두면 그 차이를 등급 안에 숨겨야 한다.

    service_risk.classify()  -> service_risk_level   (지금 얼마나 위험한가)
    아래 우선순위 1~10       -> action               (지금 무엇을 해야 하는가)

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
from services.decision.official import VisibilityResult, visible_at
from services.decision.postprocess import ContractViolation, PostprocessResult, apply
from services.decision.service_risk import (
    DataState,
    Reason,
    RiskSignals,
    ServiceRiskResult,
    classify,
)

__all__ = [
    "Action",
    "AiRiskLevel",
    "Basis",
    "ContractViolation",
    "DataState",
    "HazardSign",
    "PostprocessResult",
    "Profile",
    "Reason",
    "RiskSignals",
    "RouteStatus",
    "RouteTarget",
    "ServiceRiskLevel",
    "ServiceRiskResult",
    "UserContext",
    "VisibilityResult",
    "apply",
    "classify",
    "visible_at",
]
