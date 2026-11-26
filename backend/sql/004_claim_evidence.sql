-- Phase 4B claim-level evidence and contradiction review.
-- Apply manually after reviewing. This migration does not modify analyses or saved snapshots.

create unique index if not exists evidence_snapshots_analysis_id_id_uq
  on public.evidence_snapshots (analysis_id, id);

create table if not exists public.evidence_associations (
  id uuid primary key,
  analysis_id uuid not null references public.analyses(id) on delete cascade,
  snapshot_id uuid not null,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  supersedes_record_id uuid,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  constraint evidence_associations_snapshot_same_analysis
    foreign key (analysis_id, snapshot_id)
    references public.evidence_snapshots (analysis_id, id) on delete cascade,
  constraint evidence_associations_payload_size check (pg_column_size(payload) < 65536),
  constraint evidence_associations_owner_matches_analysis check (public.owns_analysis(analysis_id)),
  constraint evidence_associations_unique_record_per_analysis unique (analysis_id, id),
  constraint evidence_associations_supersedes_same_analysis
    foreign key (analysis_id, supersedes_record_id)
    references public.evidence_associations (analysis_id, id) on delete cascade
);

create index if not exists evidence_associations_analysis_created_idx
  on public.evidence_associations (analysis_id, created_at desc, id desc);
create index if not exists evidence_associations_snapshot_idx
  on public.evidence_associations (analysis_id, snapshot_id, created_at desc);
create unique index if not exists evidence_associations_one_correction_idx
  on public.evidence_associations (analysis_id, supersedes_record_id)
  where supersedes_record_id is not null;

create or replace function public.validate_evidence_association_insert()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_snapshot_payload jsonb;
  v_source jsonb;
  v_source_id text;
  v_access text;
  v_passage text;
  v_previous public.evidence_associations%rowtype;
