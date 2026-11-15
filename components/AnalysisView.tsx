"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import type { Analysis, CasesResponse, Context } from "@/lib/types";
import { buildModel, summarise } from "@/lib/tree";
import PlexTree from "./tree/PlexTree";
import CasesPanel from "./CasesPanel";
import ResultTabs from "./ResultTabs";

const STAGE_LABEL: Record<NonNullable<Context["startup_stage"]>, string> = { idea: "Idea", prototype: "Prototype", launched: "Launched", earning: "Earning money" };

function Notes({ context }: { context: Context }) {
  const rows: [string, string][] = [
    ["What it does", context.concept ?? ""], ["Vision", context.vision ?? ""], ["Customer", context.customer ?? ""], ["How it makes money", context.revenue_model ?? ""],
    ["Where it is today", context.startup_stage ? STAGE_LABEL[context.startup_stage] : ""], ["Team size", context.team_size ? String(context.team_size) : ""], ["Biggest worry", context.biggest_worry ?? ""],
  ].filter(([, value]) => value) as [string, string][];
  return <div className="max-w-3xl rounded-3xl border border-ink/10 bg-dark-surface p-6 md:p-8">
    <p className="eyebrow text-coral">Founder supplied context</p>
    <h2 className="mt-2 font-display text-3xl">Your notes, kept in their lane.</h2>
    <p className="mt-2 max-w-2xl text-sm text-muted">These notes are saved with this analysis. They do not change the historical model output and have not been independently verified.</p>
    {rows.length ? <dl className="mt-6 grid gap-0 divide-y divide-ink/10 border-y border-ink/10 text-sm sm:grid-cols-[160px_1fr]">
      {rows.map(([label, value]) => <div key={label} className="contents"><dt className="py-3 text-muted">{label}</dt><dd className="py-3 whitespace-pre-line break-words">{value}</dd></div>)}
    </dl> : <p className="mt-6 text-sm text-muted">No additional founder notes were saved for this analysis.</p>}
  </div>;
}

function SignalArt({ branches }: { branches: Analysis["result"]["tree"]["children"] }) {
  const max = Math.max(...branches.map((branch) => Math.abs(branch.net_shap)), 0.0001);
  const slot = (index: number) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(branches.length, 1);
    return { x: 50 + 36 * Math.cos(angle), y: 48 + 36 * Math.sin(angle) };
  };
  return <div className="relative mx-auto aspect-square w-full max-w-[300px]" aria-label="Model contribution map">
    <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full" role="img" aria-label="Connections between startup fields represented in this historical model">
      <defs><radialGradient id="coreGlow"><stop stopColor="var(--coral)" stopOpacity=".6"/><stop offset="1" stopColor="var(--coral)" stopOpacity="0"/></radialGradient></defs>
      {branches.map((branch, index) => { const p = slot(index); return <path key={branch.group} d={`M50 48 Q ${(50 + p.x) / 2} ${(48 + p.y) / 2 - 8} ${p.x} ${p.y}`} fill="none" stroke={branch.effect === "raises" ? "var(--coral)" : branch.effect === "lowers" ? "var(--acid)" : "var(--muted)"} strokeOpacity=".7" strokeWidth=".55" strokeDasharray="1.2 1.8" />; })}
      <circle cx="50" cy="48" r="20" fill="url(#coreGlow)" />
      <circle cx="50" cy="48" r="8" fill="var(--surface)" stroke="var(--coral)" strokeWidth=".8" />
      <text x="50" y="47" textAnchor="middle" fill="var(--text)" fontSize="2.2" fontWeight="700">THIS RUN</text>
      <text x="50" y="51" textAnchor="middle" fill="var(--muted)" fontSize="1.8">MODEL TRACE</text>
      {branches.map((branch, index) => { const p = slot(index); const radius = 2.5 + 3.4 * Math.abs(branch.net_shap) / max; const color = branch.effect === "raises" ? "var(--coral)" : branch.effect === "lowers" ? "var(--acid)" : "var(--muted)"; return <g key={branch.group}>
        <title>{branch.label}: signed model contribution {branch.net_shap.toFixed(3)} log-odds</title>
        <circle cx={p.x} cy={p.y} r={radius + 2} fill={color} opacity=".1" />
        <circle cx={p.x} cy={p.y} r={radius} fill="var(--surface)" stroke={color} strokeWidth=".8" />
        <circle cx={p.x - radius * .28} cy={p.y - radius * .28} r={radius * .2} fill="var(--text)" opacity=".75" />
        <text x={p.x} y={p.y + radius + 4.5} textAnchor="middle" fill="var(--text)" fontSize="2.6" fontWeight="600">{branch.label.length > 15 ? `${branch.label.slice(0, 13)}…` : branch.label}</text>
      </g>; })}
    </svg>
    <div className="absolute bottom-0 left-1/2 flex -translate-x-1/2 items-center gap-3 whitespace-nowrap text-[10px] text-muted">
      <span className="flex items-center gap-1.5"><i className="size-1.5 rounded-full bg-coral"/>Raises model score</span>
      <span className="flex items-center gap-1.5"><i className="size-1.5 rounded-full bg-lime"/>Lowers model score</span>
    </div>
  </div>;
}

