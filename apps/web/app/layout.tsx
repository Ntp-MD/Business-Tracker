import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Social Tracker",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th" data-theme="light" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