begin
  if new.user_id <> (select auth.uid()) or not public.owns_analysis(new.analysis_id) then
    raise exception 'analysis ownership validation failed' using errcode = '42501';
  end if;
  if new.payload->>'record_id' is distinct from new.id::text
     or new.payload->>'analysis_id' is distinct from new.analysis_id::text
     or new.payload->>'snapshot_id' is distinct from new.snapshot_id::text
     or new.payload->>'supersedes_record_id' is distinct from new.supersedes_record_id::text
     or coalesce(new.payload->>'contract_version', '') <> '1.0'
     or coalesce(new.payload->>'claim_category', '') not in ('historical_case_fact', 'general_research_finding', 'startup_specific_interpretation', 'recommendation')
     or coalesce(new.payload->>'relationship', '') not in ('supports', 'partially_supports', 'contextualizes', 'contradicts', 'insufficient')
     or coalesce(new.payload->>'verification_state', '') not in ('pending_review', 'verified', 'rejected', 'not_assessed') then
    raise exception 'association payload identity does not match storage columns' using errcode = '23514';
  end if;

  select s.payload into v_snapshot_payload
    from public.evidence_snapshots s
    where s.id = new.snapshot_id and s.analysis_id = new.analysis_id;
  if v_snapshot_payload is null then
    raise exception 'evidence snapshot does not belong to analysis' using errcode = '23503';
  end if;

  v_source_id := new.payload->>'source_id';
  select elem.value into v_source
    from jsonb_array_elements(coalesce(v_snapshot_payload->'sources', '[]'::jsonb)) as elem(value)
    where lower(coalesce(elem.value->>'openalex_id', '')) = lower(v_source_id)
       or lower(coalesce(elem.value->>'doi', '')) = lower(v_source_id)
       or lower(coalesce(elem.value->>'url', '')) = lower(v_source_id)
    limit 1;
  if v_source is null then
    raise exception 'source does not exist in evidence snapshot' using errcode = '23514';
  end if;
  if new.payload->>'source_url' is distinct from v_source->>'url' then
    raise exception 'source URL does not match evidence snapshot' using errcode = '23514';
  end if;
  if new.payload->'publication'->>'title' is distinct from v_source->>'title'
     or new.payload->'publication'->>'publisher' is distinct from v_source->>'publisher'
     or new.payload->'publication'->>'journal' is distinct from v_source->>'journal'
     or new.payload->'publication'->'authors' is distinct from coalesce(v_source->'authors', '[]'::jsonb)
     or new.payload->'publication'->>'doi' is distinct from v_source->>'doi'
     or new.payload->'publication'->>'published' is distinct from v_source->>'published'
     or new.payload->'publication'->>'year' is distinct from v_source->>'year' then
    raise exception 'publication metadata does not match evidence snapshot' using errcode = '23514';
  end if;

  v_access := new.payload->>'source_access';
  v_passage := new.payload->>'exact_passage_text';
  if v_access = 'abstract_excerpt' then
    if v_source->>'access_status' <> 'abstract_only' or v_passage is distinct from v_source->>'excerpt' then
      raise exception 'abstract excerpt does not match saved source text' using errcode = '23514';
    end if;
  elsif v_access = 'metadata_only' then
    if v_source->>'access_status' <> 'metadata_only' or v_passage is not null then
      raise exception 'metadata-only source cannot assert a passage' using errcode = '23514';
    end if;
  elsif v_access = 'inaccessible' then
    if coalesce(v_source->>'access_status', '') not in ('metadata_only', 'inaccessible') or v_passage is not null then
      raise exception 'source access status does not establish an inaccessible source' using errcode = '23514';
    end if;
  elsif v_access = 'full_text_passage' then
    if v_source->>'access_status' <> 'full_text_reviewed'
       or coalesce(new.payload->>'passage_location', '') = ''
       or not exists (
         select 1 from jsonb_array_elements(coalesce(v_source->'full_text_passages', '[]'::jsonb)) as passage(value)
         where passage.value->>'text' = v_passage and passage.value->>'location' = new.payload->>'passage_location'
       ) then
      raise exception 'inspected full-text passage/location not present in snapshot' using errcode = '23514';
    end if;
  else
    raise exception 'invalid source access state' using errcode = '23514';
  end if;

  if new.payload->>'relationship' in ('supports', 'partially_supports', 'contradicts')
     and coalesce(v_passage, '') = '' then
    raise exception 'passage relationship requires inspected source text' using errcode = '23514';
  end if;

  if new.payload->>'verification_state' = 'verified'
     and (new.payload->>'verification_method' <> 'human_review'
       or coalesce(new.payload->>'reviewer_id', '') = ''
       or new.payload->>'reviewer_id' <> new.user_id::text
       or new.payload->>'verified_at' is null) then
    raise exception 'verified association requires human reviewer provenance' using errcode = '23514';
  end if;
  if new.payload->>'verification_state' = 'rejected'
     and (new.payload->>'verification_method' <> 'human_review'
       or coalesce(new.payload->>'reviewer_id', '') = ''
       or new.payload->>'reviewer_id' <> new.user_id::text
       or new.payload->>'reviewed_at' is null) then
    raise exception 'rejected association requires human reviewer provenance' using errcode = '23514';
  end if;
  if new.payload->>'verification_method' = 'ai_assisted'
     and new.payload->>'verification_state' in ('verified', 'rejected') then
    raise exception 'AI assessment cannot be human verified or rejected' using errcode = '23514';
  end if;
  if new.payload->>'reviewer_id' is not null
     and new.payload->>'reviewer_id' <> new.user_id::text then
    raise exception 'reviewer identity must match authenticated user' using errcode = '42501';
  end if;

  if new.supersedes_record_id is not null then
    select * into v_previous from public.evidence_associations a
      where a.id = new.supersedes_record_id and a.analysis_id = new.analysis_id;
    if not found or v_previous.user_id <> new.user_id or v_previous.snapshot_id <> new.snapshot_id then
      raise exception 'correction target must belong to same user, analysis and snapshot' using errcode = '23514';
    end if;
    if exists (select 1 from public.evidence_associations a
      where a.analysis_id = new.analysis_id and a.supersedes_record_id = new.supersedes_record_id) then
      raise exception 'correction target already superseded' using errcode = '23514';
    end if;
  end if;
  return new;
end $$;

revoke all on function public.validate_evidence_association_insert() from public, anon, authenticated;
create trigger evidence_associations_validate_insert
  before insert on public.evidence_associations
  for each row execute function public.validate_evidence_association_insert();

