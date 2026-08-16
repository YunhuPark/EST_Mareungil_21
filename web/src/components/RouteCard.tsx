/**
 * 경로 카드.
 *
 * RT-02. `route_verified=false` 와 제한 문구를 **항상** 노출한다.
 * RT-03. 금지된 경로 표현을 쓰지 않는다 — 목록은 CLAUDE.md 5절과
 *        `tests/test_forbidden_wording.py` 에 있다.
 * UI-11. 도달 대상을 목적지(`MOVE`)와 대피시설(`EVACUATE`)로 구분해 적는다.
 * RT-16. 목적지 도달을 단정하지 않는다.
 *
 * M-16. **목적지 차단과 안내 가능한 경로 없음을 다른 상태·다른 문구로 표시한다.**
 *       둘을 같은 카드로 보여주면 "다른 목적지를 고르면 되는 상황"과 "움직이지
 *       말아야 하는 상황"이 구분되지 않는다.
 * M-15. `EVACUATE` 인데 갈 곳·길·근거가 없으면 실패 사유를 그대로 적고 119 를
 *       강조한다. 행동은 여전히 `EVACUATE` 다 — 카드가 그것을 뒤집지 않는다.
 * M-23. 대피시설은 '안전 보장'이 아니라 '개방·안전 확인 필요'로 적는다.
 */

import {
  EXCLUDED_BY_LABEL,
  NO_SAFE_ROUTE_EXTRA,
  ROUTE_ADVICE,
  ROUTE_STATUS_LABEL,
  SHELTER_NOTE,
} from '../contracts/enums';
import type { SafeRoute } from '../contracts/types';

const FAILED: SafeRoute['status'][] = [
  'NO_SAFE_POINT',
  'NO_SAFE_ROUTE',
  'DESTINATION_BLOCKED',
  'DATA_UNAVAILABLE',
];

function heading(route: SafeRoute): string {
  if (route.route_target === 'SAFE_POINT') return '대피시설 후보까지 · 추천 후보 경로';
  if (route.route_target === 'USER_DESTINATION') return '목적지까지 · 추천 후보 경로';
  return '경로';
}

export function RouteCard({ route }: { route: SafeRoute }) {
  if (route.status === 'NOT_REQUIRED') return null;

  const failed = FAILED.includes(route.status);
  const advice = ROUTE_ADVICE[route.status];
  // M-32. 실패했을 때도 "왜 후보가 없어졌는지"는 보여준다. 사유가 사라지면
  // 화면이 "그냥 없다"고만 말하게 된다.
  const excluded = (route.candidates ?? []).filter((c) => c.excluded && c.excluded_by);

  return (
    <section className={`card route ${failed ? 'route--failed' : ''}`} aria-label="추천 후보 경로">
      <h2 className="card__title">{heading(route)}</h2>

      <p className={failed ? 'route__status route__status--failed' : 'route__status'}>
        {ROUTE_STATUS_LABEL[route.status]}
      </p>

      {advice && (
        <p className="route__advice" role="alert">
          {advice}
          {route.status === 'NO_SAFE_ROUTE' && (
            <>
              <br />
              {NO_SAFE_ROUTE_EXTRA}
            </>
          )}
        </p>
      )}

      {route.target && !failed && (
        <p className="route__target">
          <b>{route.target.label}</b> 방면 후보입니다.
          {route.distance_m != null && ` 약 ${Math.round(route.distance_m)}m`}
          {/* M-23. 시설은 개방·출입구·지상 안전층이 확인되지 않았다. */}
          {route.target.kind === 'SHELTER' && (
            <span className="route__shelter-note"> · {SHELTER_NOTE}</span>
          )}
        </p>
      )}

      {route.target?.reason && !failed && (
        <p className="route__target-reason">{route.target.reason}</p>
      )}

      {route.candidates && route.candidates.length > 0 && !failed && (
        <ol className="route__candidates">
          {route.candidates
            .filter((c) => !c.excluded)
            .slice(0, 3)
            .map((c) => (
              <li key={c.route_id}>
                <span className="route__rank">{c.rank}</span>
                {c.label}
              </li>
            ))}
        </ol>
      )}

      {excluded.length > 0 && (
        <ul className="route__excluded">
          {excluded.map((c) => (
            <li key={c.route_id}>
              {c.label} — 제외 사유: {EXCLUDED_BY_LABEL[c.excluded_by ?? ''] ?? c.excluded_by}
            </li>
          ))}
        </ul>
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
