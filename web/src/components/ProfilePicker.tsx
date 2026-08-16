/**
 * 프로필 선택 (M-37).
 *
 * 회의는 고령자·아이동반을 MVP 에 **유지**하기로 확정했다. 이 둘은 기획서와
 * 발표 범위의 핵심 사용자 유형이고, 검증되지 않은 것은 수치이지 사용자 유형이
 * 아니기 때문이다.
 *
 * 화면이 숨기지 않는 것 두 가지
 * -----------------------------
 * 1. **우회 상한 1.15 · 경사 가중 1.5 는 검증값이 아니라 팀 합의값이다.**
 *    근거 데이터로 튜닝한 값이 아니며 그 사실을 그대로 적는다.
 * 2. **지금은 선택해도 후보 순서가 바뀌지 않는다.** 경로 비교 엔진이 STUB 이라
 *    적용할 대상이 없다. 동작하지 않는 선택지를 동작하는 것처럼 두지 않는다 —
 *    `route.profile_applied` 가 비어 있는지로 화면이 이 문장을 판단한다.
 *
 * M-37 의 마지막 문장도 여기 걸린다. 프로필은 **이미 안전이 허용된 후보 안에서
 * 순서만 조정**하며 안전 기준이나 위험구간 제외 기준을 완화하지 않는다.
 */

import { PROFILES, PROFILE_LABEL } from '../contracts/enums';
import type { Profile } from '../contracts/types';

interface Props {
  selected: Profile[];
  /** route.profile_applied — 경로 결과에 실제로 반영된 프로필. */
  applied: Profile[];
  onChange: (profiles: Profile[]) => void;
  disabled?: boolean;
}

export function ProfilePicker({ selected, applied, onChange, disabled }: Props) {
  const toggle = (p: Profile) =>
    onChange(selected.includes(p) ? selected.filter((x) => x !== p) : [...selected, p]);

  const chosenButNotApplied = selected.length > 0 && applied.length === 0;

  return (
    <section className="card picker" aria-label="프로필 선택">
      <h2 className="card__title">함께 있는 사람</h2>

      <div className="picker__checks">
        {PROFILES.map((p) => (
          <label key={p} className="picker__check">
            <input
              type="checkbox"
              checked={selected.includes(p)}
              disabled={disabled}
              onChange={() => toggle(p)}
            />
            {PROFILE_LABEL[p] ?? p}
          </label>
        ))}
      </div>

      {chosenButNotApplied && (
        <p className="picker__warn">
          선택은 전달됐지만 후보 순서에는 아직 반영되지 않았습니다. 후보 비교 기능이 붙기
          전이라 적용할 대상이 없습니다.
        </p>
      )}

      <p className="picker__note">
        이동시간 60분·30분 기준과 우회 상한 1.15, 경사 가중 1.5는 팀이 합의한 값이며 근거
        데이터로 확인한 값이 아닙니다.
      </p>
      <p className="picker__note">
        선택해도 위험구간을 빼는 기준은 그대로입니다. 이미 통과한 후보 안에서 순서만
        조정합니다.
      </p>
    </section>
  );
}
