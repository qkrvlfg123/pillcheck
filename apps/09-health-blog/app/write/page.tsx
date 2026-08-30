import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";

export default async function WritePage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 로그인 안 했으면 로그인 페이지로
  if (!user) {
    redirect("/login");
  }

  // 서버 액션: 글 저장
  async function createPost(formData: FormData) {
    "use server";
    const title = String(formData.get("title") ?? "").trim();
    const content = String(formData.get("content") ?? "").trim();
    if (!title || !content) return;

    const supabase = await createClient();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) redirect("/login");

    // author_id는 반드시 본인 — RLS가 이걸 강제함
    await supabase.from("posts").insert({
      title,
      content,
      author_id: user.id,
      author_email: user.email,
    });

    revalidatePath("/");
    redirect("/");
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-6 text-2xl font-bold text-ink">새 글 쓰기</h1>
      <form action={createPost} className="space-y-4">
        <div>
          <label className="mb-1 block text-base font-medium text-ink">
            제목
          </label>
          <input
            name="title"
            required
            className="w-full rounded-lg border border-teal/25 bg-white px-4 py-3 text-base"
            placeholder="예: 감기약과 두통약, 같이 먹어도 될까요?"
          />
        </div>
        <div>
          <label className="mb-1 block text-base font-medium text-ink">
            내용
          </label>
          <textarea
            name="content"
            required
            rows={12}
            className="w-full rounded-lg border border-teal/25 bg-white px-4 py-3 text-base leading-relaxed"
            placeholder="쉬운 말로 건강 정보를 나눠주세요."
          />
        </div>
        <div className="flex gap-3">
          <button
            type="submit"
            className="rounded-full bg-teal px-6 py-3 text-base font-medium text-white hover:bg-teal-deep"
          >
            발행하기
          </button>
          <a
            href="/"
            className="rounded-full border-2 border-teal/25 px-6 py-3 text-base font-medium text-ink/60 hover:border-teal"
          >
            취소
          </a>
        </div>
      </form>
    </main>
  );
}
