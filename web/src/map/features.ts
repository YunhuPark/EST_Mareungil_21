/**
 * 지도에 그릴 것 — **순수 변환**.
 *
 * 이 파일은 leaflet 을 import 하지 않는다. 응답을 도형 목록으로 옮기기만 하고
 * 그리지 않는다. 그렇게 나눈 이유가 둘이다.
 *
 * 1. **검사할 수 있게 하려고.** jsdom 에는 지도가 없어서 leaflet 도형은 테스트에
 *    보이지 않는다. 예전에는 "무엇을 몇 개 그리는가"를 확인할 방법이 아예 없었고,
 *    그래서 화면이 근거보다 많이 주장해도 초록이었다.
 * 2. **되돌리기 단위를 줄이려고.** 지도 생명주기·스타일·문구·React 상태가 한
 *    파일에 있으면 세 사람이 같은 파일을 고치고, 되돌릴 때도 파일 통째로 되돌리게
 *    된다 — 실제로 그렇게 3커밋을 되돌렸다(`4cc3a03`).
 *
 * `limit` 은 **선택 필드가 아니다.**
 * -------------------------------
 * 모든 도형은 "이 도형이 주장하지 않는 것"을 함께 들고 다닌다. 타입이 그것을
 * 강제하므로 문구 없이 도형을 만들 수 없다. 예전에 선 스타일만 바꾼 커밋이
 * RT-02 한계 문구를 조용히 지웠고 어떤 검사도 빨개지지 않았다(`dba9648` 이
 * 사람 눈으로 되살렸다). 이제는 타입과 `features.test.ts` 가 같이 막는다.
 *
 * 좌표를 **지어내지 않는다.**
 * ---------------------------
 * 여기서 만드는 좌표는 전부 응답에 이미 있던 값이다. 계산해서 만든 좌표는 하나도
 * 없다. 앞선 시도가 되돌려진 이유가 출발지와 목적지의 중점에 반경 250m 원을
 * 놓고 그것을 침수 위험 구역이라 부른 것이었다 — 관측도 공식 통제도 아닌
 * 두 점의 평균이었다. `features.test.ts` 가 이 규칙을 검사한다.
 */

import {
  AREA_SCOPE_NOTE,
  CANDIDATE_LINE_LIMIT,
  ORIGIN_LIMIT,
  SENSOR_LAYER_NOTE,
  SENSOR_QUALITY_IS_PRECISE,
  SENSOR_QUALITY_LABEL,
  TARGET_LIMIT,
} from '../contracts/enums';
import type { AssessResponse, DestinationList, SensorReading } from '../contracts/types';

export type Scope = NonNullable<DestinationList['scope']>;

export type MapGeometry =
  /** 화면 픽셀 크기로 그리는 점. 지도를 줌해도 커지지 않는다. */
  | { shape: 'point'; lat: number; lon: number }
  | { shape: 'line'; points: Array<{ lat: number; lon: number }> }
  /** 미터 반경으로 그리는 원. 줌하면 같이 커진다. */
  | { shape: 'circle'; lat: number; lon: number; radiusM: number };

/**
 * 색만으로 가르지 않는다(UI-06/UI-09 흑백 판독). 채움과 실선·점선으로도 갈린다.
 *
 * 전부 선택 필드다. **비우면 leaflet 기본값을 쓴다** — 기존 표시를 그대로
 * 옮기기 위한 것이며, 값을 적는 자리와 안 적는 자리를 리팩터링이 바꾸지 않는다.
 */
export interface FeatureStyle {
  color?: string;
  weight?: number;
  /** `point` 의 화면 픽셀 반지름. `circle` 은 `radiusM` 을 쓴다. */
  radius?: number;
  dashArray?: string;
  opacity?: number;
  fill?: boolean;
  fillOpacity?: number;
}

