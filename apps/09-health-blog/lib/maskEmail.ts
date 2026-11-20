// 글 작성자 표시용. 이메일 주소 전체를 공개 화면과 공개 테이블에 남기지 않는다.
// "someone@example.com" → "so***"
export function maskEmail(email: string | null | undefined): string | null {
  if (!email) return null;
  const local = email.split("@")[0];
  if (local.includes("*")) return local; // 이미 가려진 값
  return `${local.slice(0, 2)}***`;
}
