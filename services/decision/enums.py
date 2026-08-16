"""공용 enum — Python 쪽 단일 출처.

정본은 `contracts/schema/*.json` 이다. 이 파일은 그 사본이고,
`web/src/contracts/enums.ts` 가 TypeScript 쪽 사본이다.

세 곳이 어긋나면 `tests/test_enum_sync.py` 가 실패한다.
**새 enum 값을 이 세 곳 밖에서 만들지 않는다.**
"""

from __future__ import annotations

from enum import StrEnum


class Action(StrEnum):
    """행동. 화면 레이아웃은 위험 등급이 아니라 이 값으로 분기한다."""

    MOVE = "MOVE"
    WAIT = "WAIT"
    EVACUATE = "EVACUATE"
    EMERGENCY = "EMERGENCY"
    UNAVAILABLE = "UNAVAILABLE"


class ServiceRiskLevel(StrEnum):
    """최종 서비스 위험 등급 (축 1).

    `AiRiskLevel` 과 다른 축이다. 판정은 `service_risk.classify()` 가 한다(C-23).
    SEVERE 는 직접 안전신호 - 공식 대피 지시 / 고립 신고 / 지하 + 현장 위험 징후 -
    가 있을 때만 나오며 **AI 는 만들 수 없다.**
    """

    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DANGER = "DANGER"
    SEVERE = "SEVERE"


class AiRiskLevel(StrEnum):
    """AI 예측 위험 등급 (축 2). 팀 합의 임계값을 적용한 이진 예측값."""

    LOW = "LOW"
    HIGH = "HIGH"


class UserContext(StrEnum):
    INDOOR = "INDOOR"
    OUTDOOR = "OUTDOOR"
    UNDERGROUND = "UNDERGROUND"


class HazardSign(StrEnum):
    """지하공간 현장 위험 징후. 사용자가 직접 신고하며 AI 로 추론하지 않는다."""

    WATER_INFLOW = "WATER_INFLOW"
    SEWER_BACKFLOW = "SEWER_BACKFLOW"
    STAIR_INFLOW = "STAIR_INFLOW"


class Profile(StrEnum):
    """MVP 지원 프로필. WHEELCHAIR·WITH_PET 은 검증 데이터 부족으로 제외한다."""

    ELDERLY = "ELDERLY"
    WITH_CHILD = "WITH_CHILD"


class RouteStatus(StrEnum):
    """경로 상태. 행동 enum 인 UNAVAILABLE 을 쓰지 않는다 - 경로 단절은 DATA_UNAVAILABLE."""

    VERIFIED_ROUTE = "VERIFIED_ROUTE"
    FALLBACK_CANDIDATE = "FALLBACK_CANDIDATE"
    NOT_REQUIRED = "NOT_REQUIRED"
    NO_SAFE_POINT = "NO_SAFE_POINT"
    NO_SAFE_ROUTE = "NO_SAFE_ROUTE"
    DESTINATION_BLOCKED = "DESTINATION_BLOCKED"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class RouteTarget(StrEnum):
    """도달 대상. MOVE 는 사용자 목적지, EVACUATE 는 서비스가 고른 안전거점."""

    USER_DESTINATION = "USER_DESTINATION"
    SAFE_POINT = "SAFE_POINT"


class Basis(StrEnum):
    """근거 출처. TEAM_RULE 은 공식 기준이 아니라 우리가 정한 규칙이라는 뜻이다."""

    OFFICIAL_GUIDANCE = "OFFICIAL_GUIDANCE"
    AI_PREDICTION = "AI_PREDICTION"
    TEAM_RULE = "TEAM_RULE"


# 행동별 경로 필요 여부. MOVE·EVACUATE 는 목적지가 필수 입력이므로 항상 true 다.
NEEDS_ROUTE = {Action.MOVE, Action.EVACUATE}

# 각 경로 상태가 나올 수 있는 1차 행동. 반대 조합은 계약 검증 실패다(RT-13).
STATUS_ALLOWED_FOR = {
    RouteStatus.VERIFIED_ROUTE: {Action.MOVE, Action.EVACUATE},
    RouteStatus.FALLBACK_CANDIDATE: {Action.MOVE, Action.EVACUATE},
    RouteStatus.NO_SAFE_ROUTE: {Action.MOVE, Action.EVACUATE},
    RouteStatus.DATA_UNAVAILABLE: {Action.MOVE, Action.EVACUATE},
    RouteStatus.NO_SAFE_POINT: {Action.EVACUATE},
    RouteStatus.DESTINATION_BLOCKED: {Action.MOVE},
    RouteStatus.NOT_REQUIRED: {Action.WAIT, Action.EMERGENCY, Action.UNAVAILABLE},
}
