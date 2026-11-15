-- Fragilee: what the founder wrote about the startup (concept, vision and so on), saved next to each analysis.
-- Run once in the Supabase dashboard: SQL Editor > New query > paste > Run. Safe to run twice.
-- Run it BEFORE using the new question flow, otherwise saving an analysis with these answers will fail.

alter table public.analyses add column if not exists context jsonb;

-- Same protection as input and result: a size limit so nobody can store huge blobs.
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'analyses_context_size') then
    alter table public.analyses
      add constraint analyses_context_size check (context is null or pg_column_size(context) < 16384);
  end if;
end $$;

-- Nothing else changes: row-level security still applies to the whole row, and there is still no update policy.
-- The table-level grants from 001 already cover the new column.
