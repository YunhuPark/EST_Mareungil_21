/**
 * 119 고정 버튼 — 화면 어디서나 보인다.
 *
 * UI-04 / F-15. 최소 48px, 확인창 없이 `tel:119`, `EMERGENCY` 에서 확대된다.
 * 119 외의 번호는 넣지 않는다. 서비스가 대신 연락하거나 위치를 보내지 않는다.
 *
 * **탭을 바꿔도 이 묶음은 남는다.** 시안은 화면마다 아래쪽 버튼이 달랐지만,
 * 119 는 어느 화면에 있든 보여야 한다는 것이 UI-04 다. 그래서 탭별 버튼이
 * 아니라 탭 위에 얹힌 고정 묶음으로 두었다.
 *
 * 고립 신고 버튼은 실제 119 통화와 분리한다.
 * 고립 신고는 사용자 상태를 입력하는 버튼이고,
 * 실제 전화 연결은 `119 긴급 전화` 버튼만 담당한다.
 */

import { useState } from 'react';

import { CopyIcon, PhoneIcon } from './icons';

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
  /**
   * M-19. 고립 신고를 눌렀을 때. **넘기지 않으면 버튼이 아예 렌더링되지 않는다.**
   *
   * 이 버튼은 상태를 입력할 뿐 전화를 걸지 않는다. 실제 통화는 `119 긴급 전화`
   * 하나만 담당한다 — 서비스가 대신 신고하거나 위치를 보내지 않는다는 약속을
   * 버튼 하나로 무너뜨리지 않기 위해서다.
   */
  onTrapped?: () => void;
  trappedBusy?: boolean;
}

export function EmergencyBar({
  urgent,
  emphasis = false,
  locationText,
  note,
  onTrapped,
  trappedBusy = false,
}: Props) {
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

      <a className="btn btn--primary emergency__call" href="tel:119">
        <PhoneIcon size={20} />
        119 긴급 전화
      </a>

      <button type="button" className="btn btn--outline" onClick={copy}>
        <CopyIcon size={18} />
        {copied ? '복사됨' : '현재 위치 문구 복사'}
      </button>

      {onTrapped && (
        <button
          type="button"
          className="btn btn--quiet"
          onClick={onTrapped}
          disabled={trappedBusy}
        >
          {trappedBusy ? '고립 상태 전달 중…' : '고립 신고'}
        </button>
      )}

      <p className="emergency__note">
        {note ??
          '누르면 전화 앱이 열립니다. 서비스가 대신 연락하거나 위치를 보내지 않습니다.'}
      </p>
    </div>
  );
}
