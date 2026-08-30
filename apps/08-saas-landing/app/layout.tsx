import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "필체크 — 여러 약, 같이 먹어도 괜찮을까요",
  description:
    "여러 약을 함께 복용할 때의 위험을 식약처 공식 데이터로 확인하는 서비스.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
