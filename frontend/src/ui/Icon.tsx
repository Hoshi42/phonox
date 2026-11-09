import type { SVGProps } from 'react'

export type IconName =
  | 'library' | 'sparkle' | 'compass' | 'user' | 'search' | 'plus' | 'sort' | 'close'
  | 'chevron-right' | 'chevron-left' | 'trash' | 'move' | 'headphones' | 'download' | 'book'
  | 'chart' | 'sun' | 'moon' | 'monitor' | 'check' | 'disc' | 'filter' | 'chat' | 'swap'

const PATHS: Record<IconName, JSX.Element> = {
  library: <><path d="M4 4v16" /><path d="M9 4v16" /><path d="m14 5.5 4.6-1.4 2.2 14.9-4.6 1.4Z" /></>,
  sparkle: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4" /><path d="m6 6 2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" /></>,
  compass: <><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2 5-5 2 2-5Z" /></>,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  sort: <><path d="M7 4v16M3.5 16.5 7 20l3.5-3.5" /><path d="M17 20V4M13.5 7.5 17 4l3.5 3.5" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  'chevron-right': <><path d="m9 6 6 6-6 6" /></>,
  'chevron-left': <><path d="m15 6-6 6 6 6" /></>,
  trash: <><path d="M4 7h16M10 11v6M14 11v6" /><path d="M6 7l1 13h10l1-13M9 7V4h6v3" /></>,
  move: <><path d="M4 12h13M13 7l5 5-5 5" /><path d="M20 4v16" /></>,
  headphones: <><path d="M4 15v-3a8 8 0 0 1 16 0v3" /><rect x="3" y="14" width="4" height="6" rx="1.5" /><rect x="17" y="14" width="4" height="6" rx="1.5" /></>,
  download: <><path d="M12 4v11M7.5 11 12 15.5 16.5 11M5 20h14" /></>,
  book: <><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3Z" /><path d="M5 17a3 3 0 0 1 3-3h11" /></>,
  chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19" /></>,
  moon: <><path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z" /></>,
  monitor: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M9 20h6M12 16v4" /></>,
  check: <><path d="m5 12.5 4.5 4.5L19 7.5" /></>,
  disc: <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="2.5" /></>,
  filter: <><path d="M4 6h16M7 12h10M10 18h4" /></>,
  chat: <><path d="M4 5h16v11H9l-5 4Z" /></>,
  swap: <><path d="M4 8h14M14 4l4 4-4 4M20 16H6M10 12l-4 4 4 4" /></>,
}

interface IconProps extends Omit<SVGProps<SVGSVGElement>, 'name'> {
  name: IconName
  size?: number
}

export function Icon({ name, size = 22, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {PATHS[name]}
    </svg>
  )
}
