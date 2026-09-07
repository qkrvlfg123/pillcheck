import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  const supabase = await createClient();

  let query = supabase
    .from("posts")
    .select("id, title, content, author_email, likes_count, created_at")
    .order("created_at", { ascending: false });

  // 검색어가 있으면 제목·내용에서 찾기
  if (q && q.trim()) {
    const kw = q.trim();
    query = query.or(`title.ilike.%${kw}%,content.ilike.%${kw}%`);
  }

  const { data: posts } = await query;

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "56px 24px" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 34, fontWeight: 800, letterSpacing: "-0.03em", margin: 0, lineHeight: 1.2 }}>
          건강 정보 이야기
        </h1>
        <p style={{ color: "var(--text-dim)", fontSize: 16, marginTop: 12 }}>
          약을 안전하게 먹기 위한 쉬운 정보를 나눕니다.
        </p>
      </div>

      {/* 검색창 */}
      <form action="/" method="get" style={{ marginBottom: 40, display: "flex", gap: 8 }}>
        <input
          name="q"
          defaultValue={q ?? ""}
          placeholder="제목·내용 검색"
          style={{
            flex: 1, padding: "12px 16px", borderRadius: 10,
            border: "1px solid var(--line)", background: "var(--bg-elev)",
            color: "var(--text)", fontSize: 15,
          }}
        />
        <button type="submit"
          style={{
            padding: "12px 20px", borderRadius: 10, border: "none",
            background: "var(--teal)", color: "var(--bg)", fontSize: 15,
            fontWeight: 600, cursor: "pointer",
          }}>
          검색
        </button>
        {q && (
          <a href="/"
            style={{
              padding: "12px 16px", borderRadius: 10, border: "1px solid var(--line)",
              color: "var(--text-dim)", fontSize: 15, textDecoration: "none",
              display: "inline-flex", alignItems: "center",
            }}>
            초기화
          </a>
        )}
      </form>

      {q && (
        <p style={{ color: "var(--text-dim)", fontSize: 14, marginBottom: 20 }}>
          '{q}' 검색 결과 {posts?.length ?? 0}건
        </p>
      )}

      {!posts || posts.length === 0 ? (
        <div style={{
          border: "1px dashed var(--line)", borderRadius: 14, padding: "56px 24px",
          textAlign: "center", color: "var(--text-dim)",
        }}>
          {q ? "검색 결과가 없어요." : "아직 글이 없어요. 첫 글을 써보세요."}
        </div>
      ) : (
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {posts.map((post, i) => (
            <li key={post.id} style={{ borderTop: i === 0 ? "1px solid var(--line)" : "none" }}>
              <Link href={`/post/${post.id}`}
                style={{ display: "block", textDecoration: "none", padding: "26px 4px", borderBottom: "1px solid var(--line)" }}>
                <h2 style={{ fontSize: 21, fontWeight: 700, margin: 0, letterSpacing: "-0.02em" }}>
                  {post.title}
                </h2>
                <p style={{
                  color: "var(--text-dim)", fontSize: 15, margin: "10px 0 0",
                  overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box",
                  WebkitLineClamp: 2, WebkitBoxOrient: "vertical", lineHeight: 1.6,
                }}>
                  {post.content}
                </p>
                <div style={{ marginTop: 14, display: "flex", gap: 16, fontSize: 13, color: "var(--text-dim)" }}>
                  <span>{post.author_email ?? "익명"}</span>
                  <span>{new Date(post.created_at).toLocaleDateString("ko-KR")}</span>
                  <span style={{ color: "var(--teal)" }}>♥ {post.likes_count}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
