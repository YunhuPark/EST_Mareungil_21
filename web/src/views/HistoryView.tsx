/**
 * 과거기록 탭 — 시안 두 번째 화면.
 *
 * 날짜·지역·시각 칩 다음에 그날 무엇이 언제 알려졌는지가 세로로 흐른다.
 * 칩은 **수동 재판단**(M-18)이고, 아래 타임라인은 그 시각까지 공개돼 있던
 * 공식정보(M-36)다. 둘은 같은 것을 시간 축으로 보는 두 부분이라 한 화면에 둔다.
 *
 * 여기서 말하는 '기록'은 사용자의 사용 이력이 아니라 **2022-08-08 사건 기록**이다.
 * 로그인·이력 화면을 만들지 않는다는 UI-01 은 그대로다.
 */

import { OfficialPanel } from '../components/OfficialPanel';
import { ReassessBar } from '../components/ReassessBar';
import type { AssessResponse, ScenarioList } from '../contracts/types';

interface Props {
  data: AssessResponse;
  scenarios: ScenarioList | null;
  current: string;
  onReassess: (scenarioId: string) => void;
  busy: boolean;
}

export function HistoryView({ data, scenarios, current, onReassess, busy }: Props) {
  return (
    <div className="view">
      <ReassessBar
        list={scenarios}
        current={current}
        onReassess={onReassess}
        disabled={busy}
        where={data.location.label}
      />

      <OfficialPanel official={data.official} clockLabel={data.clock.label} />
    </div>
  );
}