alter table public.evidence_associations enable row level security;
revoke all on public.evidence_associations from anon, authenticated;
grant select, insert on public.evidence_associations to authenticated;
create policy evidence_associations_select_own on public.evidence_associations
  for select to authenticated using (user_id = (select auth.uid()) and public.owns_analysis(analysis_id));
create policy evidence_associations_insert_own on public.evidence_associations
  for insert to authenticated with check (user_id = (select auth.uid()) and public.owns_analysis(analysis_id));

create table if not exists public.evidence_contradictions (
  id uuid primary key,
  analysis_id uuid not null references public.analyses(id) on delete cascade,
  association_1_id uuid not null,
  association_2_id uuid not null,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  supersedes_record_id uuid,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  constraint evidence_contradictions_distinct_associations check (association_1_id <> association_2_id),
  constraint evidence_contradictions_first_same_analysis foreign key (analysis_id, association_1_id)
    references public.evidence_associations (analysis_id, id) on delete cascade,
  constraint evidence_contradictions_second_same_analysis foreign key (analysis_id, association_2_id)
    references public.evidence_associations (analysis_id, id) on delete cascade,
  constraint evidence_contradictions_supersedes_same_analysis foreign key (analysis_id, supersedes_record_id)
    references public.evidence_contradictions (analysis_id, id) on delete cascade,
  constraint evidence_contradictions_payload_size check (pg_column_size(payload) < 65536),
  constraint evidence_contradictions_owner_matches_analysis check (public.owns_analysis(analysis_id)),
  constraint evidence_contradictions_unique_record_per_analysis unique (analysis_id, id)
);

create index if not exists evidence_contradictions_analysis_created_idx
  on public.evidence_contradictions (analysis_id, created_at desc, id desc);
create unique index if not exists evidence_contradictions_one_correction_idx
  on public.evidence_contradictions (analysis_id, supersedes_record_id)
  where supersedes_record_id is not null;

