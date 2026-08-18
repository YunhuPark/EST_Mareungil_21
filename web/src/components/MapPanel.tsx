/**
 * 지도.
 *
 * 지도 타일은 데모 중 **유일한 런타임 외부 의존**이다(설계서 8.5.3). 그래서
 * 이 컴포넌트는 화면에서 가장 아래에 있고, 실패해도 위험·행동·시각·119 는
 * 그대로 보인다. 타일이 안 뜨면 조용히 비는 대신 왜 안 보이는지 적는다.
 *
 * UI-05. 공식 정보는 실선, 예측은 점선으로 구분한다.
 * F-11. 위험 근거 레이어는 기본 OFF 다.
 *
 * 위험 근거 레이어에 대하여
 * -------------------------
 * 그리는 것은 **응답이 실어 보낸 값뿐이다.** 좌표는 `risk.sensors[].location`,
 * 범위는 `/api/destinations` 의 `scope`, 판정은 `in_area_scope` ·
 * `exceeds_sensor_threshold` 다. 화면은 거리를 다시 재지 않고 임계를 다시
 * 적용하지 않는다(CLAUDE.md 10절) — 그래야 지도의 점 개수와
 * `area_risk.basis` 의 "n/m" 이 어긋나지 않는다.
 *
 * 여기에 **없는 것**을 적어 둔다. 앞선 시도가 되돌려진 이유가 이것이다.
 *
 * - 공식 통제·확인 침수 구역: `geom_ref` 가 문자열 참조뿐이라 그릴 좌표가 없다.
 *   좌표를 추정해 도형을 만들지 않는다.
 * - 도형으로서의 위험 구역: 우리가 가진 것은 지점 예측이지 면이 아니다.
 *   지점을 이어 면을 만들면 없는 판단을 지어내게 된다.
 *
 * 토글·요약·한계 문구는 leaflet 이 아니라 **React DOM 에 둔다.** 타일이 실패한
 * 상황에서도 근거가 화면에 남아야 하고(8.5.3), 그래야 검사도 받는다.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import {
  AREA_SCOPE_NOTE,
  SENSOR_LAYER_EMPTY,
  SENSOR_LAYER_NOTE,
  SENSOR_LAYER_TITLE,
  SENSOR_QUALITY_IS_PRECISE,
  SENSOR_QUALITY_LABEL,
} from '../contracts/enums';
import type { AssessResponse, DestinationList, SensorReading } from '../contracts/types';

type TileState = 'loading' | 'ok' | 'failed';
type Scope = DestinationList['scope'];

/** 임계 초과 · 미만 · 판단 불가. 셋을 각각 다르게 그린다. */
function verdictOf(sensor: SensorReading): 'OVER' | 'UNDER' | 'UNKNOWN' {
  if (sensor.exceeds_sensor_threshold === null) return 'UNKNOWN';
  return sensor.exceeds_sensor_threshold ? 'OVER' : 'UNDER';
}

/**
 * 센서 하나의 표현.
 *
 * 색만으로 가르지 않는다(UI-06/UI-09 흑백 판독) — 채움 여부와 실선·점선으로도
 * 갈린다. 그리고 근사 좌표는 **더 크고 흐리게** 그린다. 정밀 좌표와 같은 크기의
 * 점으로 찍으면 없는 정밀도를 주장하게 된다.
 */
function styleFor(sensor: SensorReading): L.CircleMarkerOptions & { radius: number } {
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
    fillColor: color,
    // 임계 초과만 진하게 채운다. 넓게 그린 근사 좌표는 더 흐리게 둔다.
    fillOpacity: verdict === 'OVER' ? (precise ? 0.65 : 0.3) : precise ? 0.2 : 0.1,
  };
}

