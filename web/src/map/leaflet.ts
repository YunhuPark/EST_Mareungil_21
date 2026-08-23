/**
 * leaflet 경계 — **이 파일에서만 지도를 만진다.**
 *
 * `features.ts` 가 정한 도형 목록을 받아 그리기만 한다. 무엇을 그릴지는 여기서
 * 정하지 않는다. 그래서 지도 라이브러리를 바꾸더라도 고칠 곳이 이 파일 하나다.
 *
 * 지도 타일은 데모 중 **유일한 런타임 외부 의존**이다(설계서 8.5.3). 실패해도
 * 조용히 비지 않고 왜 안 보이는지 화면이 적는다 — 그 문구는 React DOM 에 있고
 * 여기서는 실패 사실만 올려보낸다.
 */

import { useEffect, useRef, useState, type RefObject } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { popupHtml, type MapFeature } from './features';

export type TileState = 'loading' | 'ok' | 'failed';

const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

/** 도형 하나를 leaflet 레이어로. 스타일에 없는 값은 leaflet 기본값이 된다. */
function toLayer(feature: MapFeature): L.Layer {
  const { geometry, style } = feature;
  const shared: L.PathOptions = {
    color: style.color,
    weight: style.weight,
    dashArray: style.dashArray,
    opacity: style.opacity,
    fill: style.fill,
    fillColor: style.color,
    fillOpacity: style.fillOpacity,
  };

  switch (geometry.shape) {
    case 'point':
      return L.circleMarker([geometry.lat, geometry.lon], {
        ...shared,
        radius: style.radius,
      });
    case 'line':
      return L.polyline(
        geometry.points.map((p) => [p.lat, p.lon] as L.LatLngTuple),
        shared,
      );
    case 'circle':
      return L.circle([geometry.lat, geometry.lon], {
        ...shared,
        radius: geometry.radiusM,
      });
  }
}

/**
 * 도형을 올린다. **팝업은 항상 붙는다** — `popupHtml()` 이 한계 문구를 마지막
 * 줄로 넣으므로, 문구 없는 도형이 지도에 올라갈 수 없다.
 */
function addAll(into: L.Map | L.LayerGroup, features: MapFeature[]): void {
  for (const feature of features) {
    toLayer(feature).bindPopup(popupHtml(feature)).addTo(into);
  }
}

/**
 * 지도 생명주기.
 *
 * `features` 는 호출부에서 memo 로 고정한 배열이어야 한다 — 매 렌더 새 배열을
 * 넘기면 지도를 매번 다시 만든다.
 */
export function useLeafletMap(
  holder: RefObject<HTMLDivElement | null>,
  center: { lat: number; lon: number } | null,
  features: MapFeature[],
): { tiles: TileState; mapRef: RefObject<L.Map | null> } {
  const mapRef = useRef<L.Map | null>(null);
  const [tiles, setTiles] = useState<TileState>('loading');

  useEffect(() => {
    const el = holder.current;
    if (!el || !center) return;

    let map: L.Map | undefined;
    try {
      map = L.map(el, { attributionControl: true, zoomControl: true }).setView(
        [center.lat, center.lon],
        15,
      );

      const tileLayer = L.tileLayer(TILE_URL, {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap',
      });
      tileLayer.on('tileerror', () => setTiles('failed'));
      tileLayer.on('load', () => setTiles('ok'));
      tileLayer.addTo(map);

      addAll(map, features);
      mapRef.current = map;
    } catch {
      setTiles('failed');
    }

    return () => {
      mapRef.current = null;
      map?.remove();
    };
    // center 의 좌표가 바뀌거나 도형 목록이 바뀔 때만 다시 만든다.
  }, [holder, center?.lat, center?.lon, features]);

  return { tiles, mapRef };
}

/**
 * 켜고 끌 수 있는 레이어. 켤 때 만들고 끌 때 지운다.
 *
 * 지도 생성과 분리한 이유는 토글마다 지도를 다시 만들지 않기 위해서다. 지도가
 * 없으면(타일 실패·jsdom) 아무것도 하지 않고 조용히 넘어간다 — 요약과 한계
 * 문구는 React DOM 에 그대로 남는다.
 */
export function useFeatureLayer(
  mapRef: RefObject<L.Map | null>,
  features: MapFeature[],
  visible: boolean,
): void {
  const layerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    layerRef.current?.remove();
    layerRef.current = null;
    if (!visible) return;

    try {
      const group = L.layerGroup();
      addAll(group, features);
      group.addTo(map);
      layerRef.current = group;
    } catch {
      // 레이어를 못 올려도 지도와 요약은 그대로 둔다.
      layerRef.current = null;
    }
  }, [mapRef, features, visible]);
}
