/**
 * `AssessResponse` 의 TypeScript 타입.
 *
 * 정본은 `contracts/schema/assess_response.schema.json` 이다. 스키마를 바꾸면
 * 이 파일도 같은 커밋에서 고친다(CLAUDE.md 8절).
 */

import type {
  Action,
  AiRiskLevel,
  Basis,
  HazardSign,
  Profile,
  RouteStatus,
  RouteTarget,
  SensorLocationQuality,
  ServiceRiskLevel,
  UserContext,
} from './enums';

// 컴포넌트가 계약 타입을 한 곳에서만 가져오게 다시 내보낸다.
export type {
  Action,
  AiRiskLevel,
  Basis,
  HazardSign,
  Profile,
  RouteStatus,
  RouteTarget,
  SensorLocationQuality,
  ServiceRiskLevel,
  UserContext,
};

/**
 * F-12 / M-08. 시각은 전부 여기서 온다. 화면은 `Date.now()` 를 쓰지 않는다.
 *
 * 네 시각은 **항상 존재하지만 `null` 일 수 있다.** 확인되지 않은 시각을 지어내지
 * 않으면서(M-36) "확인되지 않음"을 표시할 자리는 남겨두기 위해서다.
 */
export interface Clock {
  mode: 'REPLAY';
  /** 재생 중인 과거 시각. 화면의 '지금'이다. */
  event_time: string;
  /** 판단에 쓴 마지막 관측이 측정된 시각. */
  observed_at: string | null;
  /** 모델이 이 예측을 만든 시각. */
  forecast_issued_at: string | null;
  /** 예측이 겨냥한 미래 시각. M-03: 그 시각의 점 예측이다. */
  forecast_target_at: string | null;
  /** 시스템이 자료를 마지막으로 받은 시각. 관측시각과 다를 수 있다. */
  last_update_at: string | null;
  /** 데이터 경과시간(초). */
  data_age_sec: number;
  /** 10분 초과. 지연 라벨만 띄우고 행동은 바꾸지 않는다. */
  stale: boolean;
  /** 30분 초과. 판단 근거에서 제외한다. 그렇다고 무조건 WAIT 은 아니다(M-08). */
  expired: boolean;
  /** 화면에 그대로 찍는 문자열. 재조립하지 않는다. */
  label: string;
}

export interface UserLocation {
  label: string;
  in_service_area: boolean;
  lat?: number | null;
  lon?: number | null;
}

/** RT-14. 경로 범위 내 지정 지점 목록에서 고른 1개. */
export interface DestinationPoint {
  id: string;
  label: string;
  lat: number;
  lon: number;
}

export interface AreaRisk {
  district: string | null;
  /** @deprecated risk_probability 의 예전 이름. 새 코드는 risk_probability 를 읽는다. */
  score: number | null;
  risk_probability?: number | null;
  ai_risk_level?: AiRiskLevel | null;
  basis: string;
}

export interface SensorReading {
  id: string;
  district: string;
  horizons: Record<'10' | '30' | '60', { high_level_p: number }>;
  is_high_now: boolean;
  predicted_transition: 'RISE' | 'FALL' | 'STABLE';
  /** 단위 미확인. 화면에 m·cm 를 붙이지 않는다(AI-07). */
  predicted_level_unit: 'UNCONFIRMED';
  physical_fill_ratio: null;
  location: { lat: number | null; lon: number | null; quality: SensorLocationQuality };
  /**
   * 경로 범위(강남역 반경 1km) 안인가. **서버가 정한다** — 화면은 거리를 다시
   * 계산하지 않는다. 좌표가 없으면 `false` 이므로 위치를 모르는 센서는 지도에
   * 올라오지 않는다.
   */
  in_area_scope: boolean;
  /**
   * t+30 고수위 확률이 임계 이상인가. `area_risk` 비율의 분자를 정한 그 판정을
   * 그대로 받는다 — 화면은 임계를 다시 적용하지 않는다(CLAUDE.md 10절).
   *
   * 확률이 없으면 `null` 이다. **`false` 로 읽지 않는다** — '임계 미만'과
   * '판단할 값이 없다'는 다른 상태이고, 화면도 둘을 다르게 그린다.
   */
  exceeds_sensor_threshold: boolean | null;
}

