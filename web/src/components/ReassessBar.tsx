/**
 * 수동 재판단 (M-18).
 *
 * 회의에서 5명 전원이 **자동 이벤트가 아니라 수동 버튼**으로 정했다. 누르면
 * 재생 시각을 바꾸고 그 시점의 예측·공식정보·데이터 상태·사용자 상태로 다시
 * 판단한다. 외부 API·위치·통제·시설 변화를 스스로 감지해 다시 계산하는 기능은
 * MVP 범위 밖이다.
 *
 * 그래서 이 컴포넌트는 **시계를 만들지 않는다.** 고를 수 있는 시각은 서버가 준
 * 목록뿐이고, 표시 문구도 서버의 `clock_label` 을 그대로 쓴다(F-12).
 */

import type { ScenarioList } from '../contracts/types';

interface Props {
  list: ScenarioList | null;
  current: string;
  onReassess: (scenarioId: string) => void;
  disabled?: boolean;
}

export function ReassessBar({ list, current, onReassess, disabled = false }: Props) {
  const options = list?.scenarios ?? [];
  if (options.length === 0) return null;

  return (
    <section className="card reassess" aria-label="재판단">
      <h2 className="card__title">다시 판단하기</h2>
      <p className="reassess__hint">
        재생 시각을 바꾸면 그 시점의 예측·공식정보·자료 상태로 다시 판단합니다.
        상황 변화를 자동으로 감지하지 않습니다.
      </p>

      <ul className="reassess__options">
        {options.map((s) => (
          <li key={s.id}>
            <button
              type="button"
              className={`reassess__button ${s.id === current ? 'reassess__button--current' : ''}`}
              onClick={() => onReassess(s.id)}
              disabled={disabled || s.id === current}
              aria-current={s.id === current}
            >
              {s.clock_label}
            </button>
          </li>
        ))}
      </ul>

      {list && list.pending.length > 0 && (
        <p className="reassess__pending">
          아직 만들지 않은 시각: {list.pending.join(' · ')}
        </p>
      )}
    </section>
  );
}
