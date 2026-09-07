import { redirect, notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { revalidatePath } from "next/cache";
import MarkdownEditor from "@/components/MarkdownEditor";

export default async function EditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: post } = await supabase.from("posts").select("*").eq("id", id).single();
  if (!post) notFound();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user || user.id !== post.author_id) redirect(`/post/${id}`);

  async function updatePost(formData: FormData) {
    "use server";
    const title = String(formData.get("title") ?? "").trim();
    const content = String(formData.get("content") ?? "").trim();
    if (!title || !content) return;
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) redirect("/login");
    await supabase.from("posts").update({ title, content }).eq("id", id);
    revalidatePath(`/post/${id}`);
    revalidatePath("/");
    redirect(`/post/${id}`);
  }

  return (
    <main style={{ maxWidth: 860, margin: "0 auto", padding: "48px 24px" }}>
      <h1 style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.02em", marginBottom: 24 }}>글 수정</h1>
      <MarkdownEditor action={updatePost} submitLabel="수정 완료"
        cancelHref={`/post/${id}`} defaultTitle={post.title} defaultContent={post.content} />
    </main>
  );
}