export interface MapFeature {
  kind: 'ORIGIN' | 'TARGET' | 'CANDIDATE_LINE' | 'SCOPE_CIRCLE' | 'SENSOR_POINT';
  geometry: MapGeometry;
  /** 팝업 첫 줄. */
  label: string;
  /** 사실 관계를 덧붙이는 줄. 없으면 비운다. */
  detail?: string[];
  /**
   * **이 도형이 주장하지 않는 것.** 빈 문자열을 허용하지 않는다.
   * 도형을 늘릴 때 문구를 같이 쓰지 않으면 타입 검사가 먼저 막는다.
   */
  limit: string;
  style: FeatureStyle;
}

/** 팝업 HTML. 한계 문구는 **항상 마지막 줄로 남는다.** */
export function popupHtml(feature: MapFeature): string {
  return [feature.label, ...(feature.detail ?? []), feature.limit].join('<br>');
}

/** 임계 초과 · 미만 · 판단 불가. 셋을 각각 다르게 그린다. */
export function verdictOf(sensor: SensorReading): 'OVER' | 'UNDER' | 'UNKNOWN' {
  if (sensor.exceeds_sensor_threshold === null) return 'UNKNOWN';
  return sensor.exceeds_sensor_threshold ? 'OVER' : 'UNDER';
}

/**
 * 센서 하나의 표현.
 *
 * 근사 좌표는 **더 크고 흐리게** 그린다. 정밀 좌표와 같은 크기의 점으로 찍으면
 * 없는 정밀도를 주장하게 된다.
 */
function sensorStyle(sensor: SensorReading): FeatureStyle {
  const verdict = verdictOf(sensor);
  const precise = SENSOR_QUALITY_IS_PRECISE[sensor.location.quality];

  const color =
    verdict === 'OVER' ? '#c8102e' : verdict === 'UNDER' ? '#0f766e' : '#6b7280';

  return {
    radius: precise ? 7 : 13,
    color,
    weight: precise ? 3 : 2,
    // 근사 좌표와 판단 불가는 점선으로 "확정이 아니다"를 형태로도 말한다.
    dashArray: precise && verdict !== 'UNKNOWN' ? undefined : '4 3',
    fill: true,
    // 임계 초과만 진하게 채운다. 넓게 그린 근사 좌표는 더 흐리게 둔다.
    fillOpacity: verdict === 'OVER' ? (precise ? 0.65 : 0.3) : precise ? 0.2 : 0.1,
  };
}

/** 팝업 본문. AI-08 — 하수 고수위를 도로 침수로 단정하지 않는다. */
function sensorDetail(sensor: SensorReading, horizon: number): string[] {
  const verdict = verdictOf(sensor);
  const probability = sensor.horizons[String(horizon) as '10' | '30' | '60']?.high_level_p;

  const verdictText =
    verdict === 'OVER'
      ? '임계 초과'
      : verdict === 'UNDER'
        ? '임계 미만'
        : '판단할 확률값이 없습니다';

  const lines = [
    probability == null
      ? `t+${horizon}분 하수관로 고수위 확률: 값 없음`
      : `t+${horizon}분 하수관로 고수위 확률 ${(probability * 100).toFixed(1)}% — ${verdictText}`,
    `좌표 품질: ${SENSOR_QUALITY_LABEL[sensor.location.quality]}`,
  ];

  if (!SENSOR_QUALITY_IS_PRECISE[sensor.location.quality]) {
    lines.push('근사 위치이므로 넓게 표시했습니다.');
  }

  return lines;
}

/**
 * 지도에 올릴 센서.
 *
 * 범위 판정은 서버가 준 `in_area_scope` 를 그대로 쓴다. 좌표를 한 번 더 보는
 * 이유는 정밀도 때문이 아니라, 계약이 깨졌을 때 지도가 `(0,0)` 에 점을 찍지
 * 않게 하려는 것이다 — 스키마도 같은 조합을 거부한다.
 */
export function sensorsInScope(sensors: SensorReading[]): SensorReading[] {
  return sensors.filter(
    (s) => s.in_area_scope && s.location.lat != null && s.location.lon != null,
  );
}