export default function AnalysisView({ analysis, cases }: { analysis: Analysis; cases: CasesResponse | null }) {
  const r = analysis.result;
  const reduce = useReducedMotion();
  const [tab, setTab] = useState("tree");
  const model = buildModel(r, analysis.title);
  const sum = summarise(model);
  const date = new Date(analysis.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  const stageLabel = analysis.stage === "stage1" ? "Level 1 · place + industry" : "Level 2 · company data";
  const researchNode = sum.up ?? [...r.tree.children].sort((a, b) => Math.abs(b.net_shap) - Math.abs(a.net_shap))[0]?.label ?? "Industry";
  const hasNotes = analysis.context && Object.values(analysis.context).some(Boolean);

  return <motion.main className="mx-auto w-full max-w-[1440px] px-4 pb-24 pt-6 md:px-8 md:pt-10 xl:px-12"
    initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: .35 }}>
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
      <Link href="/history" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-ink/10 px-4 transition-colors hover:border-coral hover:text-text focus-visible:outline-2 focus-visible:outline-coral"><span aria-hidden="true">←</span> All analyses</Link>
      <div className="flex items-center gap-2"><span className="size-1.5 rounded-full bg-lime"/><span>Saved analysis</span><span aria-hidden="true">·</span><time dateTime={analysis.created_at}>{date}</time></div>
    </div>

    <section className="relative isolate overflow-hidden rounded-[28px] border border-ink/10 bg-dark-surface p-6 surface-lift md:p-10 xl:p-12" aria-label="Analysis overview">
      <div aria-hidden="true" className="pointer-events-none absolute -right-24 -top-40 -z-10 size-[420px] rounded-full bg-coral/10 blur-[90px]"/>
      <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(250px,340px)] lg:gap-12">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="eyebrow rounded-full bg-coral-soft px-3 py-1.5 text-coral">Startup intelligence / {stageLabel}</span>
            <span className="rounded-full border border-ink/10 px-3 py-1.5 text-xs text-muted">Historical model output</span>
          </div>
          <p className="mt-7 text-sm font-medium text-muted">A closer look at</p>
          <h1 className="editorial-title mt-2 max-w-4xl break-words font-display">{analysis.title}<span className="text-coral">.</span></h1>
          <div className="mt-7 flex flex-wrap items-center gap-3">
            <a href="#model-trace" onClick={() => setTab("tree")} className="inline-flex min-h-12 items-center gap-2 rounded-full bg-sage px-6 text-sm font-semibold text-[var(--sage-ink)] transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral">Explore the model trace <span aria-hidden="true">↘</span></a>
            <button type="button" onClick={() => { setTab("cases"); document.getElementById("analysis-sections")?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }); }} className="inline-flex min-h-12 items-center gap-2 rounded-full border border-ink/20 px-6 text-sm font-semibold transition-colors hover:border-coral focus-visible:outline-2 focus-visible:outline-coral">How similar startups failed <span aria-hidden="true">↗</span></button>
          </div>
          <p className="mt-6 max-w-xl text-xs leading-relaxed text-muted">Fragilee shows what this historical model used and links to separate research and company cases. Its available data do not support a validated forecast for this individual startup.</p>
        </div>
        <div className="analysis-grid-bg relative rounded-[24px] border border-ink/10 bg-dark-bg/40 px-3 py-4 md:px-6">
          <SignalArt branches={r.tree.children}/>
        </div>
      </div>
      <div className="mt-9 grid gap-3 border-t border-ink/10 pt-5 sm:grid-cols-2">
        <div className="rounded-2xl bg-brand-coral-soft p-4">
          <p className="eyebrow text-coral">Largest positive contribution</p>
          <p className="mt-2 font-display text-2xl">{sum.up ?? "No positive contribution"}</p>
          <p className="mt-1 text-xs text-muted">Historical model attribution · not a diagnosed vulnerability</p>
        </div>
        <div className="rounded-2xl bg-brand-acid-soft p-4">
          <p className="eyebrow text-lime">Largest negative contribution</p>
          <p className="mt-2 font-display text-2xl">{sum.down ?? "No negative contribution"}</p>
          <p className="mt-1 text-xs text-muted">Historical model attribution · not evidence of protection</p>
        </div>
      </div>
    </section>

    <section id="analysis-sections" className="scroll-mt-6 pt-14 md:pt-20">
      <div id="model-trace" className="mb-7 flex flex-wrap items-end justify-between gap-4 scroll-mt-6">
        <div><p className="eyebrow text-coral">Explore the signals</p><h2 className="mt-2 font-display text-3xl md:text-4xl">What moved the model?</h2><p className="mt-2 max-w-2xl text-sm text-muted">Select a node to inspect this run’s input and contribution. Research is fetched separately and does not change the score.</p></div>
        <p className="max-w-sm text-xs text-muted">The model reflects historical associations. It cannot establish why a company failed or what will happen next.</p>
      </div>
      <ResultTabs active={tab} onChange={setTab} tabs={[
        { id: "tree", label: "Model trace", panel: <PlexTree result={r} title={analysis.title} analysisId={analysis.id} context={analysis.context}/> },
        { id: "cases", label: "How similar startups failed", panel: <CasesPanel data={cases} analysisId={analysis.id} researchNode={researchNode}/> },
        ...(hasNotes ? [{ id: "notes", label: "Founder notes", panel: <Notes context={analysis.context!}/> }] : []),
      ]}/>
    </section>

    <details className="mt-12 rounded-2xl border border-ink/10 bg-dark-surface p-5 text-sm">
      <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 font-semibold"><span>Limitations and methodology</span><span className="text-coral" aria-hidden="true">＋</span></summary>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-muted">{r.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      <p className="mt-4 border-t border-ink/10 pt-4 text-muted">{r.disclaimer}</p>
    </details>
  </motion.main>;
}