export interface RiskAssessment {
  asof: string;
  primary_horizon: 10 | 30 | 60;
  sensors: SensorReading[];
  area_risk: AreaRisk;
  model: { name: string; version: string; threshold: number; threshold_basis: string };
  /** 데이터 품질의 정본. DQ-01~05 판정이 읽는 값이며 최상위에 복사본을 두지 않는다. */
  data_quality: {
    sensors_active: number;
    /**
     * 센서별 샘플링 충족도 `min(sample_count/10, 1)` 의 평균이며 **이진 판정이 아니다** (C-28).
     * DQ-03 은 이 값이 0.70 미만이면 품질 저하로 본다.
     *
     * UI 는 이 값으로 판정하지 않는다 — 등급·행동은 API 응답을 그대로 쓴다(CLAUDE.md 10절).
     */
    observed_rate: number;
    rain_available: boolean;
    reason?: string | null;
  };
}

/** F-03. 최대 3개. 각 이유에 basis 가 붙는다. */
export interface Reason {
  code: string;
  text: string;
  value?: number | string | null;
  threshold?: number | string | null;
  basis: Basis;
}

export interface UserState {
  context: UserContext;
  trapped: boolean;
  hazard_signs: HazardSign[];
  profiles: Profile[];
  /** F-19. 필수. null 은 계약 위반이다. */
  destination: DestinationPoint;
}

export interface Decision {
  /** 경로 후처리 이전의 1차 행동. 경로 도달 대상은 이 값으로 정해진다. */
  primary_action: Action;
  /** 화면에 표시하는 최종 행동. */
  action: Action;
  route_postprocess_applied?: boolean;
  /**
   * 축 1. ai_risk_level 과 다른 필드다. 레이아웃 분기에 쓰지 않는다 — 분기는 action.
   *
   * action 과 1:1 로 잇지 않는다 (C-23). 같은 DANGER 라도 실내면 WAIT,
   * 실외면 EVACUATE 다. UI 는 두 값을 따로 받아 그대로 표시한다.
   */
  service_risk_level: ServiceRiskLevel;
  needs_route: boolean;
  next_check_at?: string | null;
  reason_code?: string | null;
  /**
   * 직전 재생 시각의 최종 행동. 행동 전환 배너용이며 없으면 배너를 띄우지 않는다.
   * UI 가 이전 응답을 기억해 스스로 만들지 않는다 - 재생 시각을 건너뛸 수 있다.
   */
  previous_action?: Action | null;
  /** 행동이 바뀐 재생 시각. previous_action 과 함께 쓴다. */
  changed_at?: string | null;
  user_state: UserState;
  reasons: Reason[];
  policy_version: string;
}

export interface RouteCandidate {
  route_id: string;
  label: string;
  rank: number;
  /** 후보 사이의 상대값이다. 절대 침수 확률이 아니므로 확률로 표시하지 않는다. */
  relative_risk: number | null;
  distance_m?: number | null;
  excluded?: boolean;
  excluded_by?: string | null;
}

export interface RouteHazard {
  kind: 'OFFICIAL_CLOSURE' | 'CONFIRMED_FLOODING' | 'PREDICTED_HIGH_LEVEL' | 'PROFILE_CONSTRAINT';
  text: string;
  geom_ref?: string | null;
  basis: Basis;
}

export interface SafeRoute {
  status: RouteStatus;
  /** RT-02. 현재 기본 방식에서는 항상 false 다. */
  route_verified: boolean;
  route_target: RouteTarget | null;
  target: {
    kind: 'DESTINATION_POINT' | 'SHELTER';
    id: string;
    label: string;
    lat: number;
    lon: number;
    reason?: string | null;
    data_asof?: string | null;
  } | null;
  route_attempted: boolean;
  /** RT-09b. route_attempted=true 일 때만 true 가 될 수 있다. */
  no_safe_route: boolean | null;
  distance_m?: number | null;
  eta_sec?: number | null;
  detour_ratio?: number | null;
  candidates?: RouteCandidate[];
  hazards?: RouteHazard[];
  profile_applied?: Profile[];
  /** RT-02. 항상 노출하는 제한 문구. */
  limit: string;
  source?: string;
  _stub?: string;
}

