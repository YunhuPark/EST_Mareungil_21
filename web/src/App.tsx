/**
 * 모바일 단일 화면.
 *
 * UI-01. 로그인·설정·이력·온보딩 화면이 없다.
 * 설계서 12장의 순서를 고정한다:
 *   고정 상단 → 행동 카드 → 이유 → 목적지·경로·지도 → 고정 119 → 면책 문구
 *
 * 항상 보여야 하는 다섯 가지: 위험 상태, 현재 위치, 현재 행동, 재생 시각, 119.
 * 지도가 실패해도 이 다섯은 남는다.
 */

import { useCallback, useEffect, useState } from 'react';

import { fetchAssess, fetchDestinations } from './api';
import { ActionCard } from './components/ActionCard';
import { DestinationPicker } from './components/DestinationPicker';
import { EmergencyBar } from './components/EmergencyBar';
import { MapPanel } from './components/MapPanel';
import { ReasonList } from './components/ReasonList';
import { RouteCard } from './components/RouteCard';
import { TopStatus } from './components/TopStatus';
import type { AssessResponse, DestinationList } from './contracts/types';

const SCENARIO = 'DS-S1';

export function App({ initialData }: { initialData?: AssessResponse } = {}) {
  const [data, setData] = useState<AssessResponse | null>(initialData ?? null);
  const [list, setList] = useState<DestinationList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (destinationId?: string) => {
    setBusy(true);
    try {
      setData(await fetchAssess(SCENARIO, destinationId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    // 테스트에서 initialData 를 주면 네트워크를 부르지 않는다.
    if (!initialData) void load();
    fetchDestinations().then(setList).catch(() => setList(null));
  }, [initialData, load]);

  if (error && !data) {
    return (
      <main className="page page--error">
        <h1>응답을 불러오지 못했습니다</h1>
        <p className="page__hint">
          백엔드가 떠 있는지 확인하세요 — <code>.\make.ps1 api</code>
        </p>
        <pre className="page__error">{error}</pre>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="page page--loading" aria-busy="true">
        <p>불러오는 중…</p>
      </main>
    );
  }

  const { decision, route, clock, location, notice } = data;

  return (
    <div className="page">
      <TopStatus
        riskLevel={decision.service_risk_level}
        location={location}
        clock={clock}
      />

      <main className="content">
        {data.source_kind !== 'LIVE_PIPELINE' && (
          <p className="badge badge--stub">
            시연용 고정 자료로 동작 중입니다 ({data.source_kind ?? 'FIXTURE'}). 예측·판단·경로
            엔진이 아직 붙지 않았습니다.
          </p>
        )}

        <ActionCard
          action={decision.action}
          primaryAction={decision.primary_action}
          postprocessApplied={decision.route_postprocess_applied}
          nextCheckAt={decision.next_check_at}
        />

        <ReasonList reasons={decision.reasons} />

        <DestinationPicker
          list={list}
          selected={decision.user_state.destination}
          onSelect={(id) => void load(id)}
          disabled={busy}
        />

        <RouteCard route={route} />

        <MapPanel data={data} />

        {error && (
          <p className="badge badge--warn" role="alert">
            갱신에 실패해 이전 응답을 표시하고 있습니다.
          </p>
        )}
      </main>

      <EmergencyBar
        urgent={decision.action === 'EMERGENCY'}
        locationText={`${location.label} (재생 시각 ${clock.label})`}
        note={notice.emergency_note}
      />

      {/* UI-07. 어떤 상태에서도 사라지지 않는다. */}
      <footer className="disclaimer" role="contentinfo">
        {notice.disclaimer}
      </footer>
    </div>
  );
}
