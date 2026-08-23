import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

/* Font self-host qua next/font/google — DESIGN.md v2 §4.2
   Geist: primary (đã render-test đủ glyph tiếng Việt ơ ư đ ă â ê ô ạ ệ ữ)
   Geist Mono: số liệu, citation, quote, đồng hồ đếm giây */
const geist = Geist({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-geist",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "VLearn Reader",
  description: "Nền tảng học thích ứng",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="vi"
      className={`h-full antialiased ${geist.variable} ${geistMono.variable}`}
      style={{ colorScheme: "light" }}
    >
      <body className="h-full bg-surface-2 font-sans text-ink">{children}</body>
    </html>
  );
}
