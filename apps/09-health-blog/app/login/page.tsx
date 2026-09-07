"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useState } from "react";

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "13px 15px",
  borderRadius: 10,
  border: "1px solid var(--line)",
  background: "var(--bg-elev)",
  color: "var(--text)",
  fontSize: 15,
};

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
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) setMessage("로그인 실패: 이메일과 비밀번호를 확인하세요.");
    else {
      router.push("/");
      router.refresh();
    }
  }

  async function handleSignup() {
    setLoading(true);
    setMessage("");
    const { error } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) setMessage("가입 실패: " + error.message);
    else setMessage("가입되었습니다. 로그인해 주세요.");
  }

  return (
    <main style={{ maxWidth: 420, margin: "0 auto", padding: "72px 24px" }}>
      <h1 style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.02em" }}>
        로그인 / 회원가입
      </h1>
      <div
        style={{
          marginTop: 24,
          padding: 24,
          border: "1px solid var(--line)",
          borderRadius: 16,
          background: "var(--bg-elev)",
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div>
          <label style={{ display: "block", marginBottom: 7, fontSize: 14, color: "var(--text-dim)" }}>
            이메일
          </label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            style={inputStyle} placeholder="you@example.com" />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: 7, fontSize: 14, color: "var(--text-dim)" }}>
            비밀번호
          </label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            style={inputStyle} placeholder="6자 이상" />
        </div>

        {message && (
          <p style={{
            fontSize: 14, color: "var(--teal)", background: "rgba(63,191,160,0.1)",
            padding: "10px 14px", borderRadius: 8, margin: 0,
          }}>
            {message}
          </p>
        )}

        <div style={{ display: "flex", gap: 10, paddingTop: 4 }}>
          <button onClick={handleLogin} disabled={loading}
            style={{
              flex: 1, padding: "12px", borderRadius: 999, border: "none",
              background: "var(--teal)", color: "var(--bg)", fontSize: 15,
              fontWeight: 600, cursor: "pointer", opacity: loading ? 0.5 : 1,
            }}>
            로그인
          </button>
          <button onClick={handleSignup} disabled={loading}
            style={{
              flex: 1, padding: "12px", borderRadius: 999,
              border: "1px solid var(--line)", background: "transparent",
              color: "var(--text)", fontSize: 15, fontWeight: 600,
              cursor: "pointer", opacity: loading ? 0.5 : 1,
            }}>
            회원가입
          </button>
        </div>
      </div>
    </main>
  );
}
