/**
 * 지도 위험 근거 레이어 (F-11).
 *
 * **실제 계약 픽스처**를 그대로 먹인다. 손으로 만든 응답을 쓰면 계약이 바뀌었을
 * 때 이 테스트만 조용히 살아남는다.
 *
 * 렌더된 개수를 이 파일에서 다시 계산하지 않고 **서버가 쓴 `area_risk.basis`
 * 문장과 대조한다.** 컴포넌트 로직을 테스트에 옮겨 적으면 둘이 같이 틀려도
 * 통과하기 때문이다. 화면의 숫자가 등급 근거 문장과 같은지가 확인하려는 것의
 * 전부다 — 앞선 시도가 되돌려진 이유가 화면이 근거보다 많이 주장한 것이었다.
 *
 * jsdom 에는 지도 타일이 없다. 그래서 여기서 확인하는 것은 leaflet 도형이 아니라
 * **타일이 실패해도 남아야 하는 DOM**(설계서 8.5.3)이다.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MapPanel } from './MapPanel';
import {
  SENSOR_LAYER_EMPTY,
  SENSOR_LAYER_NOTE,
  SENSOR_LAYER_TITLE,
} from '../contracts/enums';
import calm from '../../../contracts/fixtures/demo/DS-S1.assess_response.json';
import rising from '../../../contracts/fixtures/demo/DS-S6.assess_response.json';
import peak from '../../../contracts/fixtures/demo/DS-S4.assess_response.json';
import noData from '../../../contracts/fixtures/risk_E1_no_data.json';
import type { AssessResponse, RiskAssessment } from '../contracts/types';

const s1 = calm as unknown as AssessResponse;
const s6 = rising as unknown as AssessResponse;
const s4 = peak as unknown as AssessResponse;

/** 재생 범위. 실제 응답에서는 `/api/destinations` 가 준다. */
const scope = {
  center_label: '강남역',
  center_lat: 37.4979,
  center_lon: 127.0276,
  radius_m: 1000,
};

/**
 * `basis` 에서 서버가 쓴 분자·분모를 꺼낸다.
 *
 * 이 문장은 `mareungil/area_risk.py` 가 만들고 픽스처에 실려 온다. 화면이
 * 보여주는 개수는 여기서 나온 수와 같아야 한다.
 */
function ratioFromBasis(basis: string): { over: number; judged: number } {
  const found = basis.match(/비율 (\d+)\/(\d+)\./);
  if (!found) throw new Error(`basis 에서 비율을 찾지 못했다: ${basis}`);
  return { over: Number(found[1]), judged: Number(found[2]) };
}

/**
 * `SENSOR_LAYER_TITLE` 은 `t+30분...` 이라 정규식 특수문자 `+` 를 품고 있다.
 * 그대로 `RegExp` 에 넣으면 `t+` 가 수량자가 되어 이름이 영영 안 잡힌다.
 */
const TITLE_RE = new RegExp(SENSOR_LAYER_TITLE.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));

function openLayer() {
  fireEvent.click(screen.getByRole('checkbox', { name: TITLE_RE }));
}

function layerText(): string {
  return screen.getByRole('group', { name: SENSOR_LAYER_TITLE }).textContent ?? '';
}

describe('위험 근거 레이어', () => {
  it('F-11. 기본으로 꺼져 있다', () => {
    render(<MapPanel data={s1} scope={scope} />);

    // 토글은 보이지만 레이어 내용은 없다.
    expect(screen.getByRole('checkbox', { name: TITLE_RE })).toBeDefined();
    expect(screen.queryByRole('group', { name: SENSOR_LAYER_TITLE })).toBeNull();
  });

  it.each([
    ['DS-S1 평온', s1],
    ['DS-S6 상승', s6],
    ['DS-S4 피크', s4],
  ])('%s — 화면의 개수가 area_risk.basis 와 같다', (_label, data) => {
    const { over, judged } = ratioFromBasis(data.risk.area_risk.basis);

    render(<MapPanel data={data} scope={scope} />);
    openLayer();

    expect(layerText()).toContain(`범위 안 센서 ${judged}개 중 임계 초과 ${over}개`);
  });

  it('등급 근거 문장과 한계 문구를 함께 싣는다', () => {
    render(<MapPanel data={s4} scope={scope} />);
    openLayer();

    const text = layerText();
    // 서버가 만든 문장을 화면이 다시 조립하지 않는다.
    expect(text).toContain(s4.risk.area_risk.basis);
    // AI-08. 하수 고수위를 도로 침수로 단정하지 않는다.
    expect(text).toContain(SENSOR_LAYER_NOTE);
  });

  it('좌표를 모르는 센서는 세지 않는다', () => {
    // 픽스처에 실제로 그런 센서가 있어야 이 검사가 의미를 가진다.
    const unmatched = s1.risk.sensors.filter((s) => s.location.lat == null);
    expect(unmatched.length).toBeGreaterThan(0);
    // 좌표가 없으면 범위 안이라고 말하지 않는다 — 서버가 그렇게 정한다.
    expect(unmatched.every((s) => s.in_area_scope === false)).toBe(true);

    const { judged } = ratioFromBasis(s1.risk.area_risk.basis);

    render(<MapPanel data={s1} scope={scope} />);
    openLayer();

    // 분모가 전체 센서 수가 아니다. 좌표 미상은 빠져 있다.
    expect(judged).toBeLessThan(s1.risk.sensors.length);
    expect(layerText()).toContain(`범위 안 센서 ${judged}개`);
  });

  it('판단할 센서가 없으면 조용히 비우지 않고 그 사실을 말한다', () => {
    // 무데이터 국면은 assess_response 픽스처가 없으므로 실제 risk 픽스처를 얹는다.
    const empty: AssessResponse = {
      ...s1,
      risk: noData as unknown as RiskAssessment,
    };
    expect(empty.risk.sensors).toHaveLength(0);

    render(<MapPanel data={empty} scope={scope} />);
    openLayer();

    const text = layerText();
    expect(text).toContain(SENSOR_LAYER_EMPTY);
    // '임계 초과 0개' 라고 말하지 않는다 — 없는 판단을 0 으로 표현하지 않는다.
    expect(text).not.toContain('임계 초과');
  });

  it('범위를 못 받아도 레이어는 동작한다', () => {
    // scope 가 null 이면 원을 그리지 않을 뿐, 센서 근거는 그대로 보인다.
    const { over, judged } = ratioFromBasis(s4.risk.area_risk.basis);

    render(<MapPanel data={s4} scope={null} />);
    openLayer();

    expect(layerText()).toContain(`범위 안 센서 ${judged}개 중 임계 초과 ${over}개`);
  });

  it('다시 누르면 꺼진다', () => {
    render(<MapPanel data={s4} scope={scope} />);
    openLayer();
    expect(screen.queryByRole('group', { name: SENSOR_LAYER_TITLE })).not.toBeNull();

    openLayer();
    expect(screen.queryByRole('group', { name: SENSOR_LAYER_TITLE })).toBeNull();
  });
});
