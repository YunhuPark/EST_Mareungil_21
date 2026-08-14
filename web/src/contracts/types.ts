/**
 * `AssessResponse` 의 TypeScript 타입.
 *
 * 정본은 `contracts/schema/assess_response.schema.json` 이다. 스키마를 바꾸면
 * 이 파일도 같은 커밋에서 고친다(CLAUDE.md 7절).
 */

import type {
  Action,
  AiRiskLevel,
  Basis,
  HazardSign,
  Profile,
  RouteStatus,
  RouteTarget,
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
  ServiceRiskLevel,
  UserContext,
};

/** F-12. UI 는 Date.now() 를 쓰지 않고 label 을 그대로 표시한다. */
export interface Clock {
  mode: 'REPLAY';
  event_time: string;
  data_age_sec: number;
  stale: boolean;
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
  location: { lat: number | null; lon: number | null; quality: string };
}

export interface RiskAssessment {
  asof: string;
  primary_horizon: 10 | 30 | 60;
  sensors: SensorReading[];
  area_risk: AreaRisk;
  model: { name: string; version: string; threshold: number; threshold_basis: string };
  data_quality: { sensors_active: number; observed_rate: number; rain_available: boolean };
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
  /** 축 1. ai_risk_level 과 다른 필드다. 레이아웃 분기에 쓰지 않는다. */
  service_risk_level: ServiceRiskLevel;
  needs_route: boolean;
  next_check_at?: string | null;
  reason_code?: string | null;
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

export interface AssessResponse {
  contract_version: string;
  /** FIXTURE 인 동안은 모델이 지금 계산한 결과가 아니다. */
  source_kind?: 'FIXTURE' | 'STUB' | 'LIVE_PIPELINE';
  clock: Clock;
  location: UserLocation;
  risk: RiskAssessment;
  decision: Decision;
  route: SafeRoute;
  official?: {
    evacuation_order: boolean;
    alerts: unknown[];
    closures: unknown[];
    source: string;
  };
  data_quality?: {
    sensors_active: number;
    observed_rate: number;
    rain_available: boolean;
    reason?: string | null;
  };
  /** UI-07. 항상 화면에 보여야 한다. */
  notice: {
    disclaimer: string;
    route_limit?: string | null;
    emergency_note?: string | null;
  };
  versions?: Record<string, string | null>;
}

/** GET /api/destinations */
export interface DestinationList {
  status: string;
  scope: { center_label: string; center_lat: number; center_lon: number; radius_m: number };
  points: (DestinationPoint & { coordinate_quality: string; distance_from_center_m: number })[];
  note: string;
}
