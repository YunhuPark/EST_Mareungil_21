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

/**
 * 최종 서비스 위험 등급 (축 1).
 *
 * SEVERE 는 직접 안전신호 — 공식 대피 지시 / 고립 신고 / 지하 + 현장 위험 징후 —
 * 가 있을 때만 나온다. AI 예측은 SEVERE 를 만들 수 없다 (C-23).
 * `action` 과 1:1 이 아니다. 같은 등급에 여러 행동이 온다.
 */
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
  NO_SAFE_POINT: '안내할 수 있는 안전거점이 없습니다',
  NO_SAFE_ROUTE: '비교한 후보가 모두 제외됐습니다',
  DESTINATION_BLOCKED: '이 시각 기준 목적지가 통제·침수 구간입니다',
  DATA_UNAVAILABLE: '경로를 판단할 자료가 없습니다',
};

/**
 * M-16 / M-15. 상태마다 **다른 문장**을 준다.
 *
 * 목적지 차단과 안내 가능한 경로 없음을 같은 문구로 처리하면 사용자가
 * "다른 목적지를 고르면 되는 상황"과 "움직이지 말아야 하는 상황"을 구분하지
 * 못한다. 회의 확정문을 그대로 옮겼고 임의로 바꾸지 않는다.
 */
export const ROUTE_ADVICE: Partial<Record<RouteStatus, string>> = {
  DESTINATION_BLOCKED: '현재 목적지는 이용할 수 없습니다. 다른 목적지를 선택해 주세요.',
  NO_SAFE_ROUTE: '안전이 확인되지 않은 경로로 이동하지 마세요.',
  NO_SAFE_POINT: '안내할 수 있는 안전거점이 없습니다. 119에 상황을 알리세요.',
  DATA_UNAVAILABLE: '경로를 판단할 자료가 없어 경로 안내를 제공하지 않습니다.',
};

/** M-16. `NO_SAFE_ROUTE` 에 덧붙이는 두 번째 줄. */
export const NO_SAFE_ROUTE_EXTRA =
  '현재 위치가 위험하다면 주변에서 위험 노출을 줄일 수 있는 장소를 먼저 확인하세요.';

/** M-23. 대피시설 카드에 항상 붙는 문구. '안전 보장'이라고 쓰지 않는다. */
export const SHELTER_NOTE = '개방·안전 확인 필요';

/**
 * M-32. 후보가 왜 빠졌는지. 값은 `safe_route` 스키마의 `excluded_by` 다.
 *
 * 이 표에 없는 값이 오면 문구 없이 코드가 그대로 보이므로, 스키마에 값을
 * 더할 때 여기도 함께 채운다.
 */
export const EXCLUDED_BY_LABEL: Record<string, string> = {
  OFFICIAL_CLOSURE: '공식 통제 구간',
  CONFIRMED_FLOODING: '확인된 침수 구간',
  PROFILE_CONSTRAINT: '선택한 이동 조건에 맞지 않음',
  OUT_OF_SCOPE: '재생 범위 밖',
  SHELTER_FULL: '대피시설 만석 확인',
  SHELTER_CLOSED: '대피시설 폐쇄 확인',
  SHELTER_INACCESSIBLE: '대피시설 접근 불가 확인',
};

/**
 * M-24 / M-36. 공식정보를 어떻게 받아들여야 하는지.
 *
 * DEMO_FIXTURE 는 **실제 정보가 아니다.** DRAFT_UNVERIFIED 와 구분해서
 * 표시한다 — '아직 확인 못 한 실제 정보'와 '지어낸 값'은 다른 상태다.
 */
export const VERIFICATION_LABEL: Record<string, string> = {
  VERIFIED_SOURCE: '원출처 확인됨',
  DRAFT_UNVERIFIED: '원출처 미확인 초안',
  DEMO_FIXTURE: '시연용으로 만든 값 (실제 정보 아님)',
};

/** 공식 통제 대상. */
export const CLOSURE_KIND_LABEL: Record<string, string> = {
  ROAD: '도로',
  UNDERPASS: '지하차도',
  RIVERSIDE: '하천변',
  SUBWAY: '지하철',
};

/**
 * 통제 범위. RT-11 / 설계서 10.3.
 *
 * **`VEHICLE` 을 보행 차단으로 승격하지 않는다.** 차량이 못 지나간다는 것과
 * 사람이 못 지나간다는 것은 다른 사실이고, 2022-08-08 자료는 보행 통제 여부를
 * 거의 남기지 않았다. 화면 문구가 그 차이를 그대로 말해야 한다.
 */
export const CLOSURE_MODE_LABEL: Record<string, string> = {
  VEHICLE: '차량 통제 (보행 통제 여부는 확인되지 않음)',
  PEDESTRIAN: '보행 통제',
  BOTH: '차량·보행 통제',
};

/** 프로필 선택지 문구 (M-37). */
export const PROFILE_LABEL: Record<string, string> = {
  ELDERLY: '고령자',
  WITH_CHILD: '아이 동반',
};
