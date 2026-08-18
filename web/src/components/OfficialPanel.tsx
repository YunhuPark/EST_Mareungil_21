/**
 * 공식정보 — 이 재생 시각에 **공개돼 있던** 경보·통제·확인 침수.
 *
 * 시안 과거기록 화면의 세로 타임라인이 이 자리다. 항목을 종류별로 묶지 않고
 * **시각 순으로 한 줄에 세운다** — 그날 무엇이 어떤 순서로 알려졌는지가
 * 종류별 묶음보다 먼저 보여야 하기 때문이다.
 *
 * 이 카드가 지키는 것
 * -------------------
 * - **시각 필터는 서버가 건다**(M-36 / services/decision/official.py). 여기서
 *   다시 거르지 않는다 — 두 곳에서 판정하면 화면과 판단이 어긋난다.
 * - **`VEHICLE` 통제를 보행 차단으로 승격하지 않는다**(RT-11). 라벨이 그 차이를
 *   그대로 말한다.
 * - **해제된 경보를 지우지 않는다**(F-14). 지나간 것은 지나갔다고 적을 뿐이다.
 * - `observed_at` 이 null 이면 "관측 시각 확인되지 않음"이라고 쓴다. 값을 만들지
 *   않는다.
 * - 목록이 비어 있으면 **비어 있다고 말한다.** 확인된 통제가 0건인 것과 통제가
 *   없었던 것은 다르므로 그 차이를 문구로 적는다.
 *
 * 색과 아이콘은 뜻을 혼자 지지 않는다. 어떤 종류인지는 항상 알약 안의 **글자**가
 * 말하며, 색은 그 글자를 거드는 자리다(UI-06 / UI-09).
 */

import { CLOSURE_KIND_LABEL, CLOSURE_MODE_LABEL, VERIFICATION_LABEL } from '../contracts/enums';
import { AlertTriangleIcon, DropletIcon, FloodIcon } from './icons';
import type { AssessResponse } from '../contracts/types';

interface Props {
  official: AssessResponse['official'];
  /** clock.label 을 그대로 받는다. UI 가 시각 문구를 만들지 않는다. */
  clockLabel: string;
}

/** `2022-08-08T21:10:00+09:00` -> `21:10`. 날짜는 clock.label 이 이미 말한다. */
function hhmm(iso?: string | null): string | null {
  if (!iso) return null;
  const m = /T(\d{2}:\d{2})/.exec(iso);
  return m?.[1] ?? iso;
}

type Tone = 'alert' | 'watch' | 'flood' | 'closure';

interface Entry {
  key: string;
  tone: Tone;
  /** 알약에 찍는 종류. 계약 값이나 라벨 표에서만 온다. */
  kind: string;
  time: string | null;
  title: string;
  lines: string[];
  /** 정렬용. 화면에 찍지 않는다. */
  sortAt: string;
}

const TONE_ICON = {
  alert: AlertTriangleIcon,
  watch: DropletIcon,
  flood: FloodIcon,
  closure: AlertTriangleIcon,
} as const;

const TONE_PILL: Record<Tone, string> = {
  alert: 'pill--red',
  watch: 'pill--orange',
  flood: 'pill--solid',
  closure: 'pill--muted',
};

/**
 * 경보인지 주의보인지. **색을 고르기 위한 것뿐이며 뜻을 새로 만들지 않는다** —
 * 알약에 찍히는 글자는 언제나 공식 발표가 쓴 종류 이름 그대로다.
 */
function alertTone(type: string): Tone {
  return type.includes('경보') ? 'alert' : 'watch';
}

export function OfficialPanel({ official, clockLabel }: Props) {
  if (!official) return null;

  const verification = official.verification;
  const alerts = official.alerts ?? [];
  const closures = official.closures ?? [];
  const flooding = official.confirmed_flooding ?? [];
  const empty = alerts.length === 0 && closures.length === 0 && flooding.length === 0;

  const entries: Entry[] = [
    ...alerts.map((a) => ({
      key: `alert-${a.type}-${a.issued_at}`,
      tone: alertTone(a.type),
      kind: a.type,
      time: hhmm(a.issued_at),
      title: a.region ? `${a.region} ${a.type}` : a.type,
      lines: [
        a.cleared_at ? `${hhmm(a.cleared_at)} 종료로 기록돼 있습니다.` : null,
        a.source ?? null,
      ].filter((x): x is string => Boolean(x)),
      sortAt: a.issued_at,
    })),

    ...closures.map((c) => ({
      key: `closure-${c.geom_ref}`,
      tone: 'closure' as const,
      kind: CLOSURE_KIND_LABEL[c.kind] ?? c.kind,
      time: hhmm(c.since),
      title: c.label ?? c.geom_ref,
      lines: [CLOSURE_MODE_LABEL[c.mode] ?? c.mode],
      sortAt: c.since ?? c.available_time ?? '',
    })),

    ...flooding.map((f) => ({
      key: `flood-${f.geom_ref}`,
      tone: 'flood' as const,
      kind: '침수 발생',
      time: hhmm(f.observed_at),
      title: f.label ?? f.geom_ref,
      lines: [f.observed_at ? '' : '관측 시각 확인되지 않음', f.source ?? ''].filter(Boolean),
      sortAt: f.observed_at ?? f.available_time ?? '',
    })),
  ].sort((a, b) => a.sortAt.localeCompare(b.sortAt));

  return (
    <section className="official" aria-label="공식정보">
      <h2 className="card__title">공식정보</h2>

      <p className="official__asof">
        {clockLabel} 시점에 공개돼 있던 정보만 표시합니다. 이후에 공개된 정보는 담지 않습니다.
      </p>

      {verification && (
        <p className={verification === 'VERIFIED_SOURCE' ? 'official__ok' : 'official__warn'}>
          {VERIFICATION_LABEL[verification] ?? verification}
        </p>
      )}

      {official.evacuation_order && (
        <p className="official__order">공식 대피 지시가 있습니다.</p>
      )}

      {empty ? (
        <p className="official__empty">
          이 시각에 공개된 공식 경보·통제 기록이 없습니다. 통제가 없었다는 뜻이 아니라, 이
          시각까지 공개된 기록을 찾지 못했다는 뜻입니다.
        </p>
      ) : (
        <ul className="timeline">
          {entries.map((e) => {
            const Icon = TONE_ICON[e.tone];
            return (
              <li key={e.key} className={`tl tl--${e.tone}`}>
                <span className="tl__dot">
                  <Icon size={18} />
                </span>

                <div className="tl__head">
                  <span className={`pill ${TONE_PILL[e.tone]}`}>{e.kind}</span>
                  {/* 시각을 모르면 자리를 비운다. 아래 문장이 그 사실을 말한다. */}
                  {e.time && <span className="tl__time">{e.time}</span>}
                </div>

                <p className="tl__title">{e.title}</p>

                {e.lines.map((line) => (
                  <p key={line} className="tl__text">
                    {line}
                  </p>
                ))}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
