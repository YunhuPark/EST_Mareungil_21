/**
 * 행동 카드 — 시안 첫 화면의 근거 카드 자리.
 *
 * UI-03 / C-05. 레이아웃은 위험 등급이 아니라 `action` 으로 분기한다.
 * 라벨은 계약 값을 그대로 옮긴 `ACTION_LABEL` 만 쓴다 — 컴포넌트가 문구를
 * 새로 만들지 않는다.
 *
 * 시안은 이 자리에 로봇 아이콘과 예측 문장을 두었다. 우리 응답에서 그 자리에
 * 오는 것은 **행동 하나와 그 행동의 설명**이고, 무엇을 근거로 그 행동이
 * 나왔는지는 바로 아래 이유 목록(`ReasonList`)이 `basis` 라벨과 함께 말한다.
 * 카드 제목을 'AI 예측'으로 굳히지 않는 이유가 그것이다 — 공식 지시로 나온
 * 행동에까지 AI 딱지가 붙는다.
 */

import { ACTION_LABEL, ACTION_MARK } from '../contracts/enums';
import { RobotIcon } from './icons';
import type { Action } from '../contracts/types';

interface Props {
  action: Action;
  /** 경로 후처리 이전의 1차 행동. 다르면 왜 바뀌었는지 보여준다. */
  primaryAction: Action;
  postprocessApplied?: boolean;
  nextCheckAt?: string | null;
}

const HINT: Record<Action, string> = {
  MOVE: '지금 이동해도 되는 상태입니다. 어디로 가라는 지시가 아닙니다.',
  WAIT: '안전한 실내에 머무르며 다시 확인하세요.',
  EVACUATE: '아래 대피시설로 이동하세요.',
  EMERGENCY: '자력 이동이 어려운 상태입니다. 119로 연락하세요.',
  UNAVAILABLE: '판단에 필요한 자료가 없어 행동을 알려드릴 수 없습니다.',
};

export function ActionCard({ action, primaryAction, postprocessApplied, nextCheckAt }: Props) {
  return (
    <section className={`card action action--${action.toLowerCase()}`} aria-label="권고 행동">
      <span className="action__icon">
        <RobotIcon size={24} />
      </span>

      <h2 className="action__label">
        <span className="action__mark" aria-hidden="true">
          {ACTION_MARK[action]}
        </span>
        {ACTION_LABEL[action]}
      </h2>

      <div className="action__body">
        <p className="action__hint">{HINT[action]}</p>

        {postprocessApplied && primaryAction !== action && (
          <p className="action__transition">
            처음 판정은 <b>{ACTION_LABEL[primaryAction]}</b>이었으나 경로 결과에 따라{' '}
            <b>{ACTION_LABEL[action]}</b>(으)로 바뀌었습니다.
          </p>
        )}

        {nextCheckAt && (
          <p className="action__next">
            다시 확인할 시각 <time dateTime={nextCheckAt}>{nextCheckAt.slice(11, 16)}</time>
          </p>
        )}
      </div>
    </section>
  );
}
