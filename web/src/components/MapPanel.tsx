/**
 * 지도 — **DOM 과 문구만** 든다.
 *
 * 무엇을 그릴지는 `map/features.ts`(순수 변환), 어떻게 그릴지는
 * `map/leaflet.ts`(라이브러리 경계) 가 맡는다. 셋을 한 파일에 두었더니 되돌릴
 * 때도 파일 통째로 되돌리게 됐고, jsdom 에 안 보이는 leaflet 쪽 회귀를 검사할
 * 방법이 없었다.
 *
 * 지도 타일은 데모 중 **유일한 런타임 외부 의존**이다(설계서 8.5.3). 그래서
 * 이 컴포넌트는 화면에서 가장 아래에 있고, 실패해도 위험·행동·시각·119 는
 * 그대로 보인다. 타일이 안 뜨면 조용히 비는 대신 왜 안 보이는지 적는다.
 *
 * UI-05. 공식 정보는 실선, 예측은 점선으로 구분한다.
 * F-11. 위험 근거 레이어는 기본 OFF 다.
 *
 * 토글·요약·한계 문구는 leaflet 이 아니라 **React DOM 에 둔다.** 타일이 실패한
 * 상황에서도 근거가 화면에 남아야 하고(8.5.3), 그래야 검사도 받는다.
 */

import { useMemo, useRef, useState } from 'react';

import {
  SENSOR_LAYER_EMPTY,
  SENSOR_LAYER_NOTE,
  SENSOR_LAYER_TITLE,
} from '../contracts/enums';
import type { AssessResponse } from '../contracts/types';
import {
  baseFeatures,
  evidenceCounts,
  evidenceFeatures,
  sensorsInScope,
  type Scope,
} from '../map/features';
import { useFeatureLayer, useLeafletMap } from '../map/leaflet';

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
  // F-11. 기본 OFF. 사용자가 켤 때만 근거 레이어를 올린다.
  const [layerOn, setLayerOn] = useState(false);

  const { lat, lon } = data.location;
  const area = data.risk.area_risk;
  const horizon = data.risk.primary_horizon;

  // memo 의 의존성은 각 함수가 실제로 읽는 값과 같다. 넓게 잡으면 목적지·프로필만
  // 바꿔도 지도를 새로 만들게 되고, 좁게 잡으면 바뀐 값을 안 그린다.
  const center = useMemo(
    () => (lat == null || lon == null ? null : { lat, lon }),
    [lat, lon],
  );
  const base = useMemo(() => baseFeatures(data), [lat, lon, data.route.target]);

  const inScope = useMemo(() => sensorsInScope(data.risk.sensors), [data.risk.sensors]);
  const counts = useMemo(() => evidenceCounts(inScope), [inScope]);
  const evidence = useMemo(
    () => evidenceFeatures(inScope, scope ?? null, horizon),
    [inScope, scope, horizon],
  );

  const { tiles, mapRef } = useLeafletMap(holder, center, base);
  useFeatureLayer(mapRef, evidence, layerOn);

  if (center === null) {
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
          {counts.judged === 0 ? (
            /* 조용히 비우지 않는다 — '임계 미만'과 '판단할 자료가 없다'는 다른 상태다. */
            <p className="map__fallback" role="status">
              {SENSOR_LAYER_EMPTY}
            </p>
          ) : (
            <>
              <p className="map__layer-summary">
                범위 안 센서 {counts.judged}개 중 임계 초과 {counts.over}개
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
