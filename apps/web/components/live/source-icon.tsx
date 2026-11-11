import type { ReactNode } from "react";

const TIKTOK =
  "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z";

function tiktok(): ReactNode {
  return (
    <g>
      <path d={TIKTOK} fill="#25F4EE" transform="translate(-.6 -.6)" />
      <path d={TIKTOK} fill="#FE2C55" transform="translate(.6 .6)" />
      <path d={TIKTOK} fill="#000" />
    </g>
  );
}

const ICONS: Record<string, () => ReactNode> = {
  youtube: () => (
    <g>
      <path
        fill="#FF0000"
        d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31.4 31.4 0 0 0 0 12a31.4 31.4 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31.4 31.4 0 0 0 24 12a31.4 31.4 0 0 0-.5-5.8z"
      />
      <path fill="#fff" d="M9.6 15.6V8.4L15.8 12z" />
    </g>
  ),
  facebook: () => (
    <g>
      <circle cx="12" cy="12" r="12" fill="#1877F2" />
      <path
        fill="#fff"
        d="M16.7 15.5l.5-3.5h-3.4V9.8c0-1 .5-1.9 2-1.9h1.5V4.8c-.9-.1-1.8-.2-2.7-.2-2.7 0-4.5 1.6-4.5 4.6V12H7.3v3.5h3V24a12 12 0 0 0 3.4 0v-8.5z"
      />
    </g>
  ),
  tiktok,
  gnews: () => (
    <g>
      <path
        fill="#4285F4"
        d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.7-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.8z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.2 0 5.9-1.1 7.9-2.9l-3.9-3c-1.1.7-2.4 1.2-4 1.2-3.1 0-5.7-2.1-6.7-4.9H1.3v3.1C3.3 21.4 7.3 24 12 24z"
      />
      <path fill="#FBBC05" d="M5.3 14.4a7.2 7.2 0 0 1 0-4.6V6.7H1.3a12 12 0 0 0 0 10.6l4-2.9z" />
      <path
        fill="#EA4335"
        d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4C17.9 1.2 15.2 0 12 0 7.3 0 3.3 2.6 1.3 6.7l4 3.1C6.3 6.9 8.9 4.8 12 4.8z"
      />
    </g>
  ),
  instagram: () => (
    <g>
      <rect x="2" y="2" width="20" height="20" rx="6" fill="#E4405F" />
      <circle cx="12" cy="12" r="4.2" fill="none" stroke="#fff" strokeWidth="2" />
      <circle cx="17.3" cy="6.7" r="1.3" fill="#fff" />
    </g>
  ),
  line: () => (
    <g>
      <rect width="24" height="24" rx="6" fill="#06C755" />
      <path
        fill="#fff"
        d="M12 5.5c-3.9 0-7 2.4-7 5.4 0 2.6 2.3 4.8 5.4 5.3.2 0 .5.1.6.3.1.2.1.5 0 .7l-.1.6c0 .2-.2.7.6.4s4.2-2.4 5.7-4.1c1-1.1 1.5-2.3 1.5-3.6 0-3-3.1-5.4-6.7-5.4z"
      />
    </g>
  ),
};

const ALIASES: Record<string, string> = {
  fbads: "facebook",
  ttads: "tiktok",
};

export function SourceIcon({
  source,
  size = 18,
  className = "src-ic",
}: {
  source: string;
  size?: number;
  className?: string;
}) {
  const key = ALIASES[source] ?? source.toLowerCase();
  const icon = ICONS[key];
  if (!icon) return null;
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      {icon()}
    </svg>
  );
}
