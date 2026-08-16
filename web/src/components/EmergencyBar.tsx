/**
 * 119 고정 버튼 — 화면 어디서나 보인다.
 *
 * UI-04 / F-15. 최소 48px, 확인창 없이 `tel:119`, `EMERGENCY` 에서 확대된다.
 * 119 외의 번호는 넣지 않는다. 서비스가 대신 연락하거나 위치를 보내지 않는다.
 */

import { useState } from 'react';

interface Props {
  /** 확대 여부. action === 'EMERGENCY' 일 때만 켠다. */
  urgent: boolean;
  /**
   * M-15. `EVACUATE` 인데 갈 곳·길·근거가 없을 때의 강조.
   *
   * `urgent` 와 **다른 단계**다. 레이아웃을 EMERGENCY 로 승격하면 화면이
   * "구조를 요청하라"로 읽히는데, 그 상태의 행동은 여전히 대피다. 그래서
   * 한 줄 안내만 덧붙인다.
   */
  emphasis?: boolean;
  locationText: string;
  note?: string | null;
}

export function EmergencyBar({ urgent, emphasis = false, locationText, note }: Props) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(locationText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div
      className={`emergency ${urgent ? 'emergency--urgent' : ''} ${
        emphasis ? 'emergency--emphasis' : ''
      }`}
    >
      {emphasis && !urgent && (
        <p className="emergency__emphasis" role="alert">
          안내할 수 있는 대피 경로를 찾지 못했습니다. 119에 상황을 알리세요.
        </p>
      )}
      <a className="emergency__call" href="tel:119">
        <span aria-hidden="true">✚</span> 119 전화
      </a>
      <button type="button" className="emergency__copy" onClick={copy}>
        {copied ? '복사됨' : '위치 문구 복사'}
      </button>
      <p className="emergency__note">
        {note ?? '누르면 전화 앱이 열립니다. 서비스가 대신 연락하거나 위치를 보내지 않습니다.'}
      </p>
    </div>
  );
}
