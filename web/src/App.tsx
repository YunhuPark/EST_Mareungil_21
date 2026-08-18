/**
 * 모바일 단일 화면.
 *
 * UI-01. 로그인·설정·이력·온보딩 화면이 없다.
 * 설계서 12장의 순서를 고정한다:
 *   고정 상단 → 행동 카드 → 이유 → 목적지·경로·지도 → 고정 119 → 면책 문구
 *
 * 항상 보여야 하는 다섯 가지: 위험 상태, 현재 위치, 현재 행동, 재생 시각, 119.
 * 지도가 실패해도 이 다섯은 남는다.
 *
 * M-18. 재판단은 **수동 버튼**이다. 자동 감지·자동 재탐색을 두지 않는다.
 * M-28 / M-35. 경로가 실패해도 119 와 행동 카드는 남는다 — 아래에서 경로 카드만
 *       빠지고 나머지는 그대로다.
 */

import { useCallback, useEffect, useState } from 'react';

import { fetchAssess, fetchDestinations, fetchScenarios } from './api';
import { ActionCard } from './components/ActionCard';
import { DestinationPicker } from './components/DestinationPicker';
import { EmergencyBar } from './components/EmergencyBar';
import { MapPanel } from './components/MapPanel';
import { OfficialPanel } from './components/OfficialPanel';
import { ProfilePicker } from './components/ProfilePicker';
import { ReasonList } from './components/ReasonList';
import { ReassessBar } from './components/ReassessBar';
import { RouteCard } from './components/RouteCard';
import { TopStatus } from './components/TopStatus';
import type {
  AssessResponse,
  DestinationList,
  Profile,
  ScenarioList,
} from './contracts/types';

const DEFAULT_SCENARIO = 'DS-S1';

/** M-15. `EVACUATE` 인데 갈 곳·길·근거가 없는 상태. 119 를 강조한다. */
const EVACUATE_ROUTE_FAILURE: AssessResponse['route']['status'][] = [
  'NO_SAFE_POINT',
  'NO_SAFE_ROUTE',
  'DATA_UNAVAILABLE',
];

export function App({ initialData }: { initialData?: AssessResponse } = {}) {
  const [data, setData] = useState<AssessResponse | null>(initialData ?? null);
  const [list, setList] = useState<DestinationList | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioList | null>(null);
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // M-37. 프로필은 화면 상태로 들고 있다가 요청에 실어 보낸다. UI 가 프로필로
  // 순서를 다시 매기지 않는다 — 정책 재구현 금지(CLAUDE.md 10절).
  const [profiles, setProfiles] = useState<Profile[]>([]);

  const load = useCallback(
    async (scenarioId: string, destinationId?: string, picked: Profile[] = []) => {
      setBusy(true);

      try {
        setData(await fetchAssess(scenarioId, destinationId, picked));
        setScenario(scenarioId);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  useEffect(() => {
    // 테스트에서 initialData 를 주면 네트워크를 부르지 않는다.
    if (!initialData) void load(DEFAULT_SCENARIO);

    fetchDestinations()
      .then(setList)
      .catch(() => setList(null));

    fetchScenarios()
      .then(setScenarios)
      .catch(() => setScenarios(null));
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

  // M-15. 강조는 EMERGENCY 승격이 아니다 — 행동은 여전히 EVACUATE 다.
  const emphasize119 =
    decision.primary_action === 'EVACUATE' &&
    EVACUATE_ROUTE_FAILURE.includes(route.status);

  return (
    <div className="page">
      <TopStatus
        riskLevel={decision.service_risk_level}
        location={location}
        clock={clock}
      />

      <main className="content">
        {data.source_kind === 'LIVE_PIPELINE' ? (
          <p className="badge badge--live">
            LIVE
          </p>
        ) : (
          <p className="badge badge--stub">
            {data.source_kind ?? 'FIXTURE'} — 재현 가능한 시연·검증용 고정 데이터를 사용하고 있습니다.
          </p>
        )}

        <ActionCard
          action={decision.action}
          primaryAction={decision.primary_action}
          postprocessApplied={decision.route_postprocess_applied}
          nextCheckAt={decision.next_check_at}
        />

        <ReasonList reasons={decision.reasons} />

        {/*
          M-24 / M-36. 공식정보를 어떤 상태로 받았는지, 그리고 이 재생 시각에
          무엇이 공개돼 있었는지를 숨기지 않는다. 시각 필터는 서버가 건다.
        */}
        <OfficialPanel
          official={data.official}
          clockLabel={clock.label}
        />

        <ReassessBar
          list={scenarios}
          current={scenario}
          onReassess={(id) =>
            void load(
              id,
              decision.user_state.destination?.id,
              profiles,
            )
          }
          disabled={busy}
        />

        <DestinationPicker
          list={list}
          selected={decision.user_state.destination}
          onSelect={(id) =>
            void load(
              scenario,
              id,
              profiles,
            )
          }
          disabled={busy}
        />

        <ProfilePicker
          selected={profiles}
          applied={route.profile_applied ?? []}
          onChange={(picked) => {
            setProfiles(picked);

            void load(
              scenario,
              decision.user_state.destination?.id,
              picked,
            );
          }}
          disabled={busy}
        />

        {/*
          M-16 / M-18. 경로가 실패하면 카드를 지우지 않고 **안내만 바꾼다.**
          카드를 통째로 감추면 "왜 안내가 없는지"가 화면에서 사라지고,
          목적지 차단과 안내 가능한 경로 없음이 다시 같은 상태로 보인다.
          도달 대상·후보 목록은 RouteCard 가 실패 상태에서 스스로 감춘다.
        */}
        <RouteCard route={route} />

        <MapPanel data={data} />

        {error && (
          <p
            className="badge badge--warn"
            role="alert"
          >
            갱신에 실패해 이전 응답을 표시하고 있습니다.
          </p>
        )}
      </main>

      <EmergencyBar
        urgent={decision.action === 'EMERGENCY'}
        emphasis={emphasize119}
        locationText={`${location.label} (재생 시각 ${clock.label})`}
        note={notice.emergency_note}
      />

      {/* UI-07. 어떤 상태에서도 사라지지 않는다. */}
      <footer
        className="disclaimer"
        role="contentinfo"
      >
        {notice.disclaimer}
      </footer>
    </div>
  );
}
