# CLAUDE.md — 09 건강정보 블로그

## 이 앱의 목표
고령자 건강정보 블로그. 글 작성·조회·좋아요 + 인증 + RLS 보안.

## 스택
- Next.js + TypeScript
- Supabase (Postgres + Auth + RLS)
- 배포: Vercel

## 핵심 규칙
- **RLS는 반드시 건다.** 테이블 만들면 바로 RLS 정책 설정. 정책 없는 테이블 금지.
- 자기 글만 수정·삭제 가능. 읽기는 공개, 쓰기는 로그인 필요.
- **service_role key는 절대 프런트엔드·git에 노출 금지.** anon key만 클라이언트 사용.
- `.env.local`은 .gitignore에 포함되어 있어야 함.
- 콘텐츠는 고령자 건강정보. ../../packages/shared/data 를 소스로 활용 가능.
- 화면은 큰 글씨·큰 버튼·쉬운 문장. 글 끝에 "참고용, 의사 상담 권장" 고지.

## 명령어
- `npm run dev` : 로컬 개발
- `npm run build` : 빌드 확인

## 보안 체크
- RLS 정책 만든 뒤 "남의 글 수정 시도가 막히는지" 반드시 테스트할 것.
