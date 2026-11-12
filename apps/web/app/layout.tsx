import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TrendRail — Social Intelligence",
  description: "แดชบอร์ดเทรนด์โซเชียล: YouTube, Google News, TikTok, FB Ads และ TikTok Ads ในที่เดียว",
  applicationName: "TrendRail",
  openGraph: {
    title: "TrendRail — Social Intelligence",
    description: "แดชบอร์ดเทรนด์โซเชียล: YouTube, Google News, TikTok, FB Ads และ TikTok Ads ในที่เดียว",
    type: "website",
  },
  twitter: { card: "summary" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th" data-theme="light" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
