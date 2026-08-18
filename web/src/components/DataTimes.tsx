/**
 * 자료 시각 (M-08).
 *
 * 관측·예측 생성·예측 대상·마지막 갱신 시각과 경과시간을 **함께** 보여준다.
 * 10분 초과는 지연 표시만, 30분 초과는 판단 근거에서 제외됐다는 표시다.
 *
 * 접어두되 지우지 않는다 — 화면이 좁아도 확인할 수 있어야 한다.
 * 확인되지 않은 값은 지어내지 않고 그대로 말한다(M-36).
 */

import type { Clock } from '../contracts/types';

function TimeRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value ? value.slice(0, 16).replace('T', ' ') : '확인되지 않음'}</dd>
    </div>
  );
}

export function DataTimes({ clock }: { clock: Clock }) {
  const ageMin = Math.floor(clock.data_age_sec / 60);

  return (
    <section className="card" aria-label="자료 시각">
      <details className="times">
        <summary>자료 시각 자세히 (경과 {ageMin}분)</summary>

        <dl>
          <TimeRow label="관측 시각" value={clock.observed_at} />
          <TimeRow label="예측 생성" value={clock.forecast_issued_at} />
          <TimeRow label="예측 대상" value={clock.forecast_target_at} />
          <TimeRow label="마지막 갱신" value={clock.last_update_at} />
        </dl>

        <p className="times__note">
          예측 대상 시각은 그 시점의 값을 맞히는 것이며, 그 사이에 잠깐 올랐다 내려가는 변화는
          잡지 못합니다.
        </p>
      </details>

      {/* 30분 초과가 10분 초과를 포함하므로 더 무거운 쪽 하나만 띄운다. */}
      {clock.expired ? (
        <p className="badge badge--warn" role="alert">
          자료가 {ageMin}분 지나 이번 판단의 근거에서 제외했습니다
        </p>
      ) : (
        clock.stale && (
          <p className="badge badge--warn" role="alert">
            자료가 {ageMin}분 지연됐습니다
          </p>
        )
      )}
    </section>
  );
}
