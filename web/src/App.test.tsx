/**
 * 화면 smoke test.
 *
 * **실제 계약 픽스처**(`contracts/fixtures/demo/DS-S1.assess_response.json`)를
 * 그대로 먹여서 렌더링한다. 손으로 만든 가짜 응답을 쓰면 계약이 바뀌었을 때
 * 이 테스트만 조용히 살아남으므로 그렇게 하지 않는다.
 *
 * 확인하는 것은 설계서 12장의 "항상 보여야 할 다섯 항목" + 고지다.
 *   위험 상태 · 현재 위치 · 현재 행동 · 재생 시각 · 119 · 면책 문구
 *
 * jsdom 에는 지도 타일이 없으므로 이 테스트는 **지도가 실패한 상황**과 같다.
 * 그런데도 위 항목이 전부 남아 있어야 한다(설계서 8.5.3).
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from './App';
import { ReassessBar } from './components/ReassessBar';
import fixture from '../../contracts/fixtures/demo/DS-S1.assess_response.json';
import shelterSwitch from '../../contracts/fixtures/demo/DS-S7.assess_response.json';
import noSafePoint from '../../contracts/fixtures/demo/DS-S8.assess_response.json';
import type { AssessResponse } from './contracts/types';

const data = fixture as unknown as AssessResponse;
const s7 = shelterSwitch as unknown as AssessResponse;
const s8 = noSafePoint as unknown as AssessResponse;

describe('모바일 단일 화면', () => {
  it('지도가 없어도 항상 보여야 할 다섯 항목이 남는다', () => {
    render(<App initialData={data} />);

    // 위험 상태
    expect(screen.getByText('위험 등급')).toBeDefined();
    // 현재 위치
    expect(screen.getByText(data.location.label)).toBeDefined();
    // 현재 행동 (MOVE -> '이동')
    expect(screen.getByRole('heading', { name: '이동' })).toBeDefined();
    // 재생 시각 — clock.label 을 그대로 쓴다 (F-12)
    expect(screen.getByText(data.clock.label)).toBeDefined();
    // 119
    const call = screen.getByRole('link', { name: /119/ });
    expect(call.getAttribute('href')).toBe('tel:119');
  });

  it('면책 문구가 항상 보인다 (UI-07)', () => {
    render(<App initialData={data} />);
    expect(screen.getByText(data.notice.disclaimer)).toBeDefined();
  });

  it('경로 제한 문구가 항상 보인다 (RT-02)', () => {
    render(<App initialData={data} />);
    expect(screen.getByText(data.route.limit)).toBeDefined();
    expect(data.route.route_verified).toBe(false);
  });

  it('픽스처 기반임을 화면에 표시한다', () => {
    render(<App initialData={data} />);
    expect(screen.getByText(/시연용 고정 자료로 동작 중/)).toBeDefined();
  });

  it('목적지 선택은 지정 지점 목록 방식이다 (UI-10)', () => {
    render(<App initialData={data} />);
    const select = screen.getByLabelText('가려던 목적지');
    expect(select.tagName).toBe('SELECT');
    // 자유 텍스트 입력을 제공하지 않는다.
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('M-08. 네 시각과 경과시간을 화면에서 볼 수 있다', () => {
    render(<App initialData={data} />);
    for (const label of ['관측 시각', '예측 생성', '예측 대상', '마지막 갱신']) {
      expect(screen.getByText(label)).toBeDefined();
    }
    expect(screen.getByText(/경과 \d+분/)).toBeDefined();
  });

});

describe('수동 재판단 (M-18)', () => {
  const list = {
    scenarios: [
      { id: 'DS-S1', label: 'DS-S1', clock_label: '2022-08-08 11:00 재생', action: 'MOVE' as const },
      { id: 'DS-S7', label: 'DS-S7', clock_label: '2022-08-08 21:40 재생', action: 'EVACUATE' as const },
    ],
    pending: ['DS-S2'],
  };

  it('자동 감지가 아니라는 것을 화면에 적는다', () => {
    render(<ReassessBar list={list} current="DS-S1" onReassess={() => {}} />);
    expect(screen.getByText(/상황 변화를 자동으로 감지하지 않습니다/)).toBeDefined();
  });

  it('버튼을 눌러야 다시 판단한다', () => {
    const picked: string[] = [];
    render(<ReassessBar list={list} current="DS-S1" onReassess={(id) => picked.push(id)} />);

    // 현재 시각 버튼은 눌리지 않는다 — 같은 시각을 다시 부르지 않는다.
    expect(screen.getByRole('button', { name: '2022-08-08 11:00 재생' }).hasAttribute('disabled')).toBe(
      true,
    );

    fireEvent.click(screen.getByRole('button', { name: '2022-08-08 21:40 재생' }));
    expect(picked).toEqual(['DS-S7']);
  });

  it('아직 만들지 않은 시각을 있는 척하지 않는다', () => {
    render(<ReassessBar list={list} current="DS-S1" onReassess={() => {}} />);
    expect(screen.getByText(/아직 만들지 않은 시각/)).toBeDefined();
  });

  it('고를 수 있는 시각이 없으면 아무것도 그리지 않는다', () => {
    const { container } = render(
      <ReassessBar list={null} current="DS-S1" onReassess={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

describe('경로가 실패했을 때 (M-15 · M-16 · M-32)', () => {
  it('갈 곳이 없어도 행동은 대피 그대로다', () => {
    render(<App initialData={s8} />);
    expect(s8.decision.action).toBe('EVACUATE');
    expect(screen.getByRole('heading', { name: '대피' })).toBeDefined();
  });

  it('안전거점이 없으면 119 를 강조하되 119 화면으로 바꾸지 않는다', () => {
    render(<App initialData={s8} />);
    expect(screen.getByText(/안내할 수 있는 대피 경로를 찾지 못했습니다/)).toBeDefined();
    // EMERGENCY 레이아웃으로 승격하지 않는다 — 행동 카드 제목은 여전히 '대피'다.
    expect(screen.queryByRole('heading', { name: '119' })).toBeNull();
  });

  it('후보가 왜 빠졌는지 사유를 남긴다', () => {
    render(<App initialData={s8} />);
    expect(screen.getByText(/대피시설 만석 확인/)).toBeDefined();
    expect(screen.getByText(/대피시설 폐쇄 확인/)).toBeDefined();
  });

  it('대피시설은 안전을 보장하지 않는다고 적는다 (M-23)', () => {
    render(<App initialData={s7} />);
    expect(screen.getByText(/개방·안전 확인 필요/)).toBeDefined();
  });

  it('M-16. 목적지 차단과 안내 가능한 경로 없음의 문구가 서로 다르다', () => {
    const blocked = {
      ...data,
      route: { ...data.route, status: 'DESTINATION_BLOCKED' as const, target: null },
    };
    const { unmount } = render(<App initialData={blocked} />);
    expect(screen.getByText(/다른 목적지를 선택해 주세요/)).toBeDefined();
    expect(screen.queryByText(/안전이 확인되지 않은 경로로 이동하지 마세요/)).toBeNull();
    unmount();

    const noRoute = {
      ...data,
      decision: { ...data.decision, action: 'WAIT' as const, route_postprocess_applied: true },
      route: { ...data.route, status: 'NO_SAFE_ROUTE' as const, no_safe_route: true },
    };
    render(<App initialData={noRoute} />);
    expect(screen.getByText(/안전이 확인되지 않은 경로로 이동하지 마세요/)).toBeDefined();
    expect(screen.queryByText(/다른 목적지를 선택해 주세요/)).toBeNull();
  });
});
