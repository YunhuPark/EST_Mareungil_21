/**
 * 지도에 그릴 것 — 순수 변환 검사.
 *
 * 금칙어 검사(`tests/test_forbidden_wording.py`)가 **쓰면 안 되는 말**을 막는다면
 * 이 파일은 **반드시 있어야 하는 말**과 **지어내면 안 되는 값**을 지킨다. 둘 다
 * 실제로 한 번씩 당한 것이라 검사로 굳힌다.
 *
 * - 한계 문구: 선 스타일만 바꾼 커밋이 RT-02 문구를 지웠는데, leaflet 팝업
 *   문자열이라 jsdom 에 보이지 않아 어떤 테스트도 빨개지지 않았다.
 * - 좌표: 출발지와 목적지의 **중점**에 반경 250m 원을 놓고 침수 위험 구역이라
 *   불렀다. 관측도 공식 통제도 아닌 두 점의 평균이었다(`4cc3a03` 이 되돌렸다).
 *
 * 손으로 만든 응답을 쓰지 않는다 — 계약 픽스처를 그대로 먹인다.
 */

import { describe, expect, it } from 'vitest';

import calm from '../../../contracts/fixtures/demo/DS-S1.assess_response.json';
import rising from '../../../contracts/fixtures/demo/DS-S6.assess_response.json';
import peak from '../../../contracts/fixtures/demo/DS-S4.assess_response.json';
import { CANDIDATE_LINE_LIMIT } from '../contracts/enums';
import type { AssessResponse } from '../contracts/types';
import {
  baseFeatures,
  evidenceCounts,
  evidenceFeatures,
  popupHtml,
  sensorsInScope,
  type MapFeature,
  type Scope,
} from './features';

const s1 = calm as unknown as AssessResponse;
const s6 = rising as unknown as AssessResponse;
const s4 = peak as unknown as AssessResponse;

/** 재생 범위. 실제 응답에서는 `/api/destinations` 가 준다. */
const scope: Scope = {
  center_label: '강남역',
  center_lat: 37.4979,
  center_lon: 127.0276,
  radius_m: 1000,
};

const CASES: Array<[string, AssessResponse]> = [
  ['DS-S1 평온', s1],
  ['DS-S6 상승', s6],
  ['DS-S4 피크', s4],
];

function allFeatures(data: AssessResponse, withScope: Scope | null = scope): MapFeature[] {
  const inScope = sensorsInScope(data.risk.sensors);
  return [
    ...baseFeatures(data),
    ...evidenceFeatures(inScope, withScope, data.risk.primary_horizon),
  ];
}

/** 도형이 쓰는 좌표를 전부 꺼낸다. */
function coordsOf(feature: MapFeature): Array<[number, number]> {
  const g = feature.geometry;
  if (g.shape === 'line') return g.points.map((p) => [p.lat, p.lon]);
  return [[g.lat, g.lon]];
}

describe('한계 문구 (RT-02 · M-22)', () => {
  it.each(CASES)('%s — 모든 도형이 비어 있지 않은 한계 문구를 든다', (_label, data) => {
    const features = allFeatures(data);
    expect(features.length).toBeGreaterThan(0);

    for (const feature of features) {
      expect(feature.limit.trim(), `${feature.kind} 에 한계 문구가 없다`).not.toBe('');
    }
  });

  it('후보 경로 선의 문구는 팝업 마지막 줄로 남는다', () => {
    const line = allFeatures(s1).find((f) => f.kind === 'CANDIDATE_LINE');
    expect(line, 'DS-S1 에는 도달 대상이 있어 선이 그려져야 한다').toBeDefined();

    expect(line!.limit).toBe(CANDIDATE_LINE_LIMIT);
    expect(popupHtml(line!).endsWith(CANDIDATE_LINE_LIMIT)).toBe(true);
  });

  it.each(CASES)('%s — 팝업에는 항상 한계 문구가 들어간다', (_label, data) => {
    for (const feature of allFeatures(data)) {
      expect(popupHtml(feature)).toContain(feature.limit);
    }
  });
});

describe('팝업은 응답 문자열을 마크업으로 해석하지 않는다', () => {
  /**
   * leaflet 의 `bindPopup(string)` 은 문자열을 HTML 로 넣는다. 팝업에 실리는 값
   * 셋이 응답에서 오므로(도달 대상 이름 · 센서 id·자치구 · 범위 이름), 실사용
   * 데이터로 갈아탈 때 그대로 두면 주입 통로가 된다.
   *
   * 계약은 이것을 막지 않는다 — JSON Schema 는 문자열 안에 `<script>` 가 있는지
   * 보지 않는다. 그래서 넣는 쪽에서 막고, 그것을 여기서 확인한다.
   */
  const PAYLOAD = '<img src=x onerror="alert(1)">';

  it('도달 대상 이름에 태그가 들어와도 글자로 남는다', () => {
    const hostile: AssessResponse = {
      ...s1,
      route: { ...s1.route, target: { ...s1.route.target!, label: PAYLOAD } },
    };

    const target = baseFeatures(hostile).find((f) => f.kind === 'TARGET');
    const html = popupHtml(target!);

    // `onerror=` 라는 **글자**는 남는다. 그것으로 충분하다 — `<` 와 `"` 가
    // 막혀 있으면 속성이 될 수 없다. 태그가 열리는지만 본다.
    expect(html).not.toContain('<img');
    expect(html).toContain('&lt;img');
    expect(html).toContain('&quot;');
  });

  it('센서 자치구 이름도 같이 막는다', () => {
    const sensors = sensorsInScope(s4.risk.sensors);
    expect(sensors.length).toBeGreaterThan(0);

    const hostile = [{ ...sensors[0]!, district: PAYLOAD }];
    const point = evidenceFeatures(hostile, scope, s4.risk.primary_horizon).find(
      (f) => f.kind === 'SENSOR_POINT',
    );

    expect(popupHtml(point!)).not.toContain('<img');
  });

  it('우리가 넣는 줄바꿈만 마크업으로 남는다', () => {
    const point = allFeatures(s4).find((f) => f.kind === 'SENSOR_POINT');
    const html = popupHtml(point!);

    // 여러 줄짜리 팝업이라 <br> 은 있어야 하고, 그 밖의 태그는 없어야 한다.
    expect(html).toContain('<br>');
    expect(html.replace(/<br>/g, '')).not.toMatch(/<[a-zA-Z/]/);
  });
});

