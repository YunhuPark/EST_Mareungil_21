/**
 * 목적지 선택.
 *
 * UI-10 / RT-14. 경로 범위 내 지정 지점 목록에서 **1개를 필수로** 고른다.
 * 자유 텍스트·자유 좌표 입력과 선택 해제를 제공하지 않는다.
 * RT-17. 목록 등재는 안전 보장이 아니다 — 그렇게 읽히는 문구를 쓰지 않는다.
 */

import type { DestinationList, DestinationPoint } from '../contracts/types';

interface Props {
  list: DestinationList | null;
  selected: DestinationPoint;
  onSelect: (id: string) => void;
  disabled?: boolean;
}

export function DestinationPicker({ list, selected, onSelect, disabled }: Props) {
  return (
    <section className="card picker" aria-label="목적지 선택">
      <h2 className="card__title">
        <label htmlFor="destination">가려던 목적지</label>
      </h2>

      <select
        id="destination"
        className="picker__select"
        value={selected.id}
        disabled={disabled || !list}
        onChange={(e) => onSelect(e.target.value)}
      >
        {(list?.points ?? [{ ...selected, distance_from_center_m: 0, coordinate_quality: '' }]).map(
          (p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ),
        )}
      </select>

      <p className="picker__note">
        {list?.scope
          ? `${list.scope.center_label} 반경 ${list.scope.radius_m}m 안의 지점만 고를 수 있습니다.`
          : '지점 목록을 불러오는 중입니다.'}
      </p>
      <p className="picker__warn">목록에 있다는 것이 그곳이 안전하다는 뜻은 아닙니다.</p>
    </section>
  );
}
