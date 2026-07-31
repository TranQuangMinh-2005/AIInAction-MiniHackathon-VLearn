import type { Metadata } from "next";
import "./globals.css";

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
    <html lang="vi" className="h-full antialiased" style={{ colorScheme: "light" }}>
      <body className="h-full bg-slate-50 text-slate-800">
        {children}
      </body>
    </html>
  );
}
