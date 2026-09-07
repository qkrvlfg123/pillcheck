"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LikeButton({
  postId, initialLiked, initialCount, loggedIn,
}: {
  postId: string; initialLiked: boolean; initialCount: number; loggedIn: boolean;
}) {
  const router = useRouter();
  const supabase = createClient();
  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const [busy, setBusy] = useState(false);

  async function toggleLike() {
    if (!loggedIn) { router.push("/login"); return; }
    if (busy) return;
    setBusy(true);
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) { router.push("/login"); return; }
    if (liked) {
      await supabase.from("likes").delete().eq("post_id", postId).eq("user_id", user.id);
      setLiked(false); setCount((c) => Math.max(c - 1, 0));
    } else {
      await supabase.from("likes").insert({ post_id: postId, user_id: user.id });
      setLiked(true); setCount((c) => c + 1);
    }
    setBusy(false);
    router.refresh();
  }

  return (
    <button onClick={toggleLike} disabled={busy}
      style={{
        display: "inline-flex", alignItems: "center", gap: 8,
        padding: "10px 20px", borderRadius: 999, fontSize: 15, cursor: "pointer",
        border: liked ? "1px solid var(--teal)" : "1px solid var(--line)",
        background: liked ? "rgba(63,191,160,0.12)" : "transparent",
        color: liked ? "var(--teal)" : "var(--text)",
      }}>
      <span>{liked ? "♥" : "♡"}</span>
      <span>좋아요 {count}</span>
    </button>
  );
}
