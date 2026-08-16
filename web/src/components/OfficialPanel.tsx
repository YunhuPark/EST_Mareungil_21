/**
 * 공식정보 카드 — 이 재생 시각에 **공개돼 있던** 경보·통제·확인 침수.
 *
 * 왜 이 카드가 필요한가
 * ---------------------
 * O-11 로 원출처를 확인하기 전까지 화면에는 `verification` 배지 한 줄뿐이었다.
 * 값을 채워도 배지 문구만 바뀌고 호우경보가 언제 발효됐는지는 한 줄도 보이지
 * 않았다. 판단 근거를 화면이 말하지 못하면 사용자는 "왜 이 행동인가"를 확인할
 * 수 없다.
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
 */

import { CLOSURE_KIND_LABEL, CLOSURE_MODE_LABEL, VERIFICATION_LABEL } from '../contracts/enums';
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

export function OfficialPanel({ official, clockLabel }: Props) {
  if (!official) return null;

  const verification = official.verification;
  const alerts = official.alerts ?? [];
  const closures = official.closures ?? [];
  const flooding = official.confirmed_flooding ?? [];
  const empty = alerts.length === 0 && closures.length === 0 && flooding.length === 0;

  return (
    <section className="card official" aria-label="공식정보">
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

      {empty && (
        <p className="official__empty">
          이 시각에 공개된 공식 경보·통제 기록이 없습니다. 통제가 없었다는 뜻이 아니라, 이
          시각까지 공개된 기록을 찾지 못했다는 뜻입니다.
        </p>
      )}

      {alerts.length > 0 && (
        <>
          <h3 className="official__head">경보</h3>
          <ul className="official__list">
            {alerts.map((a) => (
              <li key={`${a.type}-${a.issued_at}`}>
                <strong>{a.type}</strong>
                <span className="official__time">
                  {hhmm(a.issued_at)} 발효
                  {a.cleared_at ? ` · ${hhmm(a.cleared_at)} 종료` : ''}
                </span>
                {a.region && <span className="official__meta">{a.region}</span>}
              </li>
            ))}
          </ul>
        </>
      )}

      {closures.length > 0 && (
        <>
          <h3 className="official__head">통제</h3>
          <ul className="official__list">
            {closures.map((c) => (
              <li key={c.geom_ref}>
                <strong>{CLOSURE_KIND_LABEL[c.kind] ?? c.kind}</strong>
                <span className="official__meta">{c.label ?? c.geom_ref}</span>
                <span className="official__time">
                  {CLOSURE_MODE_LABEL[c.mode] ?? c.mode}
                  {c.since ? ` · ${hhmm(c.since)}부터` : ''}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {flooding.length > 0 && (
        <>
          <h3 className="official__head">확인된 침수</h3>
          <ul className="official__list">
            {flooding.map((f) => (
              <li key={f.geom_ref}>
                <span className="official__meta">{f.label ?? f.geom_ref}</span>
                <span className="official__time">
                  {f.observed_at ? `${hhmm(f.observed_at)} 관측` : '관측 시각 확인되지 않음'}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
