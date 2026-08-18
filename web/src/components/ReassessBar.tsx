/**
 * 수동 재판단 (M-18) — 시안 과거기록 화면의 날짜·시각 칩.
 *
 * 회의에서 5명 전원이 **자동 이벤트가 아니라 수동 버튼**으로 정했다. 누르면
 * 재생 시각을 바꾸고 그 시점의 예측·공식정보·데이터 상태·사용자 상태로 다시
 * 판단한다. 외부 API·위치·통제·시설 변화를 스스로 감지해 다시 계산하는 기능은
 * MVP 범위 밖이다.
 *
 * 그래서 이 컴포넌트는 **시계를 만들지 않는다.** 고를 수 있는 시각은 서버가 준
 * 목록뿐이고, 표시 문구도 서버의 `clock_label` 에서만 온다(F-12).
 *
 * 칩에는 시각만 찍고 이름은 `clock_label` 통째로 준다
 * ---------------------------------------------------
 * 시안의 칩은 `09:00` 처럼 짧다. 그런데 `clock_label` 은 `2022-08-08 21:40 재생`
 * 이고, 이 문자열이 **버튼의 이름**이어야 한다 — 날짜를 잃은 버튼은 어느 날을
 * 재생하는지 말하지 못한다. 그래서 눈에는 시각만, 이름(`aria-label`)에는 서버
 * 문자열을 통째로 준다. 날짜는 카드 머리에 한 번 적는다.
 */

import { SCENARIO_NOTE } from '../contracts/enums';
import { CalendarIcon, PinIcon } from './icons';
import type { ScenarioList } from '../contracts/types';

interface Props {
  list: ScenarioList | null;
  current: string;
  onReassess: (scenarioId: string) => void;
  disabled?: boolean;
  /** 현재 위치 문구. 시안의 지역 줄 자리이며 `location.label` 을 그대로 받는다. */
  where?: string;
}

/** `2022-08-08 21:40 재생` -> `21:40`. 못 찾으면 서버 문자열을 그대로 쓴다. */
function hhmm(label: string): string {
  return /(\d{2}:\d{2})/.exec(label)?.[1] ?? label;
}

/** `2022-08-08 21:40 재생` -> `2022-08-08`. 없으면 날짜 줄을 그리지 않는다. */
function ymd(label: string): string | null {
  return /(\d{4}-\d{2}-\d{2})/.exec(label)?.[1] ?? null;
}

export function ReassessBar({ list, current, onReassess, disabled = false, where }: Props) {
  /*
    시각 순으로 세운다. 과거기록은 그날 무엇이 언제였는지를 보는 화면이라
    목록이 뒤섞여 있으면 읽히지 않는다. 정렬 기준은 서버가 준 `clock_label`
    문자열 자체이며(`YYYY-MM-DD HH:MM 재생`) 화면이 시각을 새로 만들지 않는다.
    같은 시각끼리는 서버가 준 순서를 그대로 둔다 — DS-S4·S7·S8 이 그렇다.
  */
  const options = [...(list?.scenarios ?? [])].sort((a, b) =>
    a.clock_label.localeCompare(b.clock_label),
  );
  if (options.length === 0) return null;

  const date = ymd(options[0]?.clock_label ?? '');

  return (
    <section className="card reassess" aria-label="재판단">
      {date && (
        <p className="replay__date">
          <CalendarIcon size={20} />
          {date}
        </p>
      )}

      {where && (
        <p className="replay__where">
          <PinIcon size={18} />
          {where}
        </p>
      )}

      <ul className="replay__options">
        {options.map((s) => {
          const note = SCENARIO_NOTE[s.id];
          return (
            <li key={s.id}>
              <button
                type="button"
                className={`replay__button ${
                  s.id === current ? 'replay__button--current' : ''
                }`}
                onClick={() => onReassess(s.id)}
                disabled={disabled || s.id === current}
                aria-current={s.id === current}
                /*
                  이름은 서버가 준 재생 시각 문자열 통째로다(F-12). 칩에 보이는
                  것은 그중 시:분뿐이라 눈으로는 짧고 읽히기로는 온전하다.
                */
                aria-label={s.clock_label}
                /*
                  설명은 이름이 아니라 **설명**으로 붙인다. 버튼 안에 넣으면
                  읽히는 이름이 시각+상황으로 길어지는데, 이 버튼의 이름은
                  여전히 재생 시각이다(F-12).
                */
                aria-describedby={note ? `reassess-note-${s.id}` : undefined}
              >
                <span aria-hidden="true">{hhmm(s.clock_label)}</span>
              </button>

              {note && (
                <p className="replay__note" id={`reassess-note-${s.id}`}>
                  {note}
                </p>
              )}
            </li>
          );
        })}
      </ul>

      <p className="replay__hint">
        재생 시각을 바꾸면 그 시점의 예측·공식정보·자료 상태로 다시 판단합니다. 상황 변화를
        자동으로 감지하지 않습니다.
      </p>
    </section>
  );
}
