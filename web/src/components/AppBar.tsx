/**
 * 고정 상단 — 시안의 머리글 + UI-02 가 요구하는 상태 줄.
 *
 * 시안은 머리글 한 줄(방패·마른길·톱니)만 두지만, UI-02 는 **위험 등급·현재
 * 위치·재생 시각이 스크롤과 무관하게 보일 것**을 요구한다. 시안의 첫 화면은
 * 그 셋을 본문 히어로에 두는데, 본문은 탭마다 바뀌고 스크롤되면 사라진다.
 * 그래서 머리글 아래에 한 줄로 압축해 붙였다 — 지우지 않고 줄인 것이다.
 *
 * F-12. 시각은 `clock.label` 을 **그대로** 찍는다. 브라우저 시계를 쓰지 않는다.
 *
 * 정보 버튼
 * ---------
 * 일반 사용자에게 계약·정책·모델 버전을 노출하지 않는다. 정보 버튼은 지금
 * 화면이 과거 기록 재생인지, 공식정보 출처와 한계가 무엇인지만 펼친다.
 */

import { RISK_LABEL, RISK_MARK } from '../contracts/enums';
import { InfoIcon, ShieldIcon } from './icons';
import type { AssessResponse } from '../contracts/types';

interface Props {
  data: AssessResponse;
  infoOpen: boolean;
  onToggleInfo: () => void;
}

export function AppBar({ data, infoOpen, onToggleInfo }: Props) {
  const { decision, location, clock } = data;
  const risk = decision.service_risk_level;
  const tone = `tone--${risk.toLowerCase()}`;

  return (
    <header className="appbar">
      <div className="appbar__row">
        <span className="appbar__mark">
          <ShieldIcon size={26} />
        </span>

        <p className="appbar__brand">마른길</p>

        <button
          type="button"
          className="appbar__info"
          onClick={onToggleInfo}
          aria-expanded={infoOpen}
          aria-controls="app-info"
          aria-label="데이터 출처와 한계"
        >
          <InfoIcon size={22} />
        </button>
      </div>

      {/* UI-02. 스크롤·탭 전환과 무관하게 남는 세 가지. */}
      <div className="statusstrip" role="status" aria-live="polite">
        <span className={`statusstrip__risk ${tone}`}>
          <span aria-hidden="true">{RISK_MARK[risk]}</span>
          <span className="statusstrip__label">위험 등급</span>
          <span>{RISK_LABEL[risk]}</span>
        </span>

        <span className="statusstrip__sep" aria-hidden="true">
          |
        </span>

        <span>
          <span className="statusstrip__label">현재 위치 </span>
          <span className="statusstrip__value">{location.label}</span>
        </span>

        <span className="statusstrip__sep" aria-hidden="true">
          |
        </span>

        <span>
          <span className="statusstrip__label">재생 시각 </span>
          <span className="statusstrip__value">{clock.label}</span>
        </span>
      </div>
    </header>
  );
}

function sourceNotice(sourceKind: AssessResponse['source_kind']): string {
  if (sourceKind === 'LIVE_PIPELINE') {
    return '위험·행동은 현재 엔진이 계산했지만, 2022년 과거 기록 재생 자료를 사용합니다. 지금 발생 중인 재난을 나타내지 않습니다.';
  }

  if (sourceKind === 'STUB') {
    return '일부 기능은 시연용 대체 데이터를 사용하는 2022년 과거 기록 재생입니다. 지금 발생 중인 재난을 나타내지 않습니다.';
  }

  return '이 화면은 2022년 과거 기록 재생을 위한 시연용 고정 데이터를 사용합니다. 지금 발생 중인 재난을 나타내지 않습니다.';
}

/** 정보 버튼을 눌렀을 때 열리는 사용자용 출처·한계 안내. */
export function InfoSheet({ data }: { data: AssessResponse }) {
  const official = data.official;

  return (
    <section className="sheet" id="app-info" aria-label="데이터 출처와 한계">
      <h2 className="card__title">데이터 출처와 한계</h2>

      <p className="sheet__lead">{sourceNotice(data.source_kind)}</p>

      {official && (
        <details className="sheet__source">
          <summary>공식정보 출처 보기</summary>
          <p>{official.source}</p>
        </details>
      )}

      <p className="sheet__limit">{data.notice.disclaimer}</p>
    </section>
  );
}
