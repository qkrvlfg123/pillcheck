import { type NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

// 이메일 인증 링크를 눌렀을 때 도착하는 곳.
// 토큰을 확인하고 세션을 만든 뒤 홈으로 보낸다.
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const token_hash = searchParams.get("token_hash");
  const type = searchParams.get("type") as
    | "email"
    | "recovery"
    | "invite"
    | null;

  if (token_hash && type) {
    const supabase = await createClient();
    const { error } = await supabase.auth.verifyOtp({ type, token_hash });
    if (!error) {
      return NextResponse.redirect(`${origin}/`);
    }
  }

  return NextResponse.redirect(`${origin}/login`);
}
