/**
 * 모바일 화면 껍데기.
 *
 * UI-01. 로그인·설정·이력·온보딩 화면이 없다. 아래 네 탭은 **같은 판단 하나를
 * 네 각도로 보는 자리**이며 전부 같은 `AssessResponse` 를 읽는다 — 탭을 바꾼다고
 * 다시 요청하지 않는다.
 *
 * 어느 탭에 있어도 남는 것
 * ------------------------
 * 설계서 12장이 요구하는 다섯 가지 — 위험 상태, 현재 위치, 현재 행동, 재생 시각,
 * 119 — 중 넷은 상단 상태 줄과 하단 고정 묶음이 들고 있고, 현재 행동은 맞춤안내
 * 탭의 행동 카드가 든다. 면책 문구(UI-07)도 탭과 무관하게 남는다.
 * 지도가 실패해도 이것들은 그대로다.
 *
 * M-18. 재판단은 **수동 버튼**이다. 자동 감지·자동 재탐색을 두지 않는다.
 * M-28 / M-35. 경로가 실패해도 119 와 행동 카드는 남는다.
 */

import { useCallback, useEffect, useState } from 'react';

import { fetchAssess, fetchDestinations, fetchScenarios } from './api';
import { AppBar, InfoSheet } from './components/AppBar';
import { EmergencyBar } from './components/EmergencyBar';
import { TabBar, TAB_LABEL, type Tab } from './components/TabBar';
import { GuideView } from './views/GuideView';
import { HistoryView } from './views/HistoryView';
import { RouteView } from './views/RouteView';
import { ShelterView } from './views/ShelterView';
import type {
  AssessResponse,
  DestinationList,
  Profile,
  ScenarioList,
} from './contracts/types';

const DEFAULT_SCENARIO = 'DS-S1';

/** 처음 열었을 때 보이는 탭. 시안에서 활성 상태로 그려진 화면이다. */
const DEFAULT_TAB: Tab = 'guide';

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
  const [tab, setTab] = useState<Tab>(DEFAULT_TAB);
  const [infoOpen, setInfoOpen] = useState(false);

  // M-37. 프로필은 화면 상태로 들고 있다가 요청에 실어 보낸다. UI 가 프로필로
  // 순서를 다시 매기지 않는다 — 정책 재구현 금지(CLAUDE.md 10절).
  const [profiles, setProfiles] = useState<Profile[]>([]);

  /**
   * M-19. 고립 신고. **지금 보고 있는 재생 시각에 매인 상태다.**
   *
   * 같은 상황을 다시 보는 요청 — 목적지 변경·프로필 변경 — 에는 함께 실어
   * 보낸다. 싣지 않으면 다음 요청에서 조용히 `EMERGENCY` 가 풀리는데, 그건
   * 사용자가 취소한 것이 아니라 화면이 신고를 잊은 것이다.
   *
   * 재판단(M-18)으로 **시각을 바꾸면 해제한다.** 그건 다른 상황으로 넘어가는
   * 것이라 앞 시각의 신고를 끌고 갈 근거가 없다.
   *
   * 판정은 서버가 한다 — 여기서 `action` 을 바꾸지 않는다(정책 재구현 금지).
   */
  const [trapped, setTrapped] = useState(false);

  const load = useCallback(
    async (
      scenarioId: string,
      destinationId?: string,
      picked: Profile[] = [],
      isTrapped = false,
    ) => {
      setBusy(true);

      try {
        setData(await fetchAssess(scenarioId, destinationId, picked, isTrapped));
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
    <div className="app">
      <AppBar data={data} infoOpen={infoOpen} onToggleInfo={() => setInfoOpen((v) => !v)} />

      {infoOpen && <InfoSheet data={data} />}

      <main
        className="app__body"
        id={`panel-${tab}`}
        role="tabpanel"
        aria-labelledby={`tab-${tab}`}
        aria-label={TAB_LABEL[tab]}
      >
        {tab === 'guide' && <GuideView data={data} scope={list?.scope ?? null} />}

        {tab === 'route' && (
          <RouteView
            data={data}
            list={list}
            selected={decision.user_state.destination}
            profiles={profiles}
            busy={busy}
            onSelectDestination={(id) => void load(scenario, id, profiles, trapped)}
            onChangeProfiles={(picked) => {
              setProfiles(picked);
              void load(scenario, decision.user_state.destination?.id, picked, trapped);
            }}
          />
        )}

        {tab === 'history' && (
          <HistoryView
            data={data}
            scenarios={scenarios}
            current={scenario}
            busy={busy}
            onReassess={(id) => {
              // 재생 시각을 바꾸는 것은 **다른 상황으로 넘어가는 것**이다. 앞
              // 시각에서 한 신고를 끌고 가면 그 시나리오가 상정하지 않은 판정이
              // 나온다 — DS-S1 을 골랐는데 EMERGENCY 가 뜨는 식이다.
              // 목적지·프로필 변경과 다른 점이 여기다. 그쪽은 같은 상황을 다시
              // 보는 것이라 신고가 남는다.
              setTrapped(false);
              void load(id, decision.user_state.destination?.id, profiles, false);
            }}
          />
        )}

        {tab === 'shelter' && <ShelterView data={data} onOpenMap={() => setTab('route')} />}

        {error && (
          <p className="badge badge--warn" role="alert">
            갱신에 실패해 이전 응답을 표시하고 있습니다.
          </p>
        )}
      </main>

      <div className="dock">
        <EmergencyBar
          urgent={decision.action === 'EMERGENCY'}
          emphasis={emphasize119}
          locationText={`${location.label} (재생 시각 ${clock.label})`}
          note={notice.emergency_note}
          /*
            M-19. 이미 고립으로 판정된 화면에서는 버튼을 내린다 — 누를 것이 없다.
            `trapped` 상태가 아니라 응답의 `user_state.trapped` 를 본다. `DS-S4`
            처럼 픽스처가 이미 고립인 경우도 같이 걸러야 하기 때문이다.
          */
          onTrapped={
            decision.user_state.trapped
              ? undefined
              : () => {
                  setTrapped(true);
                  void load(
                    scenario,
                    decision.user_state.destination?.id,
                    profiles,
                    true,
                  );
                }
          }
          trappedBusy={busy}
        />

        {/* UI-07. 어떤 상태에서도, 어느 탭에서도 사라지지 않는다. */}
        <footer className="disclaimer" role="contentinfo">
          {notice.disclaimer}
        </footer>

        <TabBar current={tab} onChange={setTab} />
      </div>
    </div>
  );
}
