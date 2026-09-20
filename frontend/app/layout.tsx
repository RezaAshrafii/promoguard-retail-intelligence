import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PromoGuard | هوشمندی پروموشن",
  description: "Evidence-aware retail promotion intelligence",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
