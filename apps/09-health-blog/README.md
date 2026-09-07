# 09 · 필체크 건강 블로그 (완성 코드)

약을 안전하게 먹기 위한 건강 정보 블로그. **로그인·글쓰기·좋아요**가 되는
풀스택 앱이며, 이 챕터의 핵심은 **Supabase + RLS(Row Level Security) 보안**입니다.

## 무엇이 되나

- 글 목록 / 글 상세 보기 (누구나)
- 회원가입 / 로그인 (이메일)
- 글쓰기 (로그인 사용자만)
- 좋아요 (한 사람이 한 글에 한 번, 취소 가능)
- 본인 글만 삭제 — **RLS가 DB 레벨에서 강제**

## 실행 방법 (순서대로)

### 1. Supabase 프로젝트 준비
1. [supabase.com](https://supabase.com) 로그인 → 프로젝트 생성 (이미 있으면 사용)
2. 왼쪽 메뉴 **SQL Editor** → New query → `supabase/schema.sql` 내용을
   통째로 붙여넣고 **Run**. (테이블 + RLS 정책이 한 번에 생성됩니다)
3. 왼쪽 메뉴 **Project Settings → API** 에서 두 값을 복사:
   - `Project URL`
   - `anon public` 키

### 2. 환경변수 설정
프로젝트 루트에 `.env.local` 파일을 만들고 (`.env.local.example` 참고):
```
NEXT_PUBLIC_SUPABASE_URL=복사한_Project_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=복사한_anon_key
```
> `.env.local`은 git에 올라가지 않습니다(.gitignore 처리됨).

### 3. 실행
```bash
npm install       # 처음 한 번
npm run dev       # http://localhost:3000
```

### 4. (선택) 이메일 인증 끄기 — 로컬 테스트 편하게
Supabase → **Authentication → Providers → Email** 에서
"Confirm email"을 끄면 가입 즉시 로그인됩니다. (테스트용. 실제 배포 시엔 켜세요)

## RLS가 왜 핵심인가 (이 챕터의 요점)

Supabase는 `anon key`가 브라우저에 노출되는 구조입니다. 만약 RLS가 없으면
**누구나 그 키로 남의 글을 수정·삭제**할 수 있습니다.
`schema.sql`의 정책이 "본인 글만 수정·삭제, 읽기는 공개"를 **데이터베이스가
직접 강제**합니다.

**확인해보기**: 계정 A로 글을 쓰고, 계정 B로 로그인해 그 글을 삭제 시도하면
막힙니다. 막히면 RLS 성공.

## 폴더 구성

```
09-health-blog/
├── app/
│   ├── page.tsx              # 홈 (글 목록)
│   ├── login/page.tsx        # 로그인·회원가입
│   ├── write/page.tsx        # 글쓰기 (서버 액션)
│   ├── post/[id]/page.tsx    # 글 상세 (좋아요·삭제)
│   ├── auth/confirm/route.ts # 이메일 인증 콜백
│   └── layout.tsx            # 헤더 + 로그인 상태
├── components/
│   ├── LikeButton.tsx        # 좋아요 (클라이언트)
│   └── LogoutButton.tsx
├── lib/supabase/
│   ├── client.ts             # 브라우저용 클라이언트
│   └── server.ts             # 서버용 클라이언트
├── middleware.ts             # 세션 자동 갱신
└── supabase/schema.sql       # DB 스키마 + RLS 정책
```

## 스택

- Next.js 14 (App Router) + TypeScript + Tailwind CSS
- Supabase (`@supabase/ssr` — 최신 서버사이드 인증 방식)
- 배포: Vercel (환경변수만 넣으면 됨)

## 배포 (Vercel)

1. 이 폴더를 Vercel에 연결
2. Vercel 프로젝트 설정 → Environment Variables 에
   `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` 추가
3. Deploy

## 참고

- 블로그 콘텐츠는 `../../packages/shared`의 약물·건강 데이터를 소재로
  쓰면 좋습니다 (예: "함께 먹으면 안 되는 약", "감기약 성분 중복 주의").
- 모든 글에 "참고용, 의료 조언 아님" 고지가 표시됩니다.
