import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { createClient } from "@/lib/supabase/server";
import LogoutButton from "@/components/LogoutButton";
import ThemeToggle from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "필체크 건강 블로그",
  description: "약을 안전하게 먹기 위한 쉬운 건강 정보",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
        />
      </head>
      <body>
        <header
          style={{
            borderBottom: "1px solid var(--line)",
            background: "rgba(14,26,24,0.8)",
            backdropFilter: "blur(8px)",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <div
            style={{
              maxWidth: 760,
              margin: "0 auto",
              padding: "18px 24px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Link
              href="/"
              style={{
                fontSize: 17,
                fontWeight: 700,
                textDecoration: "none",
                letterSpacing: "-0.02em",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <span
                style={{
                  width: 9,
                  height: 9,
                  borderRadius: "50%",
                  background: "var(--teal)",
                  display: "inline-block",
                }}
              />
              필체크 <span style={{ color: "var(--text-dim)", fontWeight: 500 }}>건강 블로그</span>
            </Link>
            <nav style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 15 }}>
              <ThemeToggle />
              {user ? (
                <>
                  <Link
                    href="/write"
                    style={{
                      textDecoration: "none",
                      color: "var(--bg)",
                      background: "var(--teal)",
                      padding: "8px 16px",
                      borderRadius: 8,
                      fontWeight: 600,
                    }}
                  >
                    글쓰기
                  </Link>
                  <LogoutButton />
                </>
              ) : (
                <Link
                  href="/login"
                  style={{
                    textDecoration: "none",
                    color: "var(--bg)",
                    background: "var(--teal)",
                    padding: "8px 16px",
                    borderRadius: 8,
                    fontWeight: 600,
                  }}
                >
                  로그인
                </Link>
              )}
            </nav>
          </div>
        </header>

        {children}

        <footer
          style={{
            maxWidth: 760,
            margin: "0 auto",
            padding: "40px 24px",
            fontSize: 13,
            color: "var(--text-dim)",
            borderTop: "1px solid var(--line)",
            marginTop: 60,
          }}
        >
          본 블로그는 참고용 건강 정보이며 의료 조언이 아닙니다. 복용 전 약사·의사와
          상담하세요.
        </footer>
      </body>
    </html>
  );
}
