"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { apiFetch } from "@/lib/api";
import type { CasesResponse, EvidenceResponse } from "@/lib/types";
import EvidenceResults from "@/components/EvidenceResults";

const month = (iso: string) => new Date(iso + (iso.length === 7 ? "-01" : "")).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });

export default function CasesPanel({ data, analysisId, researchNode }: { data: CasesResponse | null; analysisId: string; researchNode: string }) {
  const [research, setResearch] = useState<EvidenceResponse | null>(null);
  const [researchState, setResearchState] = useState<"loading" | "ready" | "unavailable">("loading");
  const [query, setQuery] = useState("");
  const [reason, setReason] = useState("all");
  const reduce = useReducedMotion();

  useEffect(() => {
    let current = true;
    const focus = researchNode.toLowerCase().includes("market") ? "Market" : "Industry";
    apiFetch<EvidenceResponse>(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence?node=${encodeURIComponent(researchNode)}&focus=${focus}`)
      .then((value) => { if (current) { setResearch(value); setResearchState("ready"); } })
      .catch(() => { if (current) setResearchState("unavailable"); });
    return () => { current = false; };
  }, [analysisId, researchNode]);

  const commonReasons = useMemo(() => {
    if (!data) return [];
    const counts = new Map<string, number>();
    for (const item of data.cases) for (const label of item.reasons) counts.set(label, (counts.get(label) ?? 0) + 1);
    return [...counts].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([label]) => label);
  }, [data]);
  const caseLinks = useMemo(() => {
    if (!data) return [];
    const links: { from: string; to: string; shared: string[] }[] = [];
    for (let i = 0; i < data.cases.length; i++) for (let j = i + 1; j < data.cases.length; j++) {
      const a = data.cases[i], b = data.cases[j];
      const shared = a.reasons.filter((reason) => b.reasons.includes(reason));
      if (shared.length) links.push({ from: a.id, to: b.id, shared });
    }
    return links;
  }, [data]);
  const visibleCases = useMemo(() => {
    if (!data) return [];
    const needle = query.trim().toLowerCase();
    return data.cases.filter((item) => {
      const text = [item.name, item.sector, item.what, item.how_it_failed, ...item.reasons, ...item.matched_on].join(" ").toLowerCase();
      return (!needle || text.includes(needle)) && (reason === "all" || item.reasons.includes(reason));
    });
  }, [data, query, reason]);

  if (!data) return <div className="rounded-3xl border border-ink/10 bg-dark-surface p-6" role="status"><p className="eyebrow text-coral">Historical cases</p><h2 className="mt-2 font-display text-2xl">Stories are taking a break.</h2><p className="mt-2 text-sm text-muted">We could not load the case library right now. Your saved analysis is still available.</p></div>;

  return <div className="space-y-10">
    <section aria-labelledby="research-title" className="relative overflow-hidden rounded-[26px] border border-coral/20 bg-dark-surface p-5 md:p-8">
      <div aria-hidden="true" className="pointer-events-none absolute -right-10 -top-16 size-48 rounded-full bg-coral/10 blur-3xl"/>
      <div className="relative flex flex-wrap items-start justify-between gap-4">
        <div><p className="eyebrow text-coral">Research · separate from the model</p><h2 id="research-title" className="mt-2 font-display text-2xl md:text-3xl">Studies around {researchNode.toLowerCase()}</h2><p className="mt-2 max-w-2xl text-sm text-muted">External papers are context for further reading. They do not confirm that their findings apply to this startup.</p></div>
        <span className="rounded-full border border-ink/10 px-3 py-1.5 text-xs text-muted">OpenAlex · live lookup</span>
      </div>
      {(researchState === "loading" || (researchState === "ready" && research?.node !== researchNode)) && <div className="mt-6 flex items-center gap-3 text-sm text-muted" role="status"><span className="size-2 animate-pulse rounded-full bg-coral"/>Searching the research index…</div>}
      {researchState === "unavailable" && <p className="mt-6 rounded-xl bg-ink/5 p-4 text-sm text-muted" role="status">The research service is unavailable right now. The case library below remains available.</p>}
      {researchState === "ready" && research?.node === researchNode && <>
        <p className="mt-4 text-xs text-muted">{research.note}</p>
        {research.sources.length ? <EvidenceResults sources={research.sources}/> : <p className="mt-4 rounded-xl bg-ink/5 p-4 text-sm">No source passed the relevance check for this research query.</p>}
        <p className="mt-4 text-xs leading-relaxed text-muted">Open each paper to review its methods, sample and limits. A source match is not proof of a startup-specific risk.</p>
      </>}
    </section>

    <section aria-labelledby="cases-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><p className="eyebrow text-lime">Historical company cases</p><h2 id="cases-title" className="mt-2 font-display text-3xl md:text-4xl">How some failed earlier</h2><p className="mt-2 max-w-2xl text-sm text-muted">Cases are retrieved from the curated library. Shared traits are clues for comparison, not evidence that a matching factor caused closure.</p></div>
        <span className="rounded-full bg-ink/5 px-3 py-1.5 text-xs tabular-nums text-muted">{visibleCases.length} of {data.cases.length} cases</span>
      </div>

      {visibleCases.length > 1 && <div className="mt-6 rounded-[22px] border border-ink/10 bg-dark-surface p-4 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="eyebrow text-coral">Explore the returned set</p><h3 className="mt-1 font-display text-xl">Shared reported themes</h3></div><p className="max-w-sm text-xs leading-relaxed text-muted">A line means the curated records share at least one reason label. It is a navigation aid, not proof of comparability or cause.</p></div>
        <div className="mt-4 overflow-x-auto">
          <svg viewBox="0 0 720 180" className="mx-auto block min-w-[520px] max-w-3xl" role="group" aria-label={`Network of ${visibleCases.length} returned historical cases. Lines show only shared reason labels.`}>
            {caseLinks.filter((link) => visibleCases.some((item) => item.id === link.from) && visibleCases.some((item) => item.id === link.to)).map((link) => {
              const a = visibleCases.findIndex((item) => item.id === link.from), b = visibleCases.findIndex((item) => item.id === link.to);
              const x1 = 48 + (a * 624) / Math.max(visibleCases.length - 1, 1), x2 = 48 + (b * 624) / Math.max(visibleCases.length - 1, 1);
              const y1 = 83 + (a % 2 ? 22 : -22), y2 = 83 + (b % 2 ? 22 : -22);
              return <path key={`${link.from}-${link.to}`} d={`M${x1} ${y1} Q ${(x1 + x2) / 2} ${Math.min(y1, y2) - 25} ${x2} ${y2}`} fill="none" stroke="var(--coral)" strokeOpacity=".42" strokeWidth="1.5" strokeDasharray="3 4"><title>Shared reported labels: {link.shared.join(", ")}</title></path>;
            })}
            {visibleCases.map((item, index) => {
              const x = 48 + (index * 624) / Math.max(visibleCases.length - 1, 1), y = 83 + (index % 2 ? 22 : -22);
              return <g key={item.id}>
                <a href={`#case-${item.id}`} aria-label={`Go to ${item.name} historical case`}>
                  <circle cx={x} cy={y} r="17" fill="var(--surface-2)" stroke="var(--coral)" strokeWidth="1.5"/>
                  <circle cx={x - 4} cy={y - 5} r="4" fill="var(--cream)" opacity=".75"/>
                  <text x={x} y={y + 34} textAnchor="middle" fill="var(--text)" fontSize="10" fontWeight="600">{item.name.length > 18 ? `${item.name.slice(0, 16)}…` : item.name}</text>
                  <text x={x} y={y + 47} textAnchor="middle" fill="var(--muted)" fontSize="8">{item.years}</text>
                </a>
              </g>;
            })}
          </svg>
        </div>
      </div>}

      {data.cases.length > 0 && <div className="mt-6 grid gap-3 md:grid-cols-[minmax(220px,1fr)_2fr]">
        <label className="relative block"><span className="sr-only">Search historical cases</span><span aria-hidden="true" className="absolute left-4 top-1/2 -translate-y-1/2 text-muted">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search cases or matched terms" className="min-h-12 w-full rounded-full border border-ink/15 bg-dark-surface pl-11 pr-4 text-sm placeholder:text-muted focus:border-coral focus:outline-none focus-visible:ring-2 focus-visible:ring-coral"/></label>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter cases by reported theme">
          {["all", ...commonReasons].map((label) => <button key={label} type="button" aria-pressed={reason === label} onClick={() => setReason(label)} className="min-h-11 rounded-full border border-ink/15 px-4 text-xs transition-colors hover:border-coral aria-pressed:border-coral aria-pressed:bg-coral-soft aria-pressed:text-text focus-visible:outline-2 focus-visible:outline-coral">{label === "all" ? "All themes" : label}</button>)}
        </div>
      </div>}

      {data.cases.length === 0 ? <div className="mt-6 rounded-2xl border border-dashed border-ink/20 p-7"><h3 className="font-display text-xl">No close case was found.</h3><p className="mt-2 max-w-2xl text-sm text-muted">{data.note || "We leave this empty instead of filling the comparison with unrelated companies."}</p></div>
        : visibleCases.length === 0 ? <p className="mt-6 rounded-2xl bg-dark-surface p-6 text-sm text-muted">No cases match this search. Clear the text or choose another theme.</p>
        : <ul className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {visibleCases.map((item, index) => <motion.li key={item.id} id={`case-${item.id}`} className="analysis-card relative flex scroll-mt-28 flex-col overflow-hidden rounded-[22px] border border-ink/10 bg-dark-surface p-5"
            initial={reduce ? false : { opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-24px" }} transition={{ duration: reduce ? 0 : .32, delay: Math.min(index * .045, .18), ease: "easeOut" }}>
            <span aria-hidden="true" className={`absolute right-4 top-3 font-display text-6xl ${index % 2 ? "text-lime/20" : "text-coral/20"}`}>{String(index + 1).padStart(2, "0")}</span>
            <div className="relative flex items-start justify-between gap-3"><div><p className="eyebrow text-muted">{item.sector}</p><h3 className="mt-2 max-w-[18ch] break-words font-display text-2xl">{item.name}</h3></div><span className="shrink-0 rounded-full border border-ink/10 px-2.5 py-1 text-[11px] text-muted">{item.years}</span></div>
            <p className="mt-4 text-sm leading-relaxed text-text/85">{item.what}</p>
            <div className="mt-4 rounded-xl bg-brand-coral-soft p-4"><p className="eyebrow text-coral">Reported in sources</p><p className="mt-2 text-sm leading-relaxed">{item.how_it_failed}</p></div>
            <div className="mt-4 flex flex-wrap gap-1.5">{item.reasons.map((tag) => <button type="button" key={tag} onClick={() => setReason(tag)} className="min-h-8 rounded-full border border-ink/10 px-2.5 text-[11px] text-muted transition-colors hover:border-coral focus-visible:outline-2 focus-visible:outline-coral">{tag}</button>)}</div>
            <p className="mt-4 text-[11px] text-muted">Matched on: {item.matched_on.join(" · ") || "No match details available"}</p>
            <details className="mt-auto border-t border-ink/10 pt-4">
              <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 text-sm font-semibold">Read source trail <span className="text-coral" aria-hidden="true">＋</span></summary>
              <ul className="mt-2 space-y-3">{item.sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium underline decoration-coral/60 underline-offset-4 hover:text-coral">{source.title}<span aria-hidden="true"> ↗</span></a><p className="mt-1 text-xs text-muted">{source.publisher} · {month(source.published)}</p></li>)}</ul>
              {!item.sources.length && <p className="text-xs text-muted">No source links are available for this case record.</p>}
              <p className="mt-3 text-[11px] text-muted">Summaries are curated from linked reporting. Read the original sources; a reported challenge does not establish the cause of closure.</p>
            </details>
          </motion.li>)}
        </ul>}
      <p className="mt-5 text-xs text-muted">Historical comparisons are separate from academic research and do not predict this startup&apos;s outcome.</p>
    </section>
  </div>;
}
