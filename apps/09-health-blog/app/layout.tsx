import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { createClient } from "@/lib/supabase/server";
import LogoutButton from "@/components/LogoutButton";

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
        <header className="border-b border-teal/15 bg-white">
          <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-lg font-bold text-teal-deep">
              필체크 건강 블로그
            </Link>
            <nav className="flex items-center gap-4 text-base">
              {user ? (
                <>
                  <Link
                    href="/write"
                    className="rounded-full bg-teal px-4 py-2 font-medium text-white hover:bg-teal-deep"
                  >
                    글쓰기
                  </Link>
                  <LogoutButton />
                </>
              ) : (
                <Link
                  href="/login"
                  className="rounded-full bg-teal px-4 py-2 font-medium text-white hover:bg-teal-deep"
                >
                  로그인
                </Link>
              )}
            </nav>
          </div>
        </header>
        {children}
        <footer className="mx-auto max-w-3xl px-6 py-10 text-sm text-ink/50">
          <p>
            본 블로그는 참고용 건강 정보이며 의료 조언이 아닙니다. 복용 전 약사·의사와
            상담하세요.
          </p>
        </footer>
      </body>
    </html>
  );
}
