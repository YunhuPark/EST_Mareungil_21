/**
 * 백엔드 호출.
 *
 * 재생 모드는 사전 가공된 픽스처만 쓰므로 여기서 외부 서비스를 부르지 않는다.
 * 유일한 외부 의존은 지도 타일이며, 그건 MapPanel 이 따로 다룬다.
 */

import type { AssessResponse, DestinationList } from './contracts/types';

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
