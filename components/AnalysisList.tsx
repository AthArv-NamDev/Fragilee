"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { AnalysisSummary } from "@/lib/types";
import DeleteButton from "./DeleteButton";

const date = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const PAGE_LIMIT = 50;

const stageName = (stage: AnalysisSummary["stage"]) => stage === "stage1" ? "Level 1 · Place + industry" : "Level 2 · Funding + company data";

export default function AnalysisList({ items }: { items: AnalysisSummary[] }) {
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<"all" | AnalysisSummary["stage"]>("all");
  const counts = useMemo(() => ({
    total: items.length,
    level1: items.filter((item) => item.stage === "stage1").length,
    level2: items.filter((item) => item.stage === "stage2").length,
  }), [items]);
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return items.filter((item) => (!needle || item.title.toLowerCase().includes(needle)) && (stage === "all" || item.stage === stage));
  }, [items, query, stage]);

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-ink/20 p-10 text-center">
        <h2 className="font-display text-2xl mb-2">Your startup journey starts here.</h2>
        <p className="mx-auto max-w-xl text-muted mb-6">Create your first analysis to explore historical patterns and identify assumptions worth validating.</p>
        <Link href="/new" className="inline-flex min-h-12 items-center rounded-full bg-sage px-6 font-semibold button-label-on-sage">Test your idea</Link>
      </div>
    );
  }

  const childVersions = new Map<string, number>();
  for (const item of items) if (item.parent_id) childVersions.set(item.parent_id, (childVersions.get(item.parent_id) ?? 0) + 1);

  return (
    <div>
      <section aria-label="Loaded analysis counts" className="mb-7 grid grid-cols-3 gap-2 md:gap-3">
        {[["Saved reads", counts.total], ["Level 1", counts.level1], ["Level 2", counts.level2]].map(([label, count]) => <div key={label} className="rounded-2xl border border-ink/10 bg-dark-surface px-4 py-4 md:px-5"><p className="eyebrow text-muted">{label}</p><p className="mt-2 font-display text-3xl tabular-nums md:text-4xl">{count}</p></div>)}
      </section>
      <div className="mb-5 grid gap-3 md:grid-cols-[minmax(240px,1fr)_auto]">
        <label className="relative block"><span className="sr-only">Search saved analyses by name</span><span aria-hidden="true" className="absolute left-4 top-1/2 -translate-y-1/2 text-muted">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a saved idea" className="min-h-12 w-full rounded-full border border-ink/15 bg-dark-surface pl-11 pr-4 text-sm placeholder:text-muted focus:border-coral focus:outline-none focus-visible:ring-2 focus-visible:ring-coral"/></label>
        <div className="flex gap-2" role="group" aria-label="Filter saved analyses by level">{([["all", "All levels"], ["stage1", "Level 1"], ["stage2", "Level 2"]] as const).map(([id, label]) => <button key={id} type="button" aria-pressed={stage === id} onClick={() => setStage(id)} className="min-h-11 rounded-full border border-ink/15 px-4 text-xs font-semibold transition-colors hover:border-coral aria-pressed:border-coral aria-pressed:bg-coral aria-pressed:text-coral-ink focus-visible:outline-2 focus-visible:outline-coral">{label}</button>)}</div>
      </div>
      {visible.length === 0 ? <div className="rounded-2xl border border-dashed border-ink/20 p-8 text-center"><h2 className="font-display text-2xl">No saved read matches.</h2><p className="mt-2 text-sm text-muted">Change the search or show all levels.</p></div> : <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {visible.map((analysis) => {
        const versions = childVersions.get(analysis.id) ?? 0;
        return (
          <li key={analysis.id} className="analysis-card flex min-h-[190px] flex-col gap-3 rounded-[18px] border border-ink/10 bg-dark-surface p-[22px]">
            <Link href={`/analysis/${analysis.id}`} className="group flex flex-1 flex-col gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet">
              <div className="flex items-center gap-4">
                <span className="grid size-[74px] shrink-0 place-items-center rounded-full border-2 border-violet/40 text-violet" aria-label={stageName(analysis.stage)}>
                  <span className="font-display text-lg">{analysis.stage === "stage1" ? "L1" : "L2"}</span>
                </span>
                <span className="font-display text-[19px] leading-[1.15] tracking-tight group-hover:text-violet break-words">{analysis.title}</span>
              </div>
              <span className="flex flex-wrap gap-2">
                <span className="rounded-full border border-violet/30 bg-violet/10 px-3 py-1 text-xs text-violet-text">{stageName(analysis.stage)}</span>
                <time dateTime={analysis.created_at} className="rounded-full border border-ink/10 bg-ink/5 px-3 py-1 text-xs text-muted">{date(analysis.created_at)}</time>
              </span>
              <span className="mt-auto text-sm text-muted">Open the saved inputs, model trace, and supporting evidence <span aria-hidden="true">→</span></span>
            </Link>
            <div className="flex items-center justify-between gap-2 border-t border-ink/10 pt-3">
              <p className="min-h-5 text-xs text-violet-text">{versions > 0 ? `Has ${versions} newer ${versions === 1 ? "version" : "versions"}` : "Saved analysis"}</p>
              <DeleteButton id={analysis.id} title={analysis.title} />
            </div>
          </li>
        );
      })}
      <li>
        <Link href="/new" className="flex min-h-[190px] h-full flex-col items-center justify-center gap-2 rounded-[18px] border-[1.5px] border-dashed border-ink/20 p-5 text-center text-muted transition-colors hover:border-violet hover:text-text focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet">
          <span className="grid size-[46px] place-items-center rounded-full border border-ink/20 text-2xl text-text" aria-hidden="true">+</span>
          <span><b className="text-text">New analysis</b><br />Start with your idea</span>
        </Link>
      </li>
      </ul>}
      <p className="mt-4 text-xs text-muted">Counts reflect the latest {PAGE_LIMIT} analyses loaded for this view, not your full account history.</p>
    </div>
  );
}
