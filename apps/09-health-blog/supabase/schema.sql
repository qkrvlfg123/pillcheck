-- ============================================================
-- 필체크 건강 블로그 — DB 스키마 + RLS 보안 정책
-- ============================================================
-- 사용법: Supabase 대시보드 → SQL Editor → 아래 전체 붙여넣고 Run
--
-- 이 챕터(9장)의 핵심은 RLS(Row Level Security)입니다.
-- RLS가 없으면 anon key만 있으면 누구나 남의 글을 수정·삭제할 수 있습니다.
-- 아래 정책이 "누가 어떤 행을 읽고 쓸 수 있는가"를 DB 레벨에서 강제합니다.
-- ============================================================

-- ── 1. posts 테이블 (글) ──────────────────────────────────
create table if not exists public.posts (
  id          uuid primary key default gen_random_uuid(),
  title       text not null,
  content     text not null,
  author_id   uuid not null references auth.users(id) on delete cascade,
  author_email text,
  likes_count int not null default 0,
  created_at  timestamptz not null default now()
);

-- ── 2. likes 테이블 (좋아요, 한 사람이 한 글에 한 번) ──────
create table if not exists public.likes (
  id       uuid primary key default gen_random_uuid(),
  post_id  uuid not null references public.posts(id) on delete cascade,
  user_id  uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (post_id, user_id)   -- 중복 좋아요 방지
);

-- ── 3. RLS 활성화 (이걸 켜야 아래 정책이 적용됨) ───────────
alter table public.posts enable row level security;
alter table public.likes enable row level security;

-- ── 4. posts 정책 ─────────────────────────────────────────
-- 읽기: 누구나 가능 (블로그니까 공개)
create policy "글은 누구나 읽을 수 있다"
  on public.posts for select
  using (true);

-- 쓰기: 로그인한 사용자만, 그리고 author_id가 본인이어야
create policy "로그인 사용자만 글을 쓸 수 있다"
  on public.posts for insert
  with check (auth.uid() = author_id);

-- 수정: 본인 글만
create policy "본인 글만 수정할 수 있다"
  on public.posts for update
  using (auth.uid() = author_id);

-- 삭제: 본인 글만
create policy "본인 글만 삭제할 수 있다"
  on public.posts for delete
  using (auth.uid() = author_id);

-- ── 5. likes 정책 ─────────────────────────────────────────
-- 읽기: 누구나 (좋아요 수 표시용)
create policy "좋아요는 누구나 읽을 수 있다"
  on public.likes for select
  using (true);

-- 추가: 로그인 사용자만, 본인 user_id로만
create policy "로그인 사용자만 좋아요를 누를 수 있다"
  on public.likes for insert
  with check (auth.uid() = user_id);

-- 취소: 본인 좋아요만
create policy "본인 좋아요만 취소할 수 있다"
  on public.likes for delete
  using (auth.uid() = user_id);

-- ── 6. 좋아요 수 자동 갱신 (트리거) ───────────────────────
-- likes에 행이 추가/삭제되면 posts.likes_count를 자동으로 맞춘다.
create or replace function public.update_likes_count()
returns trigger
language plpgsql
security definer
as $$
begin
  if (TG_OP = 'INSERT') then
    update public.posts set likes_count = likes_count + 1 where id = NEW.post_id;
    return NEW;
  elsif (TG_OP = 'DELETE') then
    update public.posts set likes_count = greatest(likes_count - 1, 0) where id = OLD.post_id;
    return OLD;
  end if;
  return null;
end;
$$;

drop trigger if exists likes_count_trigger on public.likes;
create trigger likes_count_trigger
  after insert or delete on public.likes
  for each row execute function public.update_likes_count();

-- ============================================================
-- 완료! 이제 RLS가 적용됩니다.
--
-- 확인 방법: 로그인 A로 글을 쓰고, 로그인 B로 그 글을 수정 시도하면
-- 막혀야 정상입니다. (본인 글만 수정 가능)
-- ============================================================
