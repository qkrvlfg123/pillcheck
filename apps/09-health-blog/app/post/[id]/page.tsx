import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";
import LikeButton from "@/components/LikeButton";
import Markdown from "@/components/Markdown";

export default async function PostPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: post } = await supabase
    .from("posts")
    .select("*")
    .eq("id", id)
    .single();

  if (!post) notFound();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  let liked = false;
  if (user) {
    const { data: likeRow } = await supabase
      .from("likes")
      .select("id")
      .eq("post_id", id)
      .eq("user_id", user.id)
      .maybeSingle();
    liked = !!likeRow;
  }

  const isAuthor = user?.id === post.author_id;

  async function deletePost() {
    "use server";
    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) redirect("/login");
    await supabase.from("posts").delete().eq("id", id);
    revalidatePath("/");
    redirect("/");
  }

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "48px 24px" }}>
      <Link
        href="/"
        style={{ fontSize: 14, color: "var(--text-dim)", textDecoration: "none" }}
      >
        ← 목록으로
      </Link>

      <article style={{ marginTop: 32 }}>
        <h1
          style={{
            fontSize: 32,
            fontWeight: 800,
            letterSpacing: "-0.03em",
            lineHeight: 1.25,
            margin: 0,
          }}
        >
          {post.title}
        </h1>
        <div
          style={{
            marginTop: 16,
            display: "flex",
            gap: 14,
            fontSize: 14,
            color: "var(--text-dim)",
            paddingBottom: 28,
            borderBottom: "1px solid var(--line)",
          }}
        >
          <span>{post.author_email ?? "익명"}</span>
          <span>{new Date(post.created_at).toLocaleDateString("ko-KR")}</span>
        </div>

        <div style={{ marginTop: 32 }}>
          <Markdown>{post.content}</Markdown>
        </div>

        <div style={{ marginTop: 40, display: "flex", alignItems: "center", gap: 12 }}>
          <LikeButton
            postId={post.id}
            initialLiked={liked}
            initialCount={post.likes_count}
            loggedIn={!!user}
          />
          {isAuthor && (
            <a
              href={`/post/${post.id}/edit`}
              style={{
                background: "transparent",
                border: "1px solid var(--line)",
                color: "var(--text)",
                padding: "10px 18px",
                borderRadius: 999,
                fontSize: 15,
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
              }}
            >
              수정
            </a>
          )}
          {isAuthor && (
            <form action={deletePost}>
              <button
                type="submit"
                style={{
                  background: "transparent",
                  border: "1px solid var(--line)",
                  color: "var(--text-dim)",
                  padding: "10px 18px",
                  borderRadius: 999,
                  fontSize: 15,
                  cursor: "pointer",
                }}
              >
                삭제
              </button>
            </form>
          )}
        </div>

        <p
          style={{
            marginTop: 40,
            padding: "16px 18px",
            border: "1px solid var(--line)",
            borderLeft: "3px solid var(--amber)",
            borderRadius: 10,
            fontSize: 14,
            color: "var(--text-dim)",
            background: "var(--bg-elev)",
          }}
        >
          참고용 정보이며 의료 조언이 아닙니다. 복용 전 약사·의사와 상담하세요.
        </p>
      </article>
    </main>
  );
}
