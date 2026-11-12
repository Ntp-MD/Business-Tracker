export function BrandLogo({ compact = false }: { compact?: boolean }) {
  return (
    <svg
      className="logo-img"
      viewBox="0 0 340 92"
      role="img"
      aria-label="TrendRail logo"
      style={{ color: "var(--text)" }}
    >
      <rect x="2" y="14" width="64" height="64" rx="16" fill="#0f172a" />
      {/* rail tracks */}
      <path d="M20 64 L34 32" stroke="#22c55e" strokeWidth="5" strokeLinecap="round" />
      <path
        d="M36 64 L50 32"
        stroke="#22c55e"
        strokeWidth="5"
        strokeLinecap="round"
        opacity="0.65"
      />
      <path d="M22 56 H48" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" opacity="0.5" />
      <path d="M26 47 H51" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" opacity="0.35" />
      <path d="M17 22 L27 22" stroke="#22c55e" strokeWidth="4" strokeLinecap="round" />

      <text x="82" y="55" fontSize="40" fontWeight="800" letterSpacing="-1" fill="currentColor">
        Trend
        <tspan fill="#22c55e">Rail</tspan>
      </text>
      {!compact && (
        <text x="84" y="77" fontSize="11.5" fontWeight="600" letterSpacing="3.4" fill="#64748b">
          SOCIAL INTELLIGENCE
        </text>
      )}
    </svg>
  );
}
