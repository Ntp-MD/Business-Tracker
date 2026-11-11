import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TrendRail — Social Intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th" data-theme="light" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
