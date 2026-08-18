/**
 * M-19. 고립 신고가 **어느 요청에 실리고 어느 요청에 안 실리는지**.
 *
 * 이 파일이 지키는 것은 화면 모양이 아니라 신고의 수명이다.
 *
 * - 같은 상황을 다시 보는 요청(목적지·프로필 변경)에는 **실린다.** 안 실으면
 *   다음 요청에서 조용히 `EMERGENCY` 가 풀리는데, 사용자는 취소한 적이 없다.
 * - 재생 시각을 바꾸면(M-18) **안 실린다.** 다른 상황으로 넘어가는 것이라
 *   앞 시각의 신고를 끌고 갈 근거가 없다. `DS-S1` 을 골랐는데 `EMERGENCY` 가
 *   뜨면 그 시나리오가 상정하지 않은 화면이다.
 *
 * 판정은 서버가 한다. 여기서 보는 것은 **화면이 무엇을 보냈는가**뿐이다 —
 * 화면이 `action` 을 직접 바꾸면 그건 정책 재구현이다(CLAUDE.md 10절).
 *
 * `api` 를 통째로 대역으로 바꾸므로 `App.test.tsx` 와 파일을 나눈다. 한 파일에
 * 두면 그쪽 렌더링 검사까지 대역 위에서 돌게 된다.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import fixture from '../../contracts/fixtures/demo/DS-S1.assess_response.json';
import type { AssessResponse } from './contracts/types';

const data = fixture as unknown as AssessResponse;

/** 화면이 보낸 인자를 그대로 모은다. */
const spy = vi.hoisted(() => ({
  calls: [] as { scenario: string; trapped: boolean }[],
}));

vi.mock('./api', async () => {
  const body = (
    await import('../../contracts/fixtures/demo/DS-S1.assess_response.json')
  ).default;

  return {
    fetchAssess: (
      scenario: string,
      _destinationId?: string,
      _profiles: string[] = [],
      trapped = false,
    ) => {
      spy.calls.push({ scenario, trapped });
      return Promise.resolve(body);
    },
    fetchDestinations: () => Promise.resolve({ status: 'DRAFT', scope: {}, points: [], note: '' }),
    fetchScenarios: () =>
      Promise.resolve({
        scenarios: [
          {
            id: 'DS-S1',
            label: 'DS-S1',
            clock_label: '2022-08-08 11:00 재생',
            action: 'MOVE',
          },
          {
            id: 'DS-S7',
            label: 'DS-S7',
            clock_label: '2022-08-08 21:40 재생',
            action: 'EVACUATE',
          },
        ],
        pending: [],
      }),
  };
});

const { App } = await import('./App');

describe('고립 신고의 수명 (M-19)', () => {
  beforeEach(() => {
    spy.calls.length = 0;
  });

  it('신고를 누르면 trapped 를 실어 다시 요청한다', async () => {
    render(<App initialData={data} />);

    fireEvent.click(screen.getByRole('button', { name: '고립 신고' }));

    await waitFor(() => expect(spy.calls.length).toBe(1));
    expect(spy.calls[0]).toEqual({ scenario: 'DS-S1', trapped: true });
  });

  it('재생 시각을 바꾸면 신고를 함께 보내지 않는다 (M-18)', async () => {
    render(<App initialData={data} />);

    fireEvent.click(screen.getByRole('button', { name: '고립 신고' }));
    await waitFor(() => expect(spy.calls.length).toBe(1));

    // 다른 시각으로 넘어간다. 앞 시각의 신고는 여기 따라오지 않는다.
    const other = await screen.findByRole('button', { name: '2022-08-08 21:40 재생' });
    fireEvent.click(other);

    await waitFor(() => expect(spy.calls.length).toBe(2));
    expect(spy.calls[1]).toEqual({ scenario: 'DS-S7', trapped: false });
  });
});
