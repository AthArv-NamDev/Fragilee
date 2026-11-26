-- Phase 4C: make deterministic comparison creation idempotent per saved pair.
-- Requires 004_claim_evidence.sql. This is additive and does not edit old records.
-- Apply manually after confirming the target Supabase project and migration 004.

create unique index if not exists evidence_contradictions_deterministic_pair_once_idx
  on public.evidence_contradictions (
    analysis_id,
    least(association_1_id, association_2_id),
    greatest(association_1_id, association_2_id)
  )
  where supersedes_record_id is null
    and payload->>'detection_method' = 'deterministic_excerpt_rules';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'evidence_contradictions_generated_payload_valid'
      and conrelid = 'public.evidence_contradictions'::regclass
  ) then
    alter table public.evidence_contradictions
      add constraint evidence_contradictions_generated_payload_valid check (
        payload->>'detection_method' is distinct from 'deterministic_excerpt_rules'
        or (
          coalesce(payload->>'relationship', '') in ('supports', 'partially_supports', 'contextualizes', 'contradicts', 'insufficient')
          and coalesce(payload->>'assessment_text', '') <> ''
          and coalesce(payload->>'uncertainty_explanation', '') <> ''
          and coalesce(jsonb_typeof(payload->'context_differences'), '') = 'array'
          and coalesce(jsonb_typeof(payload->'methodological_differences'), '') = 'array'
          and coalesce(jsonb_typeof(payload->'measurement_differences'), '') = 'array'
          and coalesce(jsonb_typeof(payload->'population_differences'), '') = 'array'
          and coalesce(jsonb_typeof(payload->'geographic_differences'), '') = 'array'
          and coalesce(jsonb_typeof(payload->'time_period_differences'), '') = 'array'
          and coalesce(jsonb_typeof(payload->'source_access_limitations'), '') = 'array'
          and (
            supersedes_record_id is not null
            or (coalesce(payload->>'verification_state', '') = 'pending_review'
              and coalesce(payload->>'verification_method', '') = 'none'
              and payload->>'reviewer_id' is null)
          )
        )
      );
  end if;
end $$;
