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
 * 화면이 네 탭으로 나뉜 뒤로
 * -------------------------
 * 카드가 어느 탭에 있는지는 바뀌었지만 **무엇이 화면에 있어야 하는가는 그대로**다.
 * 그래서 아래 검사들은 지우지 않고 해당 탭으로 옮겨 눌러본다. 그리고 위 다섯
 * 항목은 탭과 무관하게 남아야 하므로, 네 탭 전부에서 남는지 따로 본다.
 *
 * jsdom 에는 지도 타일이 없으므로 이 테스트는 **지도가 실패한 상황**과 같다.
 * 그런데도 위 항목이 전부 남아 있어야 한다(설계서 8.5.3).
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from './App';
import { ProfilePicker } from './components/ProfilePicker';
import { ReassessBar } from './components/ReassessBar';
import { CLOSURE_MODE_LABEL } from './contracts/enums';
import fixture from '../../contracts/fixtures/demo/DS-S1.assess_response.json';
import blockedDestination from '../../contracts/fixtures/demo/DS-S6.assess_response.json';
import trapped from '../../contracts/fixtures/demo/DS-S4.assess_response.json';
import shelterSwitch from '../../contracts/fixtures/demo/DS-S7.assess_response.json';
import noSafePoint from '../../contracts/fixtures/demo/DS-S8.assess_response.json';
import type { AssessResponse } from './contracts/types';

const data = fixture as unknown as AssessResponse;
const destinationBlocked = blockedDestination as unknown as AssessResponse;
const trappedFixture = trapped as unknown as AssessResponse;
const s7 = shelterSwitch as unknown as AssessResponse;
const s8 = noSafePoint as unknown as AssessResponse;

/** 탭 전환. 탭을 바꿔도 다시 요청하지 않는다 — 같은 응답을 다른 각도로 본다. */
function goTab(name: '경로안내' | '과거기록' | '맞춤안내' | '대피시설') {
  fireEvent.click(screen.getByRole('tab', { name }));
}

