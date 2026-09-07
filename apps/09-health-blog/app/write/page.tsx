import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";
import MarkdownEditor from "@/components/MarkdownEditor";

export default async function WritePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  async function createPost(formData: FormData) {
    "use server";
    const title = String(formData.get("title") ?? "").trim();
    const content = String(formData.get("content") ?? "").trim();
    if (!title || !content) return;
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) redirect("/login");
    await supabase.from("posts").insert({
      title, content, author_id: user.id, author_email: user.email,
    });
    revalidatePath("/");
    redirect("/");
  }

  return (
    <main style={{ maxWidth: 860, margin: "0 auto", padding: "48px 24px" }}>
      <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 24 }}>
        새 글 쓰기
      </h1>
      <MarkdownEditor action={createPost} submitLabel="발행하기" cancelHref="/" />
    </main>
  );
}
