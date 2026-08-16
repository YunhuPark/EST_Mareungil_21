/**
 * 고정 상단 — 위험 등급, 현재 위치, 재생 시각.
 *
 * UI-02. 스크롤과 무관하게 보인다.
 * F-12. 시각은 `clock.label` 을 그대로 찍는다. 브라우저 시계를 쓰지 않는다.
 * M-08. 관측·예측 생성·예측 대상·마지막 갱신 시각과 경과시간을 **함께** 보여준다.
 *       10분 초과는 지연 표시만, 30분 초과는 판단 근거에서 제외됐다는 표시다.
 */

import { RISK_LABEL, RISK_MARK } from '../contracts/enums';
import type { Clock, ServiceRiskLevel, UserLocation } from '../contracts/types';

interface Props {
  riskLevel: ServiceRiskLevel;
  location: UserLocation;
  clock: Clock;
}

/** 시각 한 줄. 확인되지 않은 값은 지어내지 않고 그대로 말한다(M-36). */
function TimeRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value ? value.slice(0, 16).replace('T', ' ') : '확인되지 않음'}</dd>
    </div>
  );
}

export function TopStatus({ riskLevel, location, clock }: Props) {
  const ageMin = Math.floor(clock.data_age_sec / 60);

  return (
    <header className="top" role="status" aria-live="polite">
      <div className={`risk risk--${riskLevel.toLowerCase()}`}>
        <span className="risk__mark" aria-hidden="true">
          {RISK_MARK[riskLevel]}
        </span>
        <span className="risk__text">
          <span className="risk__label">위험 등급</span>
          <strong className="risk__value">{RISK_LABEL[riskLevel]}</strong>
        </span>
      </div>

      <dl className="top__meta">
        <div>
          <dt>현재 위치</dt>
          <dd>{location.label}</dd>
        </div>
        <div>
          <dt>재생 시각</dt>
          <dd>{clock.label}</dd>
        </div>
      </dl>

      {/* M-08. 네 시각과 경과시간을 한 자리에 모은다. 접어두되 지우지 않는다. */}
      <details className="top__times">
        <summary>자료 시각 자세히 (경과 {ageMin}분)</summary>
        <dl className="top__meta top__meta--times">
          <TimeRow label="관측 시각" value={clock.observed_at} />
          <TimeRow label="예측 생성" value={clock.forecast_issued_at} />
          <TimeRow label="예측 대상" value={clock.forecast_target_at} />
          <TimeRow label="마지막 갱신" value={clock.last_update_at} />
        </dl>
        <p className="top__times-note">
          예측 대상 시각은 그 시점의 값을 맞히는 것이며, 그 사이에 잠깐 올랐다
          내려가는 변화는 잡지 못합니다.
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

      {!location.in_service_area && (
        <p className="badge badge--warn">서비스 범위 밖입니다</p>
      )}
    </header>
  );
}