/**
 * 공식정보 항목 (`official_info@v1`).
 *
 * **M-36. 여기 실려 오는 것은 재생 시각에 이미 공개돼 있던 항목뿐이다.** 필터는
 * 서버(`services/decision/official.py`)가 걸며 UI 는 다시 거르지 않는다 —
 * 두 곳에서 시각을 판정하면 화면과 판단이 어긋난다.
 */
export interface OfficialAlert {
  type: string;
  /** 실제 발령시각. 공개시각(available_time)과 다른 축이다. */
  issued_at: string;
  /** F-14. 해제됐다는 사실만으로 위험 표시를 낮추지 않는다. */
  cleared_at?: string | null;
  available_time?: string | null;
  region?: string | null;
  source?: string | null;
}

export interface OfficialClosure {
  kind: 'ROAD' | 'UNDERPASS' | 'RIVERSIDE' | 'SUBWAY';
  geom_ref: string;
  label?: string | null;
  /** RT-11. VEHICLE 을 보행 차단으로 승격하지 않는다. */
  mode: 'VEHICLE' | 'PEDESTRIAN' | 'BOTH';
  since?: string | null;
  until?: string | null;
  available_time?: string | null;
  /** O-07. 목적지 차단의 유일한 근거다. 좌표 거리로 추정하지 않는다. */
  blocks_destination_ids?: string[];
}

export interface ConfirmedFlooding {
  geom_ref: string;
  label?: string | null;
  /** null 은 '관측 분 시각을 확인하지 못했다'는 뜻이다. 지어내지 않는다(M-36). */
  observed_at: string | null;
  available_time?: string | null;
  source?: string | null;
  blocks_destination_ids?: string[];
}

export interface AssessResponse {
  contract_version: string;
  /** FIXTURE 인 동안은 모델이 지금 계산한 결과가 아니다. */
  source_kind?: 'FIXTURE' | 'STUB' | 'LIVE_PIPELINE';
  clock: Clock;
  location: UserLocation;
  risk: RiskAssessment;
  decision: Decision;
  route: SafeRoute;
  /**
   * C-21. `official_info@v1` 픽스처를 그대로 받는 블록이다. 필드를 골라 담지 않는다 —
   * 골라 담으면 계약이 무엇을 거부하는지 화면 쪽에서 알 수 없게 된다.
   */
  official?: {
    evacuation_order: boolean;
    alerts: OfficialAlert[];
    closures: OfficialClosure[];
    confirmed_flooding?: ConfirmedFlooding[];
    /** 공식정보 스냅샷 시각. 화면 시각은 clock.label 이 담당하므로 직접 찍지 않는다. */
    asof?: string;
    /**
     * DRAFT_UNVERIFIED 는 원출처 미확인 초안, DEMO_FIXTURE 는 시연용으로 만든
     * 값이다(M-24·M-36). VERIFIED_SOURCE 가 아닌 것을 공식 확인 사실처럼 표시하지 않는다.
     */
    verification?: 'VERIFIED_SOURCE' | 'DRAFT_UNVERIFIED' | 'DEMO_FIXTURE';
    source_url?: string | null;
    source: string;
  };
  // 데이터 품질은 risk.data_quality 하나가 정본이다. 최상위에 복사본을 두지 않는다.
  // 관측률·센서 수가 필요하면 response.risk.data_quality 를 읽는다.
  /** UI-07. 항상 화면에 보여야 한다. */
  notice: {
    disclaimer: string;
    route_limit?: string | null;
    emergency_note?: string | null;
  };
  versions?: Record<string, string | null>;
}

/**
 * GET /api/scenarios — M-18. 수동 재판단이 고를 수 있는 재생 시각.
 *
 * `pending` 은 아직 만들지 않은 시나리오다. 목록에 없는 것을 있는 척하지 않는다.
 */
export interface ScenarioList {
  scenarios: {
    id: string;
    label: string;
    why?: string | null;
    clock_label: string;
    action: Action;
  }[];
  pending: string[];
}

/** GET /api/destinations */
export interface DestinationList {
  status: string;
  scope: { center_label: string; center_lat: number; center_lon: number; radius_m: number };
  points: (DestinationPoint & { coordinate_quality: string; distance_from_center_m: number })[];
  note: string;
}