/** 팝업 문구. AI-08 — 하수 고수위를 도로 침수로 단정하지 않는다. */
function popupFor(sensor: SensorReading, horizon: number): string {
  const verdict = verdictOf(sensor);
  const probability = sensor.horizons[String(horizon) as '10' | '30' | '60']?.high_level_p;

  const verdictText =
    verdict === 'OVER'
      ? '임계 초과'
      : verdict === 'UNDER'
        ? '임계 미만'
        : '판단할 확률값이 없습니다';

  const lines = [
    `센서 ${sensor.id} · ${sensor.district}`,
    probability == null
      ? `t+${horizon}분 하수관로 고수위 확률: 값 없음`
      : `t+${horizon}분 하수관로 고수위 확률 ${(probability * 100).toFixed(1)}% — ${verdictText}`,
    `좌표 품질: ${SENSOR_QUALITY_LABEL[sensor.location.quality]}`,
  ];

  if (!SENSOR_QUALITY_IS_PRECISE[sensor.location.quality]) {
    lines.push('근사 위치이므로 넓게 표시했습니다.');
  }

  return lines.join('<br>');
}

export function MapPanel({
  data,
  scope,
  /** 시안의 경로안내 화면은 지도를 화면 폭 가득 얹는다. 카드형이 기본이다. */
  variant = 'card',
}: {
  data: AssessResponse;
  scope?: Scope | null;
  variant?: 'card' | 'hero';
}) {
  const holder = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const [tiles, setTiles] = useState<TileState>('loading');
  // F-11. 기본 OFF. 사용자가 켤 때만 근거 레이어를 올린다.
  const [layerOn, setLayerOn] = useState(false);

  const { lat, lon } = data.location;
  const target = data.route.target;
  const area = data.risk.area_risk;
  const horizon = data.risk.primary_horizon;

  /**
   * 지도에 올릴 센서.
   *
   * 범위 판정은 서버가 준 `in_area_scope` 를 그대로 쓴다. 좌표를 한 번 더 보는
   * 이유는 정밀도 때문이 아니라, 계약이 깨졌을 때 지도가 `(0,0)` 에 점을 찍지
   * 않게 하려는 것이다 — 스키마도 같은 조합을 거부한다.
   */
  const inScope = useMemo(
    () =>
      data.risk.sensors.filter(
        (s) => s.in_area_scope && s.location.lat != null && s.location.lon != null,
      ),
    [data.risk.sensors],
  );

  /** `area_risk` 비율의 분모·분자와 같은 수. 두 조건을 함께 봐야 한다. */
  const judged = useMemo(
    () => inScope.filter((s) => s.exceeds_sensor_threshold !== null),
    [inScope],
  );
  const overCount = useMemo(
    () => judged.filter((s) => s.exceeds_sensor_threshold === true).length,
    [judged],
  );

  useEffect(() => {
    const el = holder.current;
    if (!el || lat == null || lon == null) return;

    let map: L.Map | undefined;
    try {
      map = L.map(el, { attributionControl: true, zoomControl: true }).setView([lat, lon], 15);

      const layer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap',
      });
      layer.on('tileerror', () => setTiles('failed'));
      layer.on('load', () => setTiles('ok'));
      layer.addTo(map);

      L.circleMarker([lat, lon], { radius: 8, weight: 3 })
        .bindPopup('현재 위치')
        .addTo(map);

      if (target) {
        // 도달 대상. 공식 후보 비교 결과이므로 선을 그어도 통행 보장이 아니다.
        L.circleMarker([target.lat, target.lon], { radius: 8, weight: 3, dashArray: '4 3' })
          .bindPopup(target.label)
          .addTo(map);

        L.polyline(
          [
            [lat, lon],
            [target.lat, target.lon],
          ],
          { weight: 4, dashArray: '8 6', opacity: 0.8, color: '#0066ff' },
        )
          .bindPopup('추천 후보 경로 (직선 표시 · 실제 경로 아님)')
          .addTo(map);
      }

      mapRef.current = map;
    } catch {
      setTiles('failed');
    }

    return () => {
      layerRef.current = null;
      mapRef.current = null;
      map?.remove();
    };
  }, [lat, lon, target]);

  /**
   * 위험 근거 레이어. 켤 때 만들고 끌 때 지운다.
   *
   * 지도 생성과 분리한 이유는 토글마다 지도를 다시 만들지 않기 위해서다.
   * 지도가 없으면(타일 실패·jsdom) 아무것도 하지 않고 조용히 넘어간다 —
   * 요약과 한계 문구는 아래 DOM 에 그대로 남는다.
   */
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    layerRef.current?.remove();
    layerRef.current = null;
    if (!layerOn) return;

    try {
      const group = L.layerGroup();

      // 판단 범위. 위험이 아니라 경계이므로 채우지 않는다.
      if (scope) {
        L.circle([scope.center_lat, scope.center_lon], {
          radius: scope.radius_m,
          color: '#6b7280',
          weight: 2,
          dashArray: '6 4',
          fill: false,
        })
          .bindPopup(
            `${scope.center_label} 반경 ${scope.radius_m}m<br>${AREA_SCOPE_NOTE}`,
          )
          .addTo(group);
      }

      for (const sensor of inScope) {
        L.circleMarker(
          [sensor.location.lat as number, sensor.location.lon as number],
          styleFor(sensor),
        )
          .bindPopup(popupFor(sensor, horizon))
          .addTo(group);
      }

      group.addTo(map);
      layerRef.current = group;
    } catch {
      // 레이어를 못 올려도 지도와 요약은 그대로 둔다.
      layerRef.current = null;
    }
  }, [layerOn, inScope, scope, horizon]);

  if (lat == null || lon == null) {
    return (
      <section className="card map" aria-label="지도">
        <p className="map__fallback">위치 좌표가 없어 지도를 표시하지 않습니다.</p>
      </section>
    );
  }

  return (
    <section
      className={`card map ${variant === 'hero' ? 'map--hero' : ''}`}
      aria-label="지도"
    >
      {/* 시안의 지도 위 표식 자리. 점 하나로 끝내지 않고 글자를 함께 둔다.
          경로안내 화면은 지도가 맨 위에 붙으므로 표식을 아래로 내린다. */}
      {variant === 'card' && <p className="map__here">현재 위치</p>}

      <div ref={holder} className="map__canvas" role="img" aria-label="후보 경로 지도" />

      {variant === 'hero' && <p className="map__here">현재 위치</p>}
      {tiles === 'failed' && (
        <p className="map__fallback" role="status">
          지도 배경을 불러오지 못했습니다. 위의 위험 등급·행동·119 안내는 그대로 사용할 수 있습니다.
        </p>
      )}
      <p className="map__legend">
        <span className="legend legend--solid">실선 · 공식</span>
        <span className="legend legend--dashed">점선 · AI 예측</span>
      </p>
      <p className="map__note">
        선은 후보를 잇는 직선 표시이며 실제 통행 경로가 아닙니다.
      </p>

      {/*
        F-11. 위험 근거 레이어 토글. 기본 OFF 다.
        checkbox 를 쓰는 이유는 켜고 끄는 상태가 화면에 남아야 하기 때문이다.
      */}
      <p className="map__layer-toggle">
        <label>
          <input
            type="checkbox"
            checked={layerOn}
            onChange={(event) => setLayerOn(event.target.checked)}
          />{' '}
          {SENSOR_LAYER_TITLE} 표시
        </label>
      </p>

      {layerOn && (
        <div className="map__layer" role="group" aria-label={SENSOR_LAYER_TITLE}>
          {judged.length === 0 ? (
            /* 조용히 비우지 않는다 — '임계 미만'과 '판단할 자료가 없다'는 다른 상태다. */
            <p className="map__fallback" role="status">
              {SENSOR_LAYER_EMPTY}
            </p>
          ) : (
            <>
              <p className="map__layer-summary">
                범위 안 센서 {judged.length}개 중 임계 초과 {overCount}개
              </p>
              <p className="map__legend">
                <span className="legend legend--dashed">임계 초과</span>
                <span className="legend legend--dashed">임계 미만</span>
                <span className="legend legend--dashed">근사 좌표는 넓게</span>
              </p>
            </>
          )}

          {/* 서버가 만든 문장을 그대로 싣는다. 화면이 다시 조립하지 않는다. */}
          <p className="map__note">{area.basis}</p>
          <p className="map__note">{SENSOR_LAYER_NOTE}</p>
        </div>
      )}
    </section>
  );
}