/** `area_risk.basis` 비율의 분모·분자와 같은 수. 화면이 다시 세지 않게 한 곳에 둔다. */
export function evidenceCounts(inScope: SensorReading[]): { judged: number; over: number } {
  const judged = inScope.filter((s) => s.exceeds_sensor_threshold !== null);
  return {
    judged: judged.length,
    over: judged.filter((s) => s.exceeds_sensor_threshold === true).length,
  };
}

/**
 * 항상 보이는 도형 — 현재 위치, 도달 대상, 둘을 잇는 후보 선.
 *
 * 좌표는 `location` 과 `route.target` 에서만 온다.
 */
export function baseFeatures(data: AssessResponse): MapFeature[] {
  const { lat, lon } = data.location;
  if (lat == null || lon == null) return [];

  const features: MapFeature[] = [
    {
      kind: 'ORIGIN',
      geometry: { shape: 'point', lat, lon },
      label: '현재 위치',
      limit: ORIGIN_LIMIT,
      style: { radius: 8, weight: 3 },
    },
  ];

  const target = data.route.target;
  if (!target) return features;

  features.push({
    kind: 'TARGET',
    geometry: { shape: 'point', lat: target.lat, lon: target.lon },
    label: target.label,
    limit: TARGET_LIMIT,
    style: { radius: 8, weight: 3, dashArray: '4 3' },
  });

  features.push({
    kind: 'CANDIDATE_LINE',
    geometry: {
      shape: 'line',
      points: [
        { lat, lon },
        { lat: target.lat, lon: target.lon },
      ],
    },
    label: '추천 후보 경로',
    // RT-02 · M-22. 선과 한 몸이다. 스타일만 바꾸는 변경이 이 줄을 지울 수 없다.
    limit: CANDIDATE_LINE_LIMIT,
    style: { color: '#0066ff', weight: 4, dashArray: '8 6', opacity: 0.8, fill: false },
  });

  return features;
}

/**
 * F-11 위험 근거 레이어의 도형 — 판단 범위와 범위 안 센서.
 *
 * 화면은 거리를 다시 재지 않고 임계를 다시 적용하지 않는다(CLAUDE.md 10절).
 * 여기에 **없는 것**을 적어 둔다. 앞선 시도가 되돌려진 이유가 이것이다.
 *
 * - 공식 통제·확인 침수 구역: `geom_ref` 가 문자열 참조뿐이라 그릴 좌표가 없다.
 *   좌표를 추정해 도형을 만들지 않는다.
 * - 도형으로서의 위험 구역: 우리가 가진 것은 지점 예측이지 면이 아니다.
 *   지점을 이어 면을 만들면 없는 판단을 지어내게 된다.
 */
export function evidenceFeatures(
  inScope: SensorReading[],
  scope: Scope | null,
  horizon: number,
): MapFeature[] {
  const features: MapFeature[] = [];

  // 판단 범위. 위험이 아니라 경계이므로 채우지 않는다.
  if (scope) {
    features.push({
      kind: 'SCOPE_CIRCLE',
      geometry: {
        shape: 'circle',
        lat: scope.center_lat,
        lon: scope.center_lon,
        radiusM: scope.radius_m,
      },
      label: `${scope.center_label} 반경 ${scope.radius_m}m`,
      limit: AREA_SCOPE_NOTE,
      style: { color: '#6b7280', weight: 2, dashArray: '6 4', fill: false },
    });
  }

  for (const sensor of inScope) {
    features.push({
      kind: 'SENSOR_POINT',
      geometry: {
        shape: 'point',
        lat: sensor.location.lat as number,
        lon: sensor.location.lon as number,
      },
      label: `센서 ${sensor.id} · ${sensor.district}`,
      detail: sensorDetail(sensor, horizon),
      limit: SENSOR_LAYER_NOTE,
      style: sensorStyle(sensor),
    });
  }

  return features;
}
