/**
 * 고정 상단 — 위험 등급, 현재 위치, 재생 시각.
 *
 * UI-02. 스크롤과 무관하게 보인다.
 * F-12. 시각은 `clock.label` 을 그대로 찍는다. 브라우저 시계를 쓰지 않는다.
 */

import { RISK_LABEL, RISK_MARK } from '../contracts/enums';
import type { Clock, ServiceRiskLevel, UserLocation } from '../contracts/types';

interface Props {
  riskLevel: ServiceRiskLevel;
  location: UserLocation;
  clock: Clock;
}

export function TopStatus({ riskLevel, location, clock }: Props) {
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

      {clock.stale && (
        <p className="badge badge--warn" role="alert">
          자료가 {Math.floor(clock.data_age_sec / 60)}분 지연됐습니다
        </p>
      )}

      {!location.in_service_area && (
        <p className="badge badge--warn">서비스 범위 밖입니다</p>
      )}
    </header>
  );
}
