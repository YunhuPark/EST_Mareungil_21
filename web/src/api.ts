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

export function fetchAssess(scenario: string, destinationId?: string): Promise<AssessResponse> {
  const params = new URLSearchParams({ scenario });
  if (destinationId) params.set('destination', destinationId);
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
