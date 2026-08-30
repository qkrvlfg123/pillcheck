"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function LikeButton({
  postId,
  initialLiked,
  initialCount,
  loggedIn,
}: {
  postId: string;
  initialLiked: boolean;
  initialCount: number;
  loggedIn: boolean;
}) {
  const router = useRouter();
  const supabase = createClient();
  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const [busy, setBusy] = useState(false);

  async function toggleLike() {
    if (!loggedIn) {
      router.push("/login");
      return;
    }
    if (busy) return;
    setBusy(true);

    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (!user) {
      router.push("/login");
      return;
    }

    if (liked) {
      // 좋아요 취소 (본인 것만 — RLS가 강제)
      await supabase
        .from("likes")
        .delete()
        .eq("post_id", postId)
        .eq("user_id", user.id);
      setLiked(false);
      setCount((c) => Math.max(c - 1, 0));
    } else {
      // 좋아요 추가
      await supabase
        .from("likes")
        .insert({ post_id: postId, user_id: user.id });
      setLiked(true);
      setCount((c) => c + 1);
    }
    setBusy(false);
    router.refresh();
  }

  return (
    <button
      onClick={toggleLike}
      disabled={busy}
      className={`inline-flex items-center gap-2 rounded-full border px-5 py-2.5 text-base transition ${
        liked
          ? "border-amber bg-amber/10 text-amber"
          : "border-teal/30 text-teal-deep hover:border-teal"
      }`}
    >
      <span>{liked ? "♥" : "♡"}</span>
      <span>좋아요 {count}</span>
    </button>
  );
}