describe('좌표를 지어내지 않는다', () => {
  /** 응답이 실어 보낸 좌표 전부. 이 밖의 좌표는 화면이 만든 것이다. */
  function allowed(data: AssessResponse, withScope: Scope | null): Set<string> {
    const out = new Set<string>();
    const put = (lat: number | null | undefined, lon: number | null | undefined) => {
      if (lat != null && lon != null) out.add(`${lat},${lon}`);
    };

    put(data.location.lat, data.location.lon);
    put(data.route.target?.lat, data.route.target?.lon);
    for (const sensor of data.risk.sensors) put(sensor.location.lat, sensor.location.lon);
    if (withScope) put(withScope.center_lat, withScope.center_lon);

    return out;
  }

  it.each(CASES)('%s — 모든 도형의 좌표가 응답에 있던 값이다', (_label, data) => {
    const known = allowed(data, scope);

    for (const feature of allFeatures(data)) {
      for (const [lat, lon] of coordsOf(feature)) {
        expect(known.has(`${lat},${lon}`), `${feature.kind} 가 응답에 없는 좌표를 쓴다`).toBe(
          true,
        );
      }
    }
  });

  it('면(面) 도형을 만들지 않는다 — 가진 것은 지점 예측이지 구역이 아니다', () => {
    // 원은 서버가 준 판단 범위 하나뿐이고, 그 반경도 응답 값이다.
    const circles = allFeatures(s4).filter((f) => f.geometry.shape === 'circle');

    expect(circles).toHaveLength(1);
    const only = circles[0]!;
    expect(only.kind).toBe('SCOPE_CIRCLE');
    expect(only.geometry).toMatchObject({ radiusM: scope.radius_m });
  });
});

describe('센서 도형', () => {
  it.each(CASES)('%s — 도형 개수가 범위 안 센서 수와 같다', (_label, data) => {
    const inScope = sensorsInScope(data.risk.sensors);
    const points = evidenceFeatures(inScope, scope, data.risk.primary_horizon).filter(
      (f) => f.kind === 'SENSOR_POINT',
    );

    expect(points).toHaveLength(inScope.length);
  });

  it('좌표를 모르는 센서는 도형이 되지 않는다', () => {
    // 픽스처에 실제로 그런 센서가 있어야 이 검사가 의미를 가진다.
    const unmatched = s1.risk.sensors.filter((s) => s.location.lat == null);
    expect(unmatched.length).toBeGreaterThan(0);

    expect(sensorsInScope(s1.risk.sensors).length).toBeLessThan(s1.risk.sensors.length);
  });

  it('근사 좌표는 정밀 좌표보다 크고 흐리게 그린다', () => {
    const inScope = sensorsInScope(s4.risk.sensors);
    const points = evidenceFeatures(inScope, scope, s4.risk.primary_horizon).filter(
      (f) => f.kind === 'SENSOR_POINT',
    );

    const radii = points.map((p) => p.style.radius);
    expect(radii.every((r) => typeof r === 'number')).toBe(true);

    const distinct = Array.from(new Set(radii as number[]));
    // 품질이 섞여 있지 않으면 이 검사는 아무것도 지키지 않는다.
    expect(distinct.length).toBeGreaterThan(1);
    expect(Math.max(...distinct)).toBeGreaterThan(Math.min(...distinct));
  });

  it('세는 규칙은 area_risk.basis 와 같은 수를 낸다', () => {
    for (const [, data] of CASES) {
      const found = data.risk.area_risk.basis.match(/비율 (\d+)\/(\d+)\./);
      expect(found, `basis 에서 비율을 찾지 못했다: ${data.risk.area_risk.basis}`).not.toBeNull();

      const counts = evidenceCounts(sensorsInScope(data.risk.sensors));
      expect(counts.over).toBe(Number(found![1]));
      expect(counts.judged).toBe(Number(found![2]));
    }
  });
});

describe('없는 것을 그리지 않는다', () => {
  it('범위를 못 받으면 원만 빠지고 센서는 남는다', () => {
    const inScope = sensorsInScope(s4.risk.sensors);
    const features = evidenceFeatures(inScope, null, s4.risk.primary_horizon);

    expect(features.some((f) => f.kind === 'SCOPE_CIRCLE')).toBe(false);
    expect(features.filter((f) => f.kind === 'SENSOR_POINT')).toHaveLength(inScope.length);
  });

  it('위치 좌표가 없으면 아무 도형도 만들지 않는다', () => {
    const nowhere: AssessResponse = {
      ...s1,
      location: { ...s1.location, lat: null, lon: null },
    };

    expect(baseFeatures(nowhere)).toHaveLength(0);
  });

  it('도달 대상이 없으면 선을 긋지 않는다', () => {
    const noTarget: AssessResponse = { ...s1, route: { ...s1.route, target: null } };
    const kinds = baseFeatures(noTarget).map((f) => f.kind);

    expect(kinds).toEqual(['ORIGIN']);
  });
});
