/**
 * 대피시설 탭 — 시안 네 번째 화면.
 *
 * 시안의 카드에는 `여유 / 보통 / 혼잡` 배지가 붙어 있었다. **그 값은 우리에게
 * 없다.** 시설 상태 연동은 MVP 범위 밖이고(M-32), 지금 응답이 시설에 대해
 * 말할 수 있는 것은 후보 순위와 **왜 빠졌는지**뿐이다. 그래서 같은 자리에
 * 혼잡도 대신 그 두 가지를 적는다 — 없는 값을 채워 넣으면 화면이 계약보다
 * 많이 주장하게 된다.
 *
 * M-23. 목록에 있다는 것이 개방·안전을 뜻하지 않는다. 그 문장을 카드마다
 * 붙인다.
 * RT-17. 후보로 올라와 있다는 것도 안전 보장이 아니다.
 */

import {
  EXCLUDED_BY_LABEL,
  ROUTE_ADVICE,
  ROUTE_STATUS_LABEL,
  SHELTER_NOTE,
} from '../contracts/enums';
import { routeFailed } from '../components/RouteCard';
import { MapIcon, PinIcon, WalkIcon } from '../components/icons';
import type { AssessResponse } from '../contracts/types';

interface Props {
  data: AssessResponse;
  /** 지도는 경로안내 탭이 갖고 있다. 여기서는 그쪽으로 넘긴다. */
  onOpenMap: () => void;
}

export function ShelterView({ data, onOpenMap }: Props) {
  const { route, location } = data;
  const failed = routeFailed(route);
  const candidates = route.candidates ?? [];
  const etaMin = route.eta_sec == null ? null : Math.round(route.eta_sec / 60);
  const targetDistance = route.distance_m == null ? null : Math.round(route.distance_m);

  return (
    <div className="view">
      <h1 className="view__title">가까운 대피시설</h1>
      <p className="view__lead">
        현재 위치에서 비교한 후보입니다. 개방·안전 여부는 확인되지 않았습니다.
      </p>

      {/*
        UI-11. 도달 대상이 대피시설이 아닐 수도 있다. `MOVE` 일 때 응답이 고른
        대상은 **사용자가 고른 목적지**이고 대피시설이 아니다. 그 차이를 적지
        않으면 이 화면의 제목 때문에 목적지가 대피시설로 읽힌다.
      */}
      {route.route_target === 'USER_DESTINATION' && (
        <p className="badge badge--stub">
          지금은 대피 안내 상태가 아니라서 아래는 대피시설이 아니라 고른 목적지입니다. 대피가
          필요해지면 이 자리에 대피시설 후보가 올라옵니다.
        </p>
      )}

      {route.status === 'NOT_REQUIRED' ? (
        <p className="badge">{ROUTE_STATUS_LABEL[route.status]}</p>
      ) : (
        <>
          {/*
            안내 문구가 있으면 그것만 쓴다. 상태 라벨과 안내가 같은 말을 두 번
            하는 조합이 있어서(`NO_SAFE_POINT`) 붙이면 문장이 겹쳐 읽힌다.
          */}
          {failed && (
            <p className="badge badge--warn" role="alert">
              {ROUTE_ADVICE[route.status] ?? ROUTE_STATUS_LABEL[route.status]}
            </p>
          )}

          <ul className="shelters">
            {/* 이번 안내 대상. 후보 목록과 섞지 않고 맨 위에 따로 둔다. */}
            {route.target && !failed && (
              <li className="shelter">
                <p className="shelter__name">{route.target.label}</p>
                <span className="pill pill--blue">
                  {route.target.kind === 'SHELTER' ? '이번 안내 대상' : '고른 목적지'}
                </span>

                <p className="shelter__meta">
                  <WalkIcon size={16} />
                  {etaMin != null ? `도보 ${etaMin}분` : '소요 시간 확인되지 않음'}
                  {targetDistance != null && <span>· {targetDistance}m</span>}
                </p>

                <p className="shelter__note">
                  {route.target.kind === 'SHELTER' ? `${SHELTER_NOTE} · ` : ''}
                  {route.target.reason ?? '응답이 고른 도달 대상입니다.'}
                </p>
              </li>
            )}

            {candidates.map((c) => (
              <li
                key={c.route_id}
                className={`shelter ${c.excluded ? 'shelter--excluded' : ''}`}
              >
                <p className="shelter__name">{c.label}</p>

                {c.excluded ? (
                  <span className="pill pill--red">
                    제외 · {EXCLUDED_BY_LABEL[c.excluded_by ?? ''] ?? c.excluded_by}
                  </span>
                ) : (
                  <span className="pill pill--muted">후보 {c.rank}순위</span>
                )}

                <p className="shelter__meta">
                  <WalkIcon size={16} />
                  {c.distance_m != null ? `${Math.round(c.distance_m)}m` : '거리 확인되지 않음'}
                </p>
              </li>
            ))}
          </ul>

          {candidates.length === 0 && !route.target && (
            <p className="badge badge--stub">비교한 후보 목록이 응답에 없습니다.</p>
          )}
        </>
      )}

      <h2 className="view__title">지도에서 보기</h2>

      <button type="button" className="maplink" onClick={onOpenMap}>
        <span className="maplink__icon">
          <MapIcon size={22} />
        </span>
        <span>
          <span className="maplink__title">경로안내 화면의 지도로 이동</span>
          <span className="maplink__sub">후보 위치와 판단 범위를 지도에서 봅니다</span>
        </span>
      </button>

      <p className="picker__note">
        <PinIcon size={14} /> 현 위치: {location.label}
      </p>

      <p className="picker__warn">{route.limit}</p>
    </div>
  );
}
