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

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from './App';
import fixture from '../../contracts/fixtures/demo/DS-S1.assess_response.json';
import type { AssessResponse } from './contracts/types';

const data = fixture as unknown as AssessResponse;

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
});
