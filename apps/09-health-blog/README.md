# 09 · 필체크 건강 블로그

약을 안전하게 먹기 위한 건강 정보를 쓰고 나누는 풀스택 블로그 — 이 앱의 핵심은 **Supabase RLS(Row Level Security)로 "본인 글만 수정·삭제"를 DB 레벨에서 강제**하는 것입니다.

## 주요 기능

- **회원가입 / 로그인** — Supabase Auth(이메일). 이메일 확인 링크는 `app/auth/confirm/route.ts`가 처리
- **글 CRUD** — 목록 · 상세 보기는 누구나, 글쓰기 · 수정 · 삭제는 로그인한 본인만
- **좋아요** — 한 사람이 한 글에 한 번(DB `unique` 제약), 다시 누르면 취소.
  개수는 트리거가 `posts.likes_count`에 자동 반영
- **검색** — 제목·내용에서 찾기 (`/?q=검색어`)
- **마크다운 작성 + 실시간 미리보기** — `MarkdownEditor.tsx`(작성) / `Markdown.tsx`(렌더, GFM 지원)
- **다크 / 라이트 테마 전환** — `ThemeToggle.tsx`, 선택값은 localStorage에 저장(기본 다크)
- **세션 자동 갱신** — `middleware.ts`가 만료된 인증 토큰을 갱신하고 쿠키를 동기화

### 이 앱의 핵심: RLS 보안

RLS가 없으면 anon key만 아는 사람은 **누구나 남의 글을 수정·삭제**할 수 있습니다.
`supabase/schema.sql`의 정책이 이를 DB에서 막습니다.

| 대상 | 읽기 | 쓰기 | 수정 | 삭제 |
| --- | --- | --- | --- | --- |
| `posts` | 누구나 | 로그인 + `auth.uid() = author_id` | 본인 글만 | 본인 글만 |
| `likes` | 누구나 | 로그인 + 본인 `user_id`로만 | — | 본인 좋아요만 |

> 확인 방법: 계정 A로 글을 쓰고 계정 B로 그 글을 수정해보세요. **막히면 정상입니다.**

## 실행 방법

### 1. Supabase 프로젝트 준비

1. [supabase.com](https://supabase.com) 로그인 → 프로젝트 생성
2. **SQL Editor → New query** 에 `supabase/schema.sql` 전체를 붙여넣고 **Run**
   (테이블 · RLS 정책 · 좋아요 트리거가 한 번에 만들어집니다)
3. **Project Settings → API** 에서 `Project URL` 과 `anon public` 키를 복사

### 2. 환경변수 설정

앱 폴더에 `.env.local` 파일을 만듭니다 (`.env.local.example` 참고):

```
NEXT_PUBLIC_SUPABASE_URL=복사한_Project_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=복사한_anon_key
```

> `.env.local`은 `.gitignore` 처리되어 git에 올라가지 않습니다.

### 3. 실행

```bash
cd apps/09-health-blog
npm install
npm run dev       # → http://localhost:3000
```

`npm run build` 로 배포 전 빌드를 확인할 수 있습니다.

## 기술 스택

| 항목 | 내용 |
| --- | --- |
| 프레임워크 | Next.js 14.2 (App Router, 서버 컴포넌트) |
| 언어 | TypeScript, React 18 |
| 백엔드 · DB | Supabase (Postgres + Auth + RLS) |
| Supabase 연동 | `@supabase/ssr`, `@supabase/supabase-js` |
| 마크다운 | `react-markdown` + `remark-gfm` |
| 스타일 | Tailwind CSS + CSS 변수 기반 테마(`--bg-elev`, `--line`, `--teal` 등) |
| 필요한 키 | Supabase URL + anon key (**필수**) |

### 파일 구성

```
app/page.tsx                글 목록 + 검색
app/post/[id]/page.tsx      글 상세 (좋아요 · 수정/삭제 진입)
app/post/[id]/edit/page.tsx 글 수정
app/write/page.tsx          글쓰기
app/login/page.tsx          로그인 / 회원가입
app/auth/confirm/route.ts   이메일 확인 콜백
components/                 LikeButton · LogoutButton · Markdown · MarkdownEditor · ThemeToggle
lib/supabase/               client.ts(브라우저) · server.ts(서버 컴포넌트)
middleware.ts               인증 토큰 갱신
supabase/schema.sql         테이블 + RLS 정책 + 좋아요 트리거
```

## 주의사항

- **이 서비스는 의료기기가 아닙니다.** 블로그의 글은 참고용 건강 정보이며 의료 조언·진단·처방이 아닙니다.
  **복용 전 최종 판단은 의사·약사와 함께 하세요.** (이 고지는 모든 페이지 하단에 표시됩니다)
- 글 내용은 사용자가 직접 작성하는 것이라 **검증되지 않은 정보가 섞일 수 있습니다.**
- `anon key`는 브라우저에 노출되는 공개 키입니다. **보안은 키를 숨겨서가 아니라 RLS로 지킵니다.**
  `schema.sql`을 실행하지 않은 채 서비스하지 마세요.
- `service_role` 키는 절대 프런트엔드나 `.env.local`의 `NEXT_PUBLIC_*` 변수에 넣지 마세요.
- 실제 개인정보는 쓰지 않습니다. 개발·데모에는 가상·합성 데이터만 사용하세요.
