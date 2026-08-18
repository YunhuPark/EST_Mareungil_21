/**
 * 백엔드 호출.
 *
 * 재생 모드는 사전 가공된 픽스처만 쓰므로 여기서 외부 서비스를 부르지 않는다.
 * 유일한 외부 의존은 지도 타일이며, 그건 MapPanel 이 따로 다룬다.
 */

import type { AssessResponse, DestinationList, ScenarioList } from './contracts/types';

const BASE = import.meta.env.VITE_API_BASE ?? '';

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { Accept: 'application/json' } });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`${res.status} ${res.statusText} — ${path}\n${body.slice(0, 400)}`);
  }
  return (await res.json()) as T;
}

export function fetchAssess(
  scenario: string,
  destinationId?: string,
  /** M-37. 순서 조정용이며 안전 기준을 완화하지 않는다. */
  profiles: string[] = [],
  /**
   * M-19. 사용자가 누른 고립 신고. `decide()` 규칙 1 이며 `EMERGENCY` 로 간다.
   *
   * 켜는 방향으로만 보낸다 — 거짓일 때는 아예 싣지 않는다. 신고를 끄는 것은
   * 사용자가 할 수 있는 일이 아니고, 기본값으로 픽스처의 고립 상태를 덮어쓰면
   * `DS-S4` 가 조용히 `EMERGENCY` 를 잃는다.
   */
  trapped = false,
): Promise<AssessResponse> {
  const params = new URLSearchParams({ scenario });
  if (destinationId) params.set('destination', destinationId);
  for (const p of profiles) params.append('profile', p);
  if (trapped) params.set('trapped', 'true');
  return getJson<AssessResponse>(`/api/assess?${params.toString()}`);
}

export function fetchDestinations(): Promise<DestinationList> {
  return getJson<DestinationList>('/api/destinations');
}

/**
 * M-18. 수동 재판단이 고를 수 있는 재생 시각 목록.
 *
 * 자동 감지·자동 재탐색은 MVP 범위 밖이다. 사용자가 버튼을 눌러 재생 시각을
 * 바꿀 때만 다시 판단한다.
 */
export function fetchScenarios(): Promise<ScenarioList> {
  return getJson<ScenarioList>('/api/scenarios');
}
