/**
 * 공용 enum — TypeScript 쪽 단일 출처.
 *
 * 정본은 `contracts/schema/*.json` 이고 Python 쪽 사본은
 * `services/decision/enums.py` 다. 세 곳이 어긋나면
 * `tests/test_enum_sync.py` 가 실패한다.
 *
 * **새 enum 값을 이 세 곳 밖에서 만들지 않는다.**
 */

/** 행동. 화면 레이아웃은 위험 등급이 아니라 이 값으로 분기한다. */
export const ACTIONS = ['MOVE', 'WAIT', 'EVACUATE', 'EMERGENCY', 'UNAVAILABLE'] as const;
export type Action = (typeof ACTIONS)[number];

/** 최종 서비스 위험 등급 (축 1). SEVERE 는 공식 정보만 만들 수 있다. */
export const SERVICE_RISK_LEVELS = ['SAFE', 'CAUTION', 'DANGER', 'SEVERE'] as const;
export type ServiceRiskLevel = (typeof SERVICE_RISK_LEVELS)[number];

/** AI 예측 위험 등급 (축 2). service_risk_level 과 다른 축이다. */
export const AI_RISK_LEVELS = ['LOW', 'HIGH'] as const;
export type AiRiskLevel = (typeof AI_RISK_LEVELS)[number];

export const USER_CONTEXTS = ['INDOOR', 'OUTDOOR', 'UNDERGROUND'] as const;
export type UserContext = (typeof USER_CONTEXTS)[number];

/** 지하공간 현장 위험 징후. 사용자가 직접 신고하며 AI 로 추론하지 않는다. */
export const HAZARD_SIGNS = ['WATER_INFLOW', 'SEWER_BACKFLOW', 'STAIR_INFLOW'] as const;
export type HazardSign = (typeof HAZARD_SIGNS)[number];

/** MVP 지원 프로필. WHEELCHAIR·WITH_PET 은 검증 데이터 부족으로 제외한다. */
export const PROFILES = ['ELDERLY', 'WITH_CHILD'] as const;
export type Profile = (typeof PROFILES)[number];

/** 경로 상태. 행동 enum 인 UNAVAILABLE 을 쓰지 않는다 — 경로 단절은 DATA_UNAVAILABLE. */
export const ROUTE_STATUSES = [
  'VERIFIED_ROUTE',
  'FALLBACK_CANDIDATE',
  'NOT_REQUIRED',
  'NO_SAFE_POINT',
  'NO_SAFE_ROUTE',
  'DESTINATION_BLOCKED',
  'DATA_UNAVAILABLE',
] as const;
export type RouteStatus = (typeof ROUTE_STATUSES)[number];

/** 도달 대상. MOVE 는 사용자 목적지, EVACUATE 는 서비스가 고른 안전거점. */
export const ROUTE_TARGETS = ['USER_DESTINATION', 'SAFE_POINT'] as const;
export type RouteTarget = (typeof ROUTE_TARGETS)[number];

/** 근거 출처. TEAM_RULE 은 공식 기준이 아니라 우리가 정한 규칙이라는 뜻이다. */
export const BASES = ['OFFICIAL_GUIDANCE', 'AI_PREDICTION', 'TEAM_RULE'] as const;
export type Basis = (typeof BASES)[number];

// --- 화면 표시 라벨 -------------------------------------------------------
//
// 계약 값과 화면 문구를 여기서 한 번만 잇는다. 컴포넌트가 각자 문자열을
// 만들면 금칙어 검사를 빠져나가는 문구가 생긴다.

export const ACTION_LABEL: Record<Action, string> = {
  MOVE: '이동',
  WAIT: '대기',
  EVACUATE: '대피',
  EMERGENCY: '119',
  UNAVAILABLE: '정보 없음',
};

/** 색 외에 형태·기호로도 구분한다(UI-06/UI-09 흑백 판독). */
export const ACTION_MARK: Record<Action, string> = {
  MOVE: '→',
  WAIT: '■',
  EVACUATE: '▲',
  EMERGENCY: '✚',
  UNAVAILABLE: '?',
};

export const RISK_LABEL: Record<ServiceRiskLevel, string> = {
  SAFE: '안전',
  CAUTION: '주의',
  DANGER: '위험',
  SEVERE: '심각',
};

export const RISK_MARK: Record<ServiceRiskLevel, string> = {
  SAFE: '○',
  CAUTION: '◐',
  DANGER: '●',
  SEVERE: '◆',
};

export const BASIS_LABEL: Record<Basis, string> = {
  OFFICIAL_GUIDANCE: '공식',
  AI_PREDICTION: 'AI 예측',
  TEAM_RULE: '팀 기준',
};

export const ROUTE_STATUS_LABEL: Record<RouteStatus, string> = {
  VERIFIED_ROUTE: '검증 기준 충족 경로',
  FALLBACK_CANDIDATE: '추천 후보 경로',
  NOT_REQUIRED: '경로가 필요하지 않습니다',
  NO_SAFE_POINT: '조건에 맞는 대피시설을 찾지 못했습니다',
  NO_SAFE_ROUTE: '비교한 후보가 모두 제외됐습니다',
  DESTINATION_BLOCKED: '이 시각 기준 목적지가 통제·침수 구간입니다',
  DATA_UNAVAILABLE: '경로를 판단할 자료가 없습니다',
};
