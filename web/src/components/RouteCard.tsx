/**
 * 경로 카드.
 *
 * RT-02. `route_verified=false` 와 제한 문구를 **항상** 노출한다.
 * RT-03. 금지된 경로 표현을 쓰지 않는다 — 목록은 CLAUDE.md 4절과
 *        `tests/test_forbidden_wording.py` 에 있다.
 * UI-11. 도달 대상을 목적지(`MOVE`)와 대피시설(`EVACUATE`)로 구분해 적는다.
 * RT-16. 목적지 도달을 단정하지 않는다.
 */

import { ROUTE_STATUS_LABEL } from '../contracts/enums';
import type { SafeRoute } from '../contracts/types';

const FAILED: SafeRoute['status'][] = [
  'NO_SAFE_POINT',
  'NO_SAFE_ROUTE',
  'DESTINATION_BLOCKED',
  'DATA_UNAVAILABLE',
];

function heading(route: SafeRoute): string {
  if (route.route_target === 'SAFE_POINT') return '대피시설까지 · 추천 후보 경로';
  if (route.route_target === 'USER_DESTINATION') return '목적지까지 · 추천 후보 경로';
  return '경로';
}

export function RouteCard({ route }: { route: SafeRoute }) {
  if (route.status === 'NOT_REQUIRED') return null;

  const failed = FAILED.includes(route.status);

  return (
    <section className={`card route ${failed ? 'route--failed' : ''}`} aria-label="추천 후보 경로">
      <h2 className="card__title">{heading(route)}</h2>

      <p className={failed ? 'route__status route__status--failed' : 'route__status'}>
        {ROUTE_STATUS_LABEL[route.status]}
      </p>

      {route.status === 'DESTINATION_BLOCKED' && (
        <p className="route__advice" role="alert">
          다른 목적지를 골라 보세요.
        </p>
      )}

      {route.target && !failed && (
        <p className="route__target">
          <b>{route.target.label}</b> 방면 후보입니다.
          {route.distance_m != null && ` 약 ${Math.round(route.distance_m)}m`}
        </p>
      )}

      {route.candidates && route.candidates.length > 0 && !failed && (
        <ol className="route__candidates">
          {route.candidates.slice(0, 3).map((c) => (
            <li key={c.route_id}>
              <span className="route__rank">{c.rank}</span>
              {c.label}
            </li>
          ))}
        </ol>
      )}

      {route.hazards && route.hazards.length > 0 && (
        <ul className="route__hazards">
          {route.hazards.map((h, i) => (
            <li key={`${h.kind}-${i}`}>{h.text}</li>
          ))}
        </ul>
      )}

      {/* RT-02. 이 문구는 어떤 상태에서도 지우지 않는다. */}
      <p className="route__limit">{route.limit}</p>
      {!route.route_verified && (
        <p className="route__limit route__limit--sub">
          경로를 검증하지 않았습니다. 실제 통행 가능 여부는 현장에서 확인하세요.
        </p>
      )}
    </section>
  );
}
