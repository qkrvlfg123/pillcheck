import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

// 글 목록은 서버에서 불러온다 (읽기는 RLS상 누구나 가능)
export default async function Home() {
  const supabase = await createClient();
  const { data: posts } = await supabase
    .from("posts")
    .select("id, title, content, author_email, likes_count, created_at")
    .order("created_at", { ascending: false });

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-2 text-3xl font-bold text-ink">건강 정보 이야기</h1>
      <p className="mb-8 text-ink/60">
        약을 안전하게 먹기 위한 쉬운 정보를 나눠요.
      </p>

      {!posts || posts.length === 0 ? (
        <div className="rounded-2xl border border-teal/15 bg-white p-10 text-center text-ink/50">
          아직 글이 없어요. 첫 글을 써보세요.
        </div>
      ) : (
        <ul className="space-y-4">
          {posts.map((post) => (
            <li key={post.id}>
              <Link
                href={`/post/${post.id}`}
                className="block rounded-2xl border border-teal/15 bg-white p-6 transition hover:border-teal/40 hover:shadow-md"
              >
                <h2 className="text-xl font-bold text-ink">{post.title}</h2>
                <p className="mt-2 line-clamp-2 text-ink/65">{post.content}</p>
                <div className="mt-4 flex items-center gap-4 text-sm text-ink/45">
                  <span>{post.author_email ?? "익명"}</span>
                  <span>
                    {new Date(post.created_at).toLocaleDateString("ko-KR")}
                  </span>
                  <span>♥ {post.likes_count}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