create or replace function public.validate_evidence_contradiction_insert()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.user_id <> (select auth.uid()) or not public.owns_analysis(new.analysis_id) then
    raise exception 'analysis ownership validation failed' using errcode = '42501';
  end if;
  if new.payload->>'record_id' is distinct from new.id::text
     or new.payload->>'analysis_id' is distinct from new.analysis_id::text
     or new.payload->>'supersedes_record_id' is distinct from new.supersedes_record_id::text
     or coalesce(new.payload->>'contract_version', '') <> '1.0'
     or coalesce(new.payload->>'nature', '') not in ('genuine_disagreement', 'different_population', 'different_geography', 'different_period', 'different_definition', 'different_methodology', 'complementary', 'insufficient_information')
     or coalesce(new.payload->>'verification_state', '') not in ('pending_review', 'verified', 'rejected', 'not_assessed') then
    raise exception 'contradiction payload identity does not match storage columns' using errcode = '23514';
  end if;
  if not exists (select 1 from public.evidence_associations a where a.id = new.association_1_id
      and a.analysis_id = new.analysis_id and a.user_id = new.user_id and coalesce(a.payload->>'exact_passage_text', '') <> '')
     or not exists (select 1 from public.evidence_associations a where a.id = new.association_2_id
      and a.analysis_id = new.analysis_id and a.user_id = new.user_id and coalesce(a.payload->>'exact_passage_text', '') <> '') then
    raise exception 'contradiction candidates require two same-analysis passage associations' using errcode = '23514';
  end if;
  if new.payload->>'verification_state' = 'verified'
     and (new.payload->>'verification_method' <> 'human_review'
       or coalesce(new.payload->>'reviewer_id', '') = ''
       or new.payload->>'reviewer_id' <> new.user_id::text
       or new.payload->>'reviewed_at' is null) then
    raise exception 'verified contradiction requires human reviewer provenance' using errcode = '23514';
  end if;
  if new.payload->>'verification_state' = 'rejected'
     and (new.payload->>'verification_method' <> 'human_review'
       or coalesce(new.payload->>'reviewer_id', '') = ''
       or new.payload->>'reviewer_id' <> new.user_id::text
       or new.payload->>'reviewed_at' is null) then
    raise exception 'rejected contradiction requires human reviewer provenance' using errcode = '23514';
  end if;
  if jsonb_array_length(coalesce(new.payload->'compared_evidence', '[]'::jsonb)) <> 2
     or not exists (
       select 1 from public.evidence_associations a
       cross join lateral jsonb_array_elements(new.payload->'compared_evidence') ref(value)
       where a.id = new.association_1_id and a.analysis_id = new.analysis_id
         and ref.value->>'association_id' = a.id::text
         and ref.value->>'snapshot_id' = a.snapshot_id::text
         and ref.value->>'source_id' = a.payload->>'source_id'
         and ref.value->>'claim_text' = a.payload->>'claim_text'
         and ref.value->>'exact_passage_text' = a.payload->>'exact_passage_text'
         and ref.value->>'passage_location' is not distinct from a.payload->>'passage_location'
         and ref.value->>'source_access' = a.payload->>'source_access'
         and ref.value->>'source_url' = a.payload->>'source_url'
         and ref.value->'publication' = a.payload->'publication'
     )
     or not exists (
       select 1 from public.evidence_associations a
       cross join lateral jsonb_array_elements(new.payload->'compared_evidence') ref(value)
       where a.id = new.association_2_id and a.analysis_id = new.analysis_id
         and ref.value->>'association_id' = a.id::text
         and ref.value->>'snapshot_id' = a.snapshot_id::text
         and ref.value->>'source_id' = a.payload->>'source_id'
         and ref.value->>'claim_text' = a.payload->>'claim_text'
         and ref.value->>'exact_passage_text' = a.payload->>'exact_passage_text'
         and ref.value->>'passage_location' is not distinct from a.payload->>'passage_location'
         and ref.value->>'source_access' = a.payload->>'source_access'
         and ref.value->>'source_url' = a.payload->>'source_url'
         and ref.value->'publication' = a.payload->'publication'
     ) then
    raise exception 'contradiction passage references do not match saved associations' using errcode = '23514';
  end if;
  if new.payload->>'verification_method' = 'ai_assisted'
     and new.payload->>'verification_state' in ('verified', 'rejected') then
    raise exception 'AI contradiction candidate cannot be verified or rejected' using errcode = '23514';
  end if;
  if new.payload->>'reviewer_id' is not null and new.payload->>'reviewer_id' <> new.user_id::text then
    raise exception 'reviewer identity must match authenticated user' using errcode = '42501';
  end if;
  if new.supersedes_record_id is not null and not exists (
    select 1 from public.evidence_contradictions c where c.id = new.supersedes_record_id
      and c.analysis_id = new.analysis_id and c.user_id = new.user_id
  ) then
    raise exception 'contradiction correction target does not belong to same user and analysis' using errcode = '23514';
  end if;
  if new.supersedes_record_id is not null and not exists (
    select 1 from public.evidence_contradictions c
    where c.id = new.supersedes_record_id and c.analysis_id = new.analysis_id
      and ((c.association_1_id = new.association_1_id and c.association_2_id = new.association_2_id)
        or (c.association_1_id = new.association_2_id and c.association_2_id = new.association_1_id))
  ) then
    raise exception 'contradiction correction must retain its evidence pair' using errcode = '23514';
  end if;
  return new;
end $$;

revoke all on function public.validate_evidence_contradiction_insert() from public, anon, authenticated;
create trigger evidence_contradictions_validate_insert
  before insert on public.evidence_contradictions
  for each row execute function public.validate_evidence_contradiction_insert();

alter table public.evidence_contradictions enable row level security;
revoke all on public.evidence_contradictions from anon, authenticated;
grant select, insert on public.evidence_contradictions to authenticated;
create policy evidence_contradictions_select_own on public.evidence_contradictions
  for select to authenticated using (user_id = (select auth.uid()) and public.owns_analysis(analysis_id));
create policy evidence_contradictions_insert_own on public.evidence_contradictions
  for insert to authenticated with check (user_id = (select auth.uid()) and public.owns_analysis(analysis_id));

-- No update/delete grants or policies: reviews and corrections append new records.
