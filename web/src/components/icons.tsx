/**
 * 화면 아이콘 — 인라인 SVG.
 *
 * 아이콘 폰트·CDN 을 쓰지 않는다. 런타임 외부 의존은 지도 타일 하나뿐이라는
 * 약속(설계서 8.5.3)이 아이콘에도 걸린다 — 네트워크가 끊긴 상황에서 위험·행동·
 * 119 가 남아야 하는데, 그때 아이콘만 네모로 깨지면 화면이 읽히지 않는다.
 *
 * **아이콘은 뜻을 혼자 지지 않는다.** UI-06 / UI-09 대로 색과 그림만으로
 * 상태를 가르지 않으며, 옆에 항상 글자가 붙는다. 그래서 전부 `aria-hidden` 이다.
 */

interface IconProps {
  /** px. 기본 24. */
  size?: number;
  className?: string;
}

function svg(
  path: React.ReactNode,
  { size = 24, className }: IconProps,
  extra?: { fill?: string },
) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={extra?.fill ?? 'none'}
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {path}
    </svg>
  );
}

export const ShieldIcon = (p: IconProps) =>
  svg(
    <>
      <path d="M12 3 4.5 6v5.4c0 4.4 3 8.3 7.5 9.6 4.5-1.3 7.5-5.2 7.5-9.6V6L12 3Z" />
      <path d="M9.5 12.2 11.3 14l3.4-3.6" />
    </>,
    p,
  );

export const GearIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="12" cy="12" r="3.1" />
      <path d="M19.4 13.9a1.5 1.5 0 0 0 .3 1.7l.1.1a1.8 1.8 0 1 1-2.6 2.6l-.1-.1a1.5 1.5 0 0 0-1.7-.3 1.5 1.5 0 0 0-.9 1.4v.2a1.8 1.8 0 1 1-3.6 0v-.1a1.5 1.5 0 0 0-1-1.4 1.5 1.5 0 0 0-1.7.3l-.1.1a1.8 1.8 0 1 1-2.6-2.6l.1-.1a1.5 1.5 0 0 0 .3-1.7 1.5 1.5 0 0 0-1.4-.9h-.2a1.8 1.8 0 1 1 0-3.6h.1a1.5 1.5 0 0 0 1.4-1 1.5 1.5 0 0 0-.3-1.7l-.1-.1a1.8 1.8 0 1 1 2.6-2.6l.1.1a1.5 1.5 0 0 0 1.7.3h.1a1.5 1.5 0 0 0 .9-1.4v-.2a1.8 1.8 0 1 1 3.6 0v.1a1.5 1.5 0 0 0 .9 1.4 1.5 1.5 0 0 0 1.7-.3l.1-.1a1.8 1.8 0 1 1 2.6 2.6l-.1.1a1.5 1.5 0 0 0-.3 1.7v.1a1.5 1.5 0 0 0 1.4.9h.2a1.8 1.8 0 1 1 0 3.6h-.1a1.5 1.5 0 0 0-1.4.9Z" />
    </>,
    p,
  );

/** 위험·심각. 삼각 경고. */
export const AlertTriangleIcon = (p: IconProps) =>
  svg(
    <>
      <path d="M12 3.6 1.9 20.4h20.2L12 3.6Z" />
      <path d="M12 9.6v4.6" />
      <path d="M12 17.4h.01" />
    </>,
    p,
  );

/** 주의. 원형 느낌표. */
export const AlertCircleIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 7.8v4.6" />
      <path d="M12 16h.01" />
    </>,
    p,
  );

/** 안전. 체크. */
export const CheckCircleIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="m8.4 12.2 2.5 2.5 4.7-5" />
    </>,
    p,
  );

/** AI 예측 근거. */
export const RobotIcon = (p: IconProps) =>
  svg(
    <>
      <rect x="4" y="8" width="16" height="11" rx="3" />
      <path d="M12 4.2v3.6" />
      <circle cx="12" cy="3.4" r="1.1" />
      <path d="M9.2 12.4v1.6M14.8 12.4v1.6" />
      <path d="M9.6 16.6h4.8" />
    </>,
    p,
  );

export const PhoneIcon = (p: IconProps) =>
  svg(
    <path d="M6.3 3.6h3l1.5 3.8-1.9 1.2a12.4 12.4 0 0 0 5.5 5.5l1.2-1.9 3.8 1.5v3a1.8 1.8 0 0 1-2 1.8C10.5 17.7 6.3 13.5 4.5 5.6a1.8 1.8 0 0 1 1.8-2Z" />,
    p,
  );

export const CopyIcon = (p: IconProps) =>
  svg(
    <>
      <rect x="8.4" y="8.4" width="11" height="11" rx="2.4" />
      <path d="M15.6 5.6H6.8a2.4 2.4 0 0 0-2.4 2.4v8.8" />
    </>,
    p,
  );

export const CalendarIcon = (p: IconProps) =>
  svg(
    <>
      <rect x="3.6" y="5.4" width="16.8" height="15" rx="2.6" />
      <path d="M3.6 10h16.8M8.4 3.6v3.6M15.6 3.6v3.6" />
    </>,
    p,
  );

