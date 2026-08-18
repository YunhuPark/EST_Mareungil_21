/**
 * 경로안내 탭 — 시안 세 번째 화면.
 *
 * 지도를 화면 폭 가득 얹고, 그 아래에 도달 대상·소요·후보와 '함께 있는 사람'을
 * 둔다. 시안의 맨 아래 큰 버튼은 **경로 따라가기 시작**이었는데 그런 기능이
 * 없다 — 우리가 하는 것은 공식 대피경로 후보를 상대 비교해 보여주는 것까지다
 * (M-20 · M-22). 그래서 그 자리는 지도로 되돌아가는 버튼으로 둔다. 없는 기능을
 * 있는 것처럼 보이는 버튼을 두지 않는다(CLAUDE.md 3절).
 */

import { useRef } from 'react';

import { DestinationPicker } from '../components/DestinationPicker';
import { MapPanel } from '../components/MapPanel';
import { ProfilePicker } from '../components/ProfilePicker';
import { RouteCard, routeFailed, routeHeading } from '../components/RouteCard';
import { MapIcon, RouteIcon } from '../components/icons';
import type {
  AssessResponse,
  DestinationList,
  DestinationPoint,
  Profile,
} from '../contracts/types';

interface Props {
  data: AssessResponse;
  list: DestinationList | null;
  selected: DestinationPoint;
  profiles: Profile[];
  onSelectDestination: (id: string) => void;
  onChangeProfiles: (profiles: Profile[]) => void;
  busy: boolean;
}

export function RouteView({
  data,
  list,
  selected,
  profiles,
  onSelectDestination,
  onChangeProfiles,
  busy,
}: Props) {
  const mapTop = useRef<HTMLDivElement>(null);
  const { route } = data;

  return (
    <div className="view view--bleed" ref={mapTop}>
      <MapPanel data={data} scope={list?.scope ?? null} variant="hero" />

      <div className="section__head">
        <span className="section__icon">
          <RouteIcon size={22} />
        </span>
        <h2>{routeHeading(route)}</h2>
      </div>

      {/*
        M-16 / M-18. 경로가 실패하면 카드를 지우지 않고 **안내만 바꾼다.**
        카드를 통째로 감추면 "왜 안내가 없는지"가 화면에서 사라지고, 목적지
        차단과 안내 가능한 경로 없음이 다시 같은 상태로 보인다.
      */}
      <RouteCard route={route} />

      <DestinationPicker
        list={list}
        selected={selected}
        onSelect={onSelectDestination}
        disabled={busy}
      />

      <ProfilePicker
        selected={profiles}
        applied={route.profile_applied ?? []}
        onChange={onChangeProfiles}
        disabled={busy}
      />

      {!routeFailed(route) && (
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => mapTop.current?.scrollIntoView({ block: 'start' })}
        >
          <MapIcon size={20} />
          지도에서 후보 보기
        </button>
      )}
    </div>
  );
}