describe('모바일 화면', () => {
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

  /**
   * UI-02 / UI-04 / UI-07. 탭이 생기면서 새로 생긴 위험은 **탭을 옮기면 위험
   * 표시가 사라지는 것**이다. 상단 상태 줄과 하단 고정 묶음이 그것을 막는데,
   * 막고 있는지는 눌러보지 않으면 알 수 없다.
   */
  it.each(['경로안내', '과거기록', '맞춤안내', '대피시설'] as const)(
    '%s 탭에서도 위험 등급·현재 위치·재생 시각·119·면책 문구가 남는다',
    (tab) => {
      render(<App initialData={data} />);
      goTab(tab);

      expect(screen.getByText('위험 등급')).toBeDefined();
      expect(screen.getByText(data.location.label)).toBeDefined();
      expect(screen.getByText(data.clock.label)).toBeDefined();
      expect(screen.getByRole('link', { name: /119/ }).getAttribute('href')).toBe('tel:119');
      expect(screen.getByText(data.notice.disclaimer)).toBeDefined();
    },
  );

  it('면책 문구가 항상 보인다 (UI-07)', () => {
    render(<App initialData={data} />);
    expect(screen.getByText(data.notice.disclaimer)).toBeDefined();
  });

  it('정보 버튼은 사용자용 데이터 출처와 한계만 보여준다', () => {
    render(<App initialData={data} />);

    const info = screen.getByRole('button', { name: '데이터 출처와 한계' });
    expect(info.getAttribute('aria-expanded')).toBe('false');
    expect(screen.queryByRole('heading', { name: '데이터 출처와 한계' })).toBeNull();

    fireEvent.click(info);

    expect(info.getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByRole('heading', { name: '데이터 출처와 한계' })).toBeDefined();
    expect(screen.getByText(/시연용 고정 데이터/)).toBeDefined();
    expect(screen.getByText('공식정보 출처 보기')).toBeDefined();

    // 계약·정책·모델 판은 API와 개발 문서에 남기고 일반 사용자 화면에서는 뺀다.
    expect(screen.queryByText(data.decision.policy_version)).toBeNull();
    expect(screen.queryByText(`${data.risk.model.name} ${data.risk.model.version}`)).toBeNull();
    expect(screen.queryByText(/설정 화면은 이 MVP/)).toBeNull();
  });

  it('경로 제한 문구가 항상 보인다 (RT-02)', () => {
    render(<App initialData={data} />);

    // 경로를 말하는 두 탭 어디에서도 제한 문구가 빠지지 않는다.
    goTab('경로안내');
    expect(screen.getByText(data.route.limit)).toBeDefined();

    goTab('대피시설');
    expect(screen.getByText(data.route.limit)).toBeDefined();

    expect(data.route.route_verified).toBe(false);
  });

  it('픽스처 기반임을 화면에 표시한다', () => {
    render(<App initialData={data} />);
    expect(screen.getByText(/재현 가능한 시연·검증용 고정 데이터/)).toBeDefined();
  });

  /**
   * 배지는 `source_kind` 를 **읽어서** 말해야 한다. 문자열로 굳히면 안 된다.
   *
   * 계약의 enum 은 `FIXTURE` · `STUB` · `LIVE_PIPELINE` 셋이다. 지금 API 는
   * `STUB` 을 내보내지 않지만, 굳혀 두면 내보내는 날 배지가 `FIXTURE` 라고
   * 거짓말한다. 화면이 사실을 말하는지가 이 프로젝트의 한 줄이므로 굳히지 않는다.
   *
   * 이 테스트가 없어서 같은 하드코딩이 두 번 들어왔다 — 94b7bb7 이 넣었고
   * 6092b0d(PR #11)가 뺐고 e1483cd(PR #18)가 다시 넣었다. 세 번째를 막는 것은
   * 테스트뿐이다.
   */
  it('배지는 source_kind 를 그대로 말한다 (STUB)', () => {
    const stubbed: AssessResponse = { ...data, source_kind: 'STUB' };
    render(<App initialData={stubbed} />);
    expect(screen.getByText(/^STUB —/)).toBeDefined();
  });

  it('배지는 LIVE_PIPELINE 이면 LIVE 로 바뀐다', () => {
    const live: AssessResponse = { ...data, source_kind: 'LIVE_PIPELINE' };
    render(<App initialData={live} />);
    expect(screen.getByText('LIVE')).toBeDefined();
    // 1단이라도 픽스처 문구가 남으면 화면이 두 가지를 동시에 말한다.
    expect(screen.queryByText(/재현 가능한 시연·검증용 고정 데이터/)).toBeNull();
  });

  /**
   * M-19. 고립 신고 버튼.
   *
   * `initialData` 를 주면 App 이 네트워크를 부르지 않으므로 여기서 보는 것은
   * **버튼이 실제로 화면에 있는지**다. 이 검사가 없으면 `onTrapped` 를 넘기지
   * 않아도 아무것도 빨개지지 않고, 버튼이 영영 렌더링되지 않은 채로 "고립 신고
   * 넣었다"가 된다 — 실제로 PR #22 가 그 상태였다.
   *
   * 누른 뒤의 판정은 서버가 한다. 화면이 `EMERGENCY` 로 바꾸지 않는다.
   */
  it('고립 신고 버튼이 화면에 있고, 119 전화와 분리돼 있다 (M-19)', () => {
    render(<App initialData={data} />);

    const report = screen.getByRole('button', { name: '고립 신고' });
    // 전화가 아니라 상태 입력이다. 링크였다면 누르는 순간 전화 앱이 열린다.
    expect(report.tagName).toBe('BUTTON');
    expect(report.getAttribute('href')).toBeNull();

    // 실제 통화는 여전히 이 하나뿐이다.
    expect(screen.getByRole('link', { name: /119/ }).getAttribute('href')).toBe('tel:119');
  });

  it('이미 고립으로 판정된 화면에는 신고 버튼을 두지 않는다 (M-19)', () => {
    // DS-S4 는 픽스처가 이미 trapped 다. 누를 것이 없다.
    render(<App initialData={trappedFixture} />);

    expect(screen.queryByRole('button', { name: '고립 신고' })).toBeNull();
    expect(screen.getByRole('link', { name: /119/ })).toBeDefined();
  });

  it('목적지 선택은 지정 지점 목록 방식이다 (UI-10)', () => {
    render(<App initialData={data} />);
    goTab('경로안내');

    const select = screen.getByLabelText('가려던 목적지');
    expect(select.tagName).toBe('SELECT');
    // 자유 텍스트 입력을 제공하지 않는다.
    expect(screen.queryByRole('textbox')).toBeNull();
  });

  it('M-08. 네 시각과 경과시간을 화면에서 볼 수 있다', () => {
    render(<App initialData={data} />);
    for (const label of ['관측 시각', '예측 생성', '예측 대상', '마지막 갱신']) {
      expect(screen.getByText(label)).toBeDefined();
    }
    expect(screen.getByText(/경과 \d+분/)).toBeDefined();
  });
});