/** 경로안내 탭. */
export const CompassIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="12" cy="12" r="8.8" />
      <path d="m15.4 8.6-2 5.4-5.4 2 2-5.4 5.4-2Z" />
    </>,
    p,
  );

/** 과거기록 탭. */
export const HistoryIcon = (p: IconProps) =>
  svg(
    <>
      <path d="M3.6 12a8.4 8.4 0 1 0 2.5-6" />
      <path d="M3.4 3.6v4.2h4.2" />
      <path d="M12 7.8V12l2.8 1.7" />
    </>,
    p,
  );

/** 맞춤안내 탭. */
export const PeopleIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="9" cy="8.4" r="2.9" />
      <path d="M3.8 19.4a5.2 5.2 0 0 1 10.4 0" />
      <circle cx="17.2" cy="9.4" r="2.3" />
      <path d="M15 19.4a4.4 4.4 0 0 1 5.4-3.6" />
    </>,
    p,
  );

/** 대피시설 탭. */
export const PinIcon = (p: IconProps) =>
  svg(
    <>
      <path d="M12 21.2c4-4.2 6-7.4 6-9.8a6 6 0 1 0-12 0c0 2.4 2 5.6 6 9.8Z" />
      <circle cx="12" cy="11.2" r="2.3" />
    </>,
    p,
  );

/** 우회 후보. 갈라지는 길. */
export const RouteIcon = (p: IconProps) =>
  svg(
    <>
      <path d="M12 20.4v-5.2l4.4-4.4V6.4" />
      <path d="M12 15.2 7.6 10.8V6.4" />
      <circle cx="7.6" cy="4.6" r="1.9" />
      <circle cx="16.4" cy="4.6" r="1.9" />
      <circle cx="12" cy="20.4" r="1.9" />
    </>,
    p,
  );

/** 도보 소요. */
export const WalkIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="13" cy="4.4" r="1.9" />
      <path d="M12.6 20.4 11 15.2 8.4 12l1.2-4.4 3.2-.6 2.4 3 2.6 1" />
      <path d="M11 15.2 8 20.4" />
    </>,
    p,
  );

/** 홍수·하천 경보. */
export const DropletIcon = (p: IconProps) =>
  svg(
    <path d="M12 3.4c3.2 3.8 5.2 6.6 5.2 9a5.2 5.2 0 1 1-10.4 0c0-2.4 2-5.2 5.2-9Z" />,
    p,
  );

/** 침수 발생. */
export const FloodIcon = (p: IconProps) =>
  svg(
    <>
      <path d="M5.6 12.4V8.2L12 4.6l6.4 3.6v4.2" />
      <path d="M9 12.4V9.6h6v2.8" />
      <path d="M2.8 16.2c1.6 0 1.6 1.4 3.2 1.4s1.6-1.4 3.2-1.4 1.6 1.4 3.2 1.4 1.6-1.4 3.2-1.4 1.6 1.4 3.2 1.4 1.6-1.4 2.4-1.4" />
      <path d="M2.8 20c1.6 0 1.6 1.4 3.2 1.4s1.6-1.4 3.2-1.4 1.6 1.4 3.2 1.4 1.6-1.4 3.2-1.4 1.6 1.4 3.2 1.4 1.6-1.4 2.4-1.4" />
    </>,
    p,
  );

/** 고령자 동반. */
export const ElderlyIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="11.4" cy="4.4" r="1.9" />
      <path d="M11 20.4V14l-2.4-2.6.8-3.4 2.8-.6 2.2 2.6 2.2.8" />
      <path d="M8.6 14.2 7 20.4" />
      <path d="M17.6 10.4v10" />
    </>,
    p,
  );

/** 아이 동반. */
export const ChildIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M9.2 10.4h.01M14.8 10.4h.01" />
      <path d="M9 14.6a4 4 0 0 0 6 0" />
    </>,
    p,
  );

/** 지도 현위치. */
export const LocateIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="12" cy="12" r="6.6" />
      <circle cx="12" cy="12" r="2" />
      <path d="M12 2.6v2.6M12 18.8v2.6M2.6 12h2.6M18.8 12h2.6" />
    </>,
    p,
  );

export const MapIcon = (p: IconProps) =>
  svg(
    <>
      <path d="m3.6 6.6 5.4-2.2 6 2.2 5.4-2.2v12.8l-5.4 2.2-6-2.2-5.4 2.2V6.6Z" />
      <path d="M9 4.4v14.8M15 6.6v14.8" />
    </>,
    p,
  );

export const InfoIcon = (p: IconProps) =>
  svg(
    <>
      <circle cx="12" cy="12" r="8.6" />
      <path d="M12 11.2v5M12 8h.01" />
    </>,
    p,
  );

export const ChevronDownIcon = (p: IconProps) => svg(<path d="m6.6 9.4 5.4 5.2 5.4-5.2" />, p);
