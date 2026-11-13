import type { Metadata } from "next";

import { CookieNotice } from "@/components/cookie-notice";

export const metadata: Metadata = {
  title: "TrendRail — Social Intelligence",
  description: "แดชบอร์ดเทรนด์โซเชียล: YouTube, Google News, TikTok, FB Ads และ TikTok Ads ในที่เดียว",
  applicationName: "TrendRail",
  verification: { google: "Yc6fLFj26KAvrLdVLe6J5FT3S2zft6XD7R_NmzMx8bo" },
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
      <body>
        {children}
        <CookieNotice />
      </body>
    </html>
  );
}
