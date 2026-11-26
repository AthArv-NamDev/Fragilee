-- Append-only research retrieval snapshots. Apply manually in Supabase SQL Editor.
-- Saved analyses remain immutable; research is stored separately so it cannot affect scoring.
create table if not exists public.evidence_snapshots (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid not null references public.analyses(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  node text not null check (char_length(node) between 1 and 100),
  focus text not null check (focus in ('Market', 'Industry', 'Funding', 'Traction', 'Location')),
  payload jsonb not null,
  created_at timestamptz not null default now(),
  constraint evidence_snapshots_payload_size check (pg_column_size(payload) < 1048576),
  constraint evidence_snapshots_owner_matches_analysis check (public.owns_analysis(analysis_id))
);

create index if not exists evidence_snapshots_latest_idx
  on public.evidence_snapshots (analysis_id, node, focus, created_at desc, id desc);

alter table public.evidence_snapshots enable row level security;
revoke all on public.evidence_snapshots from anon, authenticated;
grant select, insert on public.evidence_snapshots to authenticated;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'evidence_snapshots' and policyname = 'evidence_snapshots_select_own') then
    create policy "evidence_snapshots_select_own" on public.evidence_snapshots
      for select to authenticated
      using (user_id = (select auth.uid()) and public.owns_analysis(analysis_id));
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'evidence_snapshots' and policyname = 'evidence_snapshots_insert_own') then
    create policy "evidence_snapshots_insert_own" on public.evidence_snapshots
      for insert to authenticated
      with check (user_id = (select auth.uid()) and public.owns_analysis(analysis_id));
  end if;
end $$;
-- No update or delete policy: a refresh appends a record. Analysis deletion cascades its snapshots.
