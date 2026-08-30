import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";
import LikeButton from "@/components/LikeButton";

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

  // 이 사용자가 이미 좋아요 눌렀는지
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

  // 서버 액션: 삭제 (본인 글만 — RLS가 강제)
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
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/" className="text-base text-teal hover:underline">
        ← 목록으로
      </Link>

      <article className="mt-6">
        <h1 className="text-3xl font-bold text-ink">{post.title}</h1>
        <div className="mt-3 flex items-center gap-4 text-sm text-ink/45">
          <span>{post.author_email ?? "익명"}</span>
          <span>{new Date(post.created_at).toLocaleDateString("ko-KR")}</span>
        </div>

        <div className="mt-8 whitespace-pre-wrap text-lg leading-relaxed text-ink/85">
          {post.content}
        </div>

        <div className="mt-10 flex items-center gap-4">
          <LikeButton
            postId={post.id}
            initialLiked={liked}
            initialCount={post.likes_count}
            loggedIn={!!user}
          />
          {isAuthor && (
            <form action={deletePost}>
              <button
                type="submit"
                className="rounded-full border border-ink/15 px-5 py-2.5 text-base text-ink/50 hover:border-ink/30 hover:text-ink/70"
              >
                삭제
              </button>
            </form>
          )}
        </div>

        <p className="mt-10 rounded-xl border border-amber/30 bg-amber/5 p-4 text-sm text-ink/60">
          참고용 정보이며 의료 조언이 아닙니다. 복용 전 약사·의사와 상담하세요.
        </p>
      </article>
    </main>
  );
}
