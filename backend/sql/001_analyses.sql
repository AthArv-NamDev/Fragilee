-- Fragilee: saved analyses with row-level security.
-- Run once in the Supabase dashboard: SQL Editor > New query > paste > Run.

create table if not exists public.analyses (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  parent_id   uuid references public.analyses (id) on delete set null,   -- set when a re-run is saved as a new version
  stage       text not null check (stage in ('stage1', 'stage2')),
  title       text not null check (char_length(title) between 1 and 80),
  input       jsonb not null,
  result      jsonb not null,
  band        text not null check (band in ('Low', 'Medium', 'High', 'Critical')),
  probability numeric(4, 3) not null check (probability between 0 and 1),
  created_at  timestamptz not null default now(),
  constraint analyses_payload_size check (pg_column_size(input) < 8192 and pg_column_size(result) < 32768)
);

create index if not exists analyses_user_created_idx on public.analyses (user_id, created_at desc);

alter table public.analyses enable row level security;

-- Rows are private: a signed-in user can only see, add or delete their own.
-- There is deliberately NO update policy: a saved analysis never changes. Editing saves a new version.
create policy "analyses_select_own" on public.analyses
  for select to authenticated
  using (user_id = (select auth.uid()));

-- A policy cannot query its own table directly (Postgres reports infinite recursion), so the
-- "is this parent mine?" check lives in a small function. It only ever answers true or false
-- about the caller's own rows, so it leaks nothing.
create or replace function public.owns_analysis(p_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.analyses a where a.id = p_id and a.user_id = (select auth.uid()))
$$;
revoke all on function public.owns_analysis(uuid) from public, anon;
grant execute on function public.owns_analysis(uuid) to authenticated;

create policy "analyses_insert_own" on public.analyses
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and (parent_id is null or public.owns_analysis(parent_id))
  );

create policy "analyses_delete_own" on public.analyses
  for delete to authenticated
  using (user_id = (select auth.uid()));

-- Table privileges: anonymous visitors get nothing; signed-in users can read, add and delete (no update).
revoke all on public.analyses from anon, authenticated;
grant select, insert, delete on public.analyses to authenticated;
