"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LoginPage() {
  const router = useRouter();
  const supabase = createClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    setLoading(true);
    setMessage("");
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (error) {
      setMessage("로그인 실패: 이메일과 비밀번호를 확인하세요.");
    } else {
      router.push("/");
      router.refresh();
    }
  }

  async function handleSignup() {
    setLoading(true);
    setMessage("");
    const { error } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) {
      setMessage("가입 실패: " + error.message);
    } else {
      setMessage(
        "가입 확인 메일을 보냈어요. 메일의 링크를 눌러 인증한 뒤 로그인하세요."
      );
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <h1 className="mb-6 text-2xl font-bold text-ink">로그인 / 회원가입</h1>
      <div className="space-y-4 rounded-2xl border border-teal/15 bg-white p-6">
        <div>
          <label className="mb-1 block text-base font-medium text-ink">
            이메일
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-teal/25 px-4 py-3 text-base"
            placeholder="you@example.com"
          />
        </div>
        <div>
          <label className="mb-1 block text-base font-medium text-ink">
            비밀번호
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-teal/25 px-4 py-3 text-base"
            placeholder="6자 이상"
          />
        </div>

        {message && (
          <p className="rounded-lg bg-teal-soft px-4 py-3 text-sm text-teal-deep">
            {message}
          </p>
        )}

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleLogin}
            disabled={loading}
            className="flex-1 rounded-full bg-teal px-5 py-3 text-base font-medium text-white hover:bg-teal-deep disabled:opacity-50"
          >
            로그인
          </button>
          <button
            onClick={handleSignup}
            disabled={loading}
            className="flex-1 rounded-full border-2 border-teal/30 px-5 py-3 text-base font-medium text-teal-deep hover:border-teal disabled:opacity-50"
          >
            회원가입
          </button>
        </div>
      </div>
    </main>
  );
}
