import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "DripJudge AI",
  description: "Multimodal outfit analysis, roasts, and style evolution.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
