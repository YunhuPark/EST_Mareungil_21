/**
 * 하단 탭 — 시안의 네 칸.
 *
 * 탭 이름에 대하여
 * ----------------
 * 시안 첫 칸의 이름은 길찾기 계열 낱말이었다. 그 계열은 화면 문구에서 막혀
 * 있다(CLAUDE.md 5절 · `tests/test_forbidden_wording.py`) — 우리가 만드는 것은
 * 새 길을 만들어 따라가게 하는 기능이 아니라 **공식 대피경로 후보를 상대
 * 비교해 보여주는 화면**이고, 이름이 그보다 많이 주장하면 안 된다. 그래서
 * `경로안내` 로 적는다.
 *
 * UI-01 과의 관계
 * ---------------
 * 로그인·설정·이력·온보딩 화면은 여전히 없다. 네 탭은 **같은 한 번의 판단을
 * 네 각도로 보는 자리**이며 모두 같은 `AssessResponse` 하나를 읽는다.
 */

import { CompassIcon, HistoryIcon, PeopleIcon, PinIcon } from './icons';

export const TABS = ['route', 'history', 'guide', 'shelter'] as const;
export type Tab = (typeof TABS)[number];

export const TAB_LABEL: Record<Tab, string> = {
  route: '경로안내',
  history: '과거기록',
  guide: '맞춤안내',
  shelter: '대피시설',
};

const TAB_ICON: Record<Tab, (p: { size?: number }) => React.ReactElement> = {
  route: CompassIcon,
  history: HistoryIcon,
  guide: PeopleIcon,
  shelter: PinIcon,
};

interface Props {
  current: Tab;
  onChange: (tab: Tab) => void;
}

export function TabBar({ current, onChange }: Props) {
  return (
    <nav className="tabbar" role="tablist" aria-label="화면 전환">
      {TABS.map((tab) => {
        const Icon = TAB_ICON[tab];
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            id={`tab-${tab}`}
            className="tabbar__item"
            aria-selected={tab === current}
            aria-controls={`panel-${tab}`}
            onClick={() => onChange(tab)}
          >
            <Icon size={22} />
            {TAB_LABEL[tab]}
          </button>
        );
      })}
    </nav>
  );
}
