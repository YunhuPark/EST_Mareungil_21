/**
 * 판단 이유.
 *
 * F-03. 최대 3줄. 계약이 이미 `maxItems: 3` 으로 막지만 화면에서도 자른다.
 * 각 줄에 `basis` 라벨을 붙여 공식·AI 예측·팀 기준을 섞지 않는다(N-09).
 */

import { BASIS_LABEL } from '../contracts/enums';
import type { Reason } from '../contracts/types';

export function ReasonList({ reasons }: { reasons: Reason[] }) {
  if (reasons.length === 0) return null;

  return (
    <section className="card reasons" aria-label="판단 이유">
      <h2 className="card__title">왜 이런 판단인가</h2>
      <ul>
        {reasons.slice(0, 3).map((r) => (
          <li key={r.code} className={`reason reason--${r.basis.toLowerCase()}`}>
            <span className="reason__basis">{BASIS_LABEL[r.basis]}</span>
            <span className="reason__text">{r.text}</span>
          </li>
        ))}
      </ul>
      <p className="reasons__note">
        &lsquo;팀 기준&rsquo;은 공식 재난 기준이 아니라 이 팀이 정한 규칙입니다.
      </p>
    </section>
  );
}