describe('수동 재판단 (M-18)', () => {
  const list = {
    scenarios: [
      { id: 'DS-S1', label: 'DS-S1', clock_label: '2022-08-08 11:00 재생', action: 'MOVE' as const },
      { id: 'DS-S7', label: 'DS-S7', clock_label: '2022-08-08 21:40 재생', action: 'EVACUATE' as const },
    ],
    pending: ['DS-S2'],
  };

  it('자동 감지가 아니라는 것을 화면에 적는다', () => {
    render(<ReassessBar list={list} current="DS-S1" onReassess={() => {}} />);
    expect(screen.getByText(/상황 변화를 자동으로 감지하지 않습니다/)).toBeDefined();
  });

  it('버튼을 눌러야 다시 판단한다', () => {
    const picked: string[] = [];
    render(<ReassessBar list={list} current="DS-S1" onReassess={(id) => picked.push(id)} />);

    // 현재 시각 버튼은 눌리지 않는다 — 같은 시각을 다시 부르지 않는다.
    expect(screen.getByRole('button', { name: '2022-08-08 11:00 재생' }).hasAttribute('disabled')).toBe(
      true,
    );

    fireEvent.click(screen.getByRole('button', { name: '2022-08-08 21:40 재생' }));
    expect(picked).toEqual(['DS-S7']);
  });

  /**
   * 칩에 보이는 글자는 `21:40` 이지만 **버튼의 이름은 서버가 준 재생 시각
   * 문자열 통째로**여야 한다(F-12). 이름에서 날짜가 빠지면 어느 날을 재생하는지
   * 화면이 말하지 못하고, 그걸 눈으로 잡을 방법이 없다.
   */
  it('칩은 시각만 보여주되 이름은 서버의 clock_label 그대로다 (F-12)', () => {
    render(<ReassessBar list={list} current="DS-S1" onReassess={() => {}} />);

    const button = screen.getByRole('button', { name: '2022-08-08 21:40 재생' });
    expect(button.textContent).toBe('21:40');
    // 날짜는 카드 머리에서 한 번 말한다.
    expect(screen.getByText('2022-08-08')).toBeDefined();
  });

  /**
   * M-32. `DS-S4`·`DS-S7`·`DS-S8` 은 `clock_label` 이 셋 다
   * `2022-08-08 21:40 재생` 이다. 시설 상태 시계열이 없어 시간 흐름이 아니라
   * 상태 차이로 보여주기 때문인데, 그래서 **시각만 적으면 버튼이 구분되지
   * 않는다.** 상황 설명이 버튼마다 붙어야 고를 수 있다.
   */
  it('같은 재생 시각이어도 버튼마다 어떤 상황인지 적는다 (M-32)', () => {
    const sameClock = {
      scenarios: [
        { id: 'DS-S7', label: 'DS-S7', clock_label: '2022-08-08 21:40 재생', action: 'EVACUATE' as const },
        { id: 'DS-S8', label: 'DS-S8', clock_label: '2022-08-08 21:40 재생', action: 'EVACUATE' as const },
      ],
      pending: [],
    };
    render(<ReassessBar list={sameClock} current="DS-S7" onReassess={() => {}} />);

    expect(screen.getByText(/1순위 대피시설이 만석/)).toBeDefined();
    expect(screen.getByText(/남은 곳이 없는 상태/)).toBeDefined();

    // 설명은 버튼 이름이 아니라 설명으로 붙는다 — 이름은 여전히 재생 시각이다.
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
    expect(buttons[1]?.getAttribute('aria-describedby')).toBe('reassess-note-DS-S8');
  });

  it('설명이 없는 시나리오는 시각만 보여준다 — 지어내지 않는다', () => {
    const unknown = {
      scenarios: [
        { id: 'DS-S1', label: 'DS-S1', clock_label: '2022-08-08 11:00 재생', action: 'MOVE' as const },
        { id: 'DS-S9', label: 'DS-S9', clock_label: '2022-08-08 23:00 재생', action: 'WAIT' as const },
      ],
      pending: [],
    };
    render(<ReassessBar list={unknown} current="DS-S1" onReassess={() => {}} />);

    const button = screen.getByRole('button', { name: '2022-08-08 23:00 재생' });
    expect(button.getAttribute('aria-describedby')).toBeNull();
  });

  it('고를 수 있는 시각이 없으면 아무것도 그리지 않는다', () => {
    const { container } = render(
      <ReassessBar list={null} current="DS-S1" onReassess={() => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });
});

describe('경로가 실패했을 때 (M-15 · M-16 · M-32)', () => {
  it('갈 곳이 없어도 행동은 대피 그대로다', () => {
    render(<App initialData={s8} />);
    expect(s8.decision.action).toBe('EVACUATE');
    expect(screen.getByRole('heading', { name: '대피' })).toBeDefined();
  });

  it('안전거점이 없으면 119 를 강조하되 119 화면으로 바꾸지 않는다', () => {
    render(<App initialData={s8} />);
    expect(screen.getByText(/안내할 수 있는 대피 경로를 찾지 못했습니다/)).toBeDefined();
    // EMERGENCY 레이아웃으로 승격하지 않는다 — 행동 카드 제목은 여전히 '대피'다.
    expect(screen.queryByRole('heading', { name: '119' })).toBeNull();
  });

  it('후보가 왜 빠졌는지 사유를 남긴다', () => {
    render(<App initialData={s8} />);
    goTab('경로안내');

    expect(screen.getByText(/대피시설 만석 확인/)).toBeDefined();
    expect(screen.getByText(/대피시설 폐쇄 확인/)).toBeDefined();
  });

  it('대피시설은 안전을 보장하지 않는다고 적는다 (M-23)', () => {
    render(<App initialData={s7} />);
    goTab('경로안내');

    expect(screen.getByText(/개방·안전 확인 필요/)).toBeDefined();
  });

  it('M-16. 목적지 차단과 안내 가능한 경로 없음의 문구가 서로 다르다', () => {
    const blocked = {
      ...data,
      route: { ...data.route, status: 'DESTINATION_BLOCKED' as const, target: null },
    };
    const { unmount } = render(<App initialData={blocked} />);
    goTab('경로안내');
    expect(screen.getByText(/다른 목적지를 선택해 주세요/)).toBeDefined();
    expect(screen.queryByText(/안전이 확인되지 않은 경로로 이동하지 마세요/)).toBeNull();
    unmount();

    const noRoute = {
      ...data,
      decision: { ...data.decision, action: 'WAIT' as const, route_postprocess_applied: true },
      route: { ...data.route, status: 'NO_SAFE_ROUTE' as const, no_safe_route: true },
    };
    render(<App initialData={noRoute} />);
    goTab('경로안내');
    expect(screen.getByText(/안전이 확인되지 않은 경로로 이동하지 마세요/)).toBeDefined();
    expect(screen.queryByText(/다른 목적지를 선택해 주세요/)).toBeNull();
  });
});

describe('공식정보 (O-11 · M-24 · M-36)', () => {
  it('그 시각에 공개돼 있던 경보를 화면에서 볼 수 있다', () => {
    // DS-S7 은 21:40 재생이다. 호우경보(12:50 발효)는 이미 공개돼 있었다.
    render(<App initialData={s7} />);
    goTab('과거기록');

    expect(screen.getByRole('heading', { name: '공식정보' })).toBeDefined();
    expect(screen.getByText('호우경보')).toBeDefined();
  });

  /**
   * 그날 강남 도로 통제 보도는 전부 22:01 이후 송고다. 21:40 화면은 몰라야 한다.
   *
   * 타임라인이 종류별 묶음이 아니라 시각 순 한 줄이 되면서, "통제 제목이
   * 없다"로는 아무것도 증명되지 않게 됐다 — 제목 자체가 사라졌기 때문이다.
   * 그래서 **통제 항목이 렌더링될 때만 나오는 문구**가 없는지 본다.
   */
  it('그 시각에 공개돼 있지 않던 통제를 화면에 올리지 않는다', () => {
    expect(s7.official?.closures).toEqual([]);

    render(<App initialData={s7} />);
    goTab('과거기록');

    for (const label of Object.values(CLOSURE_MODE_LABEL)) {
      expect(screen.queryByText(label)).toBeNull();
    }
  });

  it('원출처를 확인한 값과 시연용으로 만든 값을 구분해 표시한다', () => {
    const { unmount } = render(<App initialData={s7} />);
    goTab('과거기록');
    expect(screen.getByText('원출처 확인됨')).toBeDefined();
    unmount();

    // DS-S6 의 통제는 실제 기록이 아니라 시연용 합성값이다.
    expect(destinationBlocked.official?.verification).toBe('DEMO_FIXTURE');
    render(<App initialData={destinationBlocked} />);
    goTab('과거기록');
    expect(screen.getByText(/시연용으로 만든 값/)).toBeDefined();
  });

  it('관측 시각을 모르는 침수는 모른다고 적는다', () => {
    // 2022-08-08 자료 대부분이 '그날 밤'까지만 말하고 분 시각을 남기지 않았다.
    const flooding = s7.official?.confirmed_flooding ?? [];
    expect(flooding.some((f) => f.observed_at === null)).toBe(true);

    render(<App initialData={s7} />);
    goTab('과거기록');
    expect(screen.getAllByText('관측 시각 확인되지 않음').length).toBeGreaterThan(0);
  });

  it('RT-11. 차량 통제를 보행 통제로 적지 않는다', () => {
    const vehicleOnly = {
      ...data,
      official: {
        ...data.official!,
        closures: [
          {
            kind: 'ROAD' as const,
            geom_ref: 'TEST-R-001',
            label: '검사용 구간',
            mode: 'VEHICLE' as const,
            available_time: data.clock.event_time,
          },
        ],
      },
    };
    render(<App initialData={vehicleOnly} />);
    goTab('과거기록');

    expect(screen.getByText(/차량 통제 \(보행 통제 여부는 확인되지 않음\)/)).toBeDefined();
  });
});

describe('프로필 (M-37)', () => {
  it('고령자·아이 동반을 고를 수 있다', () => {
    render(<App initialData={data} />);
    goTab('경로안내');

    expect(screen.getByLabelText('고령자')).toBeDefined();
    expect(screen.getByLabelText('아이 동반')).toBeDefined();
  });

  it('검증값이 아니라 팀 합의값이라고 적는다', () => {
    render(<App initialData={data} />);
    goTab('경로안내');

    expect(screen.getByText(/팀이 합의한 값이며 근거 데이터로 확인한 값이 아닙니다/)).toBeDefined();
  });

  it('안전 기준을 완화하지 않는다고 적는다', () => {
    render(<App initialData={data} />);
    goTab('경로안내');

    expect(screen.getByText(/위험구간을 빼는 기준은 그대로/)).toBeDefined();
  });

  it('골랐지만 아직 반영되지 않았다는 사실을 숨기지 않는다', () => {
    // 경로 비교 엔진이 STUB 이라 route.profile_applied 가 비어 있다.
    // ReassessBar 와 같은 방식으로 컴포넌트만 렌더링한다 — App 을 통해 누르면
    // 재요청이 나가고 그 응답이 이 검사가 보려는 것을 가린다.
    expect(data.route.profile_applied).toEqual([]);

    const { unmount } = render(
      <ProfilePicker selected={[]} applied={[]} onChange={() => {}} />,
    );
    expect(screen.queryByText(/후보 순서에는 아직 반영되지 않았습니다/)).toBeNull();
    unmount();

    render(<ProfilePicker selected={['ELDERLY']} applied={[]} onChange={() => {}} />);
    expect(screen.getByText(/후보 순서에는 아직 반영되지 않았습니다/)).toBeDefined();
  });

  it('고른 값이 그대로 위로 전달된다', () => {
    const picked: string[][] = [];
    render(
      <ProfilePicker selected={[]} applied={[]} onChange={(p) => picked.push(p)} />,
    );
    fireEvent.click(screen.getByLabelText('아이 동반'));
    expect(picked).toEqual([['WITH_CHILD']]);
  });
});
