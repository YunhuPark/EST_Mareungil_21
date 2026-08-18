/**
 * 지도.
 *
 * 지도 타일은 데모 중 **유일한 런타임 외부 의존**이다(설계서 8.5.3). 그래서
 * 이 컴포넌트는 화면에서 가장 아래에 있고, 실패해도 위험·행동·시각·119 는
 * 그대로 보인다. 타일이 안 뜨면 조용히 비는 대신 왜 안 보이는지 적는다.
 *
 * UI-05. 공식 정보는 실선, 예측은 점선으로 구분한다.
 * F-11. 침수흔적 레이어는 기본 OFF 다.
 */

import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import type { AssessResponse } from '../contracts/types';

type TileState = 'loading' | 'ok' | 'failed';

export function MapPanel({ data }: { data: AssessResponse }) {
  const holder = useRef<HTMLDivElement>(null);
  const [tiles, setTiles] = useState<TileState>('loading');

  const { lat, lon } = data.location;
  const target = data.route.target;

  useEffect(() => {
    const el = holder.current;
    if (!el || lat == null || lon == null) return;

    let isMounted = true;
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

        // [DEMO] "위험금지침수구역 피해서 우회하기"
        // 실제 경로 탐색 대신, OSRM Public API (OpenStreetMap 기반 무료 서비스)를 호출합니다.
        // 침수구역을 피하기 위해, 해당 위치 근처에서 약 350m 벗어난 '경유지(Waypoint)'를 추가합니다.
        
        const Ax = 0.292; const Ay = -0.956;
        const Bx = 0.956; const By = 0.292;

        const dx = target.lon - lon;
        const dy = target.lat - lat;
        const a = dx * Ax + dy * Ay;
        const b = dx * Bx + dy * By;

        const midLat = (Number(lat) + Number(target.lat)) / 2;
        const midLon = (Number(lon) + Number(target.lon)) / 2;

        // [DEMO] 침수 위험 통제 구역 (빨간 원) - 실제 지도 상의 물리적 크기 고정 (미터 단위)
        const dangerCircle = L.circle([midLat, midLon], {
          color: 'red',
          fillColor: '#ff0000',
          fillOpacity: 0.3,
          radius: 250, // 실제 반경 250m 고정
          weight: 2
        }).addTo(map);

        // [DEMO] 배경 박스(칸)가 있는 텍스트를 원 정중앙에 고정
        const textIcon = L.divIcon({
          html: '<div style="color:red; font-weight:bold; font-size:11px; text-align:center; background:rgba(255,255,255,0.8); padding:2px 4px; border-radius:2px; border:1px solid red; white-space:nowrap;">침수위험구역</div>',
          className: '', // Leaflet 기본 마커 스타일 제거
          iconSize: [80, 20],
          iconAnchor: [40, 10]
        });
        const textMarker = L.marker([midLat, midLon], { icon: textIcon, interactive: false });

        // 지도를 축소하면 하얀 박스가 붉은 원을 벗어나 거대해지는 문제 방지
        const updateVisibility = () => {
          if (!map) return;
          // 줌 레벨이 15 이상(충분히 확대됨)일 때만 글자를 보여줌
          if (map.getZoom() >= 15) {
            if (!map.hasLayer(textMarker)) textMarker.addTo(map);
          } else {
            if (map.hasLayer(textMarker)) map.removeLayer(textMarker);
          }
        };

        map.on('zoomend', updateVisibility);
        updateVisibility(); // 초기 렌더링 시 적용

        // [DEMO] 위험구역을 관통하는 기존 경로 (회색 점선)
        L.polyline(
          [
            [lat, lon],
            [target.lat, target.lon],
          ],
          { weight: 4, dashArray: '8 6', opacity: 0.6, color: '#333' },
        ).addTo(map);

        const R = 0.0028; // 약 310m (반지름 250m 원을 완벽히 피하기 위한 우회 사각형의 절반 크기)
        
        let wp1Lat, wp1Lon, wp2Lat, wp2Lon;

        // 진행 방향에 따라 금지구역을 완벽히 회피할 2개의 코너 경유지 계산
        if (Math.abs(b) > Math.abs(a)) {
            const signB = Math.sign(b) || 1;
            wp1Lat = midLat + R * Ay - signB * R * By;
            wp1Lon = midLon + R * Ax - signB * R * Bx;
            wp2Lat = midLat + R * Ay + signB * R * By;
            wp2Lon = midLon + R * Ax + signB * R * Bx;
        } else {
            const signA = Math.sign(a) || 1;
            wp1Lat = midLat + R * By - signA * R * Ay;
            wp1Lon = midLon + R * Bx - signA * R * Ax;
            wp2Lat = midLat + R * By + signA * R * Ay;
            wp2Lon = midLon + R * Bx + signA * R * Ax;
        }

        // OSRM API 호출 (도보 기준: 골목길, 흰색 길을 모두 따라가며 금지구역 외곽을 완벽히 돎)
        const osrmUrl = `https://router.project-osrm.org/route/v1/walking/${lon},${lat};${wp1Lon},${wp1Lat};${wp2Lon},${wp2Lat};${target.lon},${target.lat}?overview=full&geometries=geojson`;

        fetch(osrmUrl)
          .then(res => res.json())
          .then(data => {
            if (isMounted && map && data.routes && data.routes[0]) {
              const coords = data.routes[0].geometry.coordinates;
              const latLngs = coords.map((c: number[]) => [c[1], c[0]] as [number, number]);
              
              // 위험을 피해서 실제 도로를 따라가는 우회경로(파란색 실선)
              L.polyline(latLngs, { weight: 5, opacity: 0.9, color: '#0066ff' })
                .bindPopup('우회경로 (OSRM 기반)')
                .addTo(map);
            }
          })
          .catch(err => console.error('OSRM route fetch error:', err));
      }
    } catch {
      setTiles('failed');
    }

    return () => {
      isMounted = false;
      map?.remove();
    };
  }, [lat, lon, target]);

  if (lat == null || lon == null) {
    return (
      <section className="card map" aria-label="지도">
        <p className="map__fallback">위치 좌표가 없어 지도를 표시하지 않습니다.</p>
      </section>
    );
  }

  return (
    <section className="card map" aria-label="지도">
      <h2 className="card__title">지도</h2>
      <div ref={holder} className="map__canvas" role="img" aria-label="후보 경로 지도" />
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
    </section>
  );
}
