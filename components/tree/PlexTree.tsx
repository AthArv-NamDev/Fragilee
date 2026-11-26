"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { DIMS, buildModel, describe, layout, short, wrap, type Mode, type Role, type Slot, type TModel, type TNode } from "@/lib/tree";
import type { DiagnosticReport, PredictionResult } from "@/lib/types";
import { BreakpointDetail } from "@/components/BreakpointTree";
import BreakpointResearch from "@/components/BreakpointResearch";
import { breakpointVisualSeverity, breakpointVisualState, initialBreakpointId } from "@/lib/breakpoint-explorer.mjs";

type Cur = { x: number; y: number; r: number; op: number; role: Role };
const ease = (u: number) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const LOCKED = "#5E616D";
const SEVERITY_COLOURS = { Critical: "var(--critical)", Major: "var(--high)", Moderate: "var(--medium)", Minor: "var(--low)", unrated: "var(--muted)" } as const;
const EVIDENCE_COLOURS = { measured: "var(--color-coral)", estimated: "var(--color-amber)", hypothesis: "var(--hypothesis)", conflicted: "var(--critical)", information: "var(--color-info)", neutral: "var(--muted)" } as const;
const EVIDENCE_LABELS = { measured: "Measured", estimated: "Estimated", hypothesis: "Assumption", conflicted: "Conflict", information: "Information needed", neutral: "Not triggered / N/A" } as const;
const colour = (n: TNode) => {
  if (n.kind === "locked") return LOCKED;
  if (n.kind === "diagnostic") {
    const severity = breakpointVisualSeverity(n.finding);
    if (severity !== "unrated") return SEVERITY_COLOURS[severity];
    const state = breakpointVisualState(n.finding);
    return EVIDENCE_COLOURS[state === "severity" ? "neutral" : state];
  }
  return n.kind === "diagnostic-group" ? "var(--tree-group)" : n.id === "model-trace" ? "var(--muted)" : n.kind === "factor" ? "var(--color-violet)" : "var(--color-coral)";
};
const branchWidth = (n: TNode, wide: boolean) => {
  const severity = n.kind === "diagnostic" ? breakpointVisualSeverity(n.finding) : "unrated";
  const weight = severity === "Critical" ? 5 : severity === "Major" ? 4 : severity === "Moderate" ? 3.2 : severity === "Minor" ? 2.6 : 2;
  return weight * (wide ? 1 : 1.35);
};
const glyph = (n: TNode) => n.kind === "locked" ? "🔒" : n.kind === "root" ? "◎" : n.kind === "stream" ? (n.id === "breakpoints" ? "⌁" : "◉") : n.kind === "diagnostic-group" ? "+" : n.kind === "diagnostic" ? (n.finding?.status === "INSUFFICIENT_INFORMATION" ? "?" : n.finding?.status === "CONFLICTED" ? "↔" : n.finding?.status === "NOT_TRIGGERED" || n.finding?.status === "NOT_APPLICABLE" ? "·" : "!") : n.effect === "raises" ? "↑" : n.effect === "lowers" ? "↓" : "·";
const initial = (t: Map<string, Slot>) => new Map([...t].map(([id, s]) => [id, { ...s, op: 1 }]));

/** Glides every node from where it is to where it should be. With reduced motion the tree simply jumps. */
function useGlide(target: Map<string, Slot>, origin: { x: number; y: number }, reduce: boolean) {
  const [cur, setCur] = useState<Map<string, Cur>>(() => initial(target));
  const latest = useRef(cur);
  useEffect(() => {
    const from = new Map([...latest.current].map(([k, v]) => [k, { ...v }]));
    for (const [id, s] of target) if (!from.has(id)) from.set(id, { x: origin.x, y: origin.y, r: 4, op: 0, role: s.role });
    const leaving = [...from.keys()].filter((k) => !target.has(k));
    const t0 = performance.now(), dur = reduce ? 0 : 650;
    let raf = 0;
    const step = (now: number) => {
      const u = dur ? Math.min(1, (now - t0) / dur) : 1, e = ease(u);
      const next = new Map<string, Cur>();
      for (const [id, t] of target) { const f = from.get(id)!; next.set(id, { x: f.x + (t.x - f.x) * e, y: f.y + (t.y - f.y) * e, r: f.r + (t.r - f.r) * e, op: f.op + (1 - f.op) * e, role: t.role }); }
      if (u < 1) for (const id of leaving) { const f = from.get(id)!; next.set(id, { x: f.x + (origin.x - f.x) * e, y: f.y + (origin.y - f.y) * e, r: f.r * (1 - 0.7 * e), op: f.op * (1 - e), role: f.role }); }
      latest.current = next;
      setCur(next);
      if (u < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, origin, reduce]);
  return cur;
}

export default function PlexTree({ result, title, diagnostics, analysisId }: { result: PredictionResult; title: string; diagnostics?: DiagnosticReport | null; analysisId: string }) {
  const reduce = useReducedMotion() ?? false;
  const M: TModel = useMemo(() => buildModel(result, title, diagnostics), [result, title, diagnostics]);
  const firstFindingId = initialBreakpointId(diagnostics?.findings ?? []);
  const initialNode = firstFindingId ? `diagnostic:${firstFindingId}` : "breakpoints";
  const [active, setActive] = useState(initialNode);
  const [selected, setSelected] = useState(initialNode);
  const activeId = M[active] ? active : initialNode;
  const selectedId = M[selected] ? selected : initialNode;
  const [mode, setMode] = useState<Mode>("wide");
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {        // phones get a taller, narrower tree with bigger writing
    const el = box.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    // The tree shares a desktop column with its detail panel, so it needs the
    // compact layout before reaching phone width to keep node labels readable.
    const ro = new ResizeObserver(([e]) => { if (e.contentRect.width > 0) setMode(e.contentRect.width < 1000 ? "compact" : "wide"); });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const target = useMemo(() => layout(M, activeId, mode), [M, activeId, mode]);
  const origin = useMemo(() => ({ x: DIMS[mode].CX, y: DIMS[mode].CY }), [mode]);
  const cur = useGlide(target, origin, reduce);
  const { W } = DIMS[mode];
  const H = Math.max(mode === "wide" ? 640 : 560, ...[...target.values()].map((slot) => slot.y + slot.r + 110));
  const wide = mode === "wide";

  function select(id: string) {
    setSelected(id);
    if (M[id].kind !== "locked") setActive(id);   // a locked branch only explains itself
  }
  function onKey(e: React.KeyboardEvent) {
    const parent = M[activeId].parent;
    if ((e.key === "ArrowUp" || e.key === "Backspace") && parent) { e.preventDefault(); select(parent); (box.current?.querySelector(`[data-id="${parent}"]`) as SVGElement | null)?.focus(); }
    if (e.key === "Home") { e.preventDefault(); select("root"); }
  }
  const reading = describe(M, selectedId);
  const selectedFinding = M[selectedId]?.finding;

  const outline = (id: string): React.ReactNode => {
    const n = M[id];
    return (
      <li key={id}>
        <button type="button" data-outline={id} aria-current={id === activeId ? "true" : undefined} aria-disabled={n.kind === "locked" || undefined} onClick={() => select(id)}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs hover:bg-ink/5 aria-[current=true]:bg-coral/15 aria-disabled:text-muted">
          <i className="size-2.5 rounded-full shrink-0" style={{ background: n.kind === "locked" ? "transparent" : colour(n), border: n.kind === "locked" ? "1.5px dashed #8A8D99" : undefined }} />
          <span className="flex-1 break-words">{short(n.label)}</span>
          <em className="text-xs not-italic text-muted whitespace-nowrap">{n.kind === "locked" ? "Level 2" : n.kind === "root" ? "two evidence streams" : n.kind === "stream" ? (n.id === "breakpoints" ? "profile checks" : "historical model") : n.kind === "diagnostic" ? n.finding?.status?.replaceAll("_", " ") : n.kind === "diagnostic-group" ? "breakpoint group" : n.effect === "raises" ? "↑ model output" : n.effect === "lowers" ? "↓ model output" : "model context"}</em>
        </button>
        {n.children.length > 0 && <ul className="ml-3 border-l border-ink/10 pl-1.5">{n.children.map(outline)}</ul>}
      </li>
    );
  };

  const lb = wide ? { active: 30, other: 22, sub: 17, sib: 19 } : { active: 28, other: 22, sub: 17, sib: 18 };
  return (
    <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1.08fr)_minmax(360px,.92fr)]">
      <div ref={box} onPointerMove={(event) => {
        if (reduce || event.pointerType !== "mouse") return;
        const rect = event.currentTarget.getBoundingClientRect();
        setTilt({ x: ((event.clientY - rect.top) / rect.height - .5) * -1.6, y: ((event.clientX - rect.left) / rect.width - .5) * 1.6 });
      }} onPointerLeave={() => setTilt({ x: 0, y: 0 })}
        className="analysis-grid-bg max-h-[min(72dvh,720px)] overflow-auto rounded-[28px] border border-ink/10 bg-dark-surface p-4 surface-lift focus-visible:outline-2 focus-visible:outline-coral md:p-6" style={{ perspective: "1400px" }} tabIndex={0} aria-label="Scrollable interactive startup breakpoint tree">
       <div style={{ transform: reduce ? undefined : `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`, transition: reduce ? undefined : "transform 280ms ease-out", transformStyle: "preserve-3d" }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="block w-full h-auto" role="group" aria-label="Interactive startup breakpoints and historical model attribution tree. The outline on the page has the same content as a list." onKeyDown={onKey}>
          <defs>
            <radialGradient id="factorSphere" cx="32%" cy="25%" r="78%"><stop offset="0%" stopColor="var(--cream)" stopOpacity=".86"/><stop offset="30%" stopColor="var(--violet)" stopOpacity=".9"/><stop offset="100%" stopColor="var(--surface-2)" stopOpacity=".96"/></radialGradient>
            <radialGradient id="selectedSphere" cx="28%" cy="22%" r="82%"><stop offset="0%" stopColor="var(--cream)" stopOpacity=".96"/><stop offset="28%" stopColor="var(--coral)" stopOpacity=".96"/><stop offset="100%" stopColor="var(--surface-2)" stopOpacity="1"/></radialGradient>
            <filter id="nodeDepth" x="-80%" y="-80%" width="260%" height="260%"><feDropShadow dx="0" dy="8" stdDeviation="7" floodColor="var(--coral)" floodOpacity=".24"/></filter>
          </defs>
          <g>
            {[...cur].map(([id, c]) => {
              const n = M[id], par = n?.parent ? cur.get(n.parent) : undefined;
              if (!n || !par) return null;
              const my = (par.y + c.y) / 2;
              return <path key={id} d={`M${par.x} ${par.y} C${par.x} ${my} ${c.x} ${my} ${c.x} ${c.y}`} fill="none" strokeLinecap="round"
                style={{ stroke: colour(n), strokeWidth: branchWidth(n, wide), opacity: Math.min(par.op, c.op) * (n.kind === "locked" ? 0.5 : 0.76) }} strokeDasharray={n.kind === "locked" ? "6 7" : undefined} />;
            })}
          </g>
          <g>
            {[...cur].map(([id, c]) => {
              const n = M[id];
              if (!n) return null;
              const parent = c.role === "parent", isActive = c.role === "active";
              const treeLabel = n.kind === "diagnostic-group" ? ({ "Customer and market": "Market customers", "Retention and traction": "Retention traction", "Cash and runway": "Cash runway", "Marketplace liquidity": "Marketplace", "Production readiness": "Production" }[n.label] ?? n.label) : short(n.label);
              const lines = parent ? wrap(treeLabel, wide ? 18 : 14, 2) : wrap(treeLabel, n.kind === "diagnostic-group" ? 10 : isActive ? (wide ? 24 : 20) : c.role === "child" ? (wide ? 18 : 13) : 12, n.kind === "diagnostic-group" ? 2 : c.role === "child" && n.kind === "diagnostic" ? 3 : 2);
              const size = n.kind === "diagnostic-group" ? (isActive ? wide ? 20 : 18 : wide ? 16 : 14) : isActive ? lb.active : c.role === "sib" ? lb.sib : lb.other, lh = size * 1.15;
              const sub = parent ? "" : n.kind === "root" ? "profile breakpoints + historical model · separate" : n.kind === "stream" ? (n.id === "breakpoints" ? "profile-specific checks · not a forecast" : "TreeSHAP context · not a diagnosis") : n.kind === "diagnostic-group" ? `${n.children.length} profile ${n.children.length === 1 ? "check" : "checks"}` : n.kind === "diagnostic" ? (n.finding?.status ?? "profile check").replaceAll("_", " ").toLowerCase() : n.kind === "locked" ? "unlocks at Level 2" : n.kind === "branch" ? (n.effect === "raises" ? "↑ model output" : n.effect === "lowers" ? "↓ model output" : "· no change") : `${n.effect === "raises" ? "↑ model output" : "↓ model output"}${n.value !== undefined ? ` · ${n.value}` : ""}`;
              const labelY = c.r + size + 6;
              const labelX = parent ? -c.r - 12 : 0;
              return (
                <g key={id} data-id={id} data-role={c.role} transform={`translate(${c.x.toFixed(1)} ${c.y.toFixed(1)})`} style={{ opacity: c.op, cursor: "pointer", outline: "none" }}
                  tabIndex={0} role="button" aria-current={isActive ? "true" : undefined} aria-label={`${short(n.label)}.${n.kind === "diagnostic" ? ` Finding state ${n.finding?.status?.replaceAll("_", " ") ?? "unavailable"}. ${n.finding?.severity_if_true ? `Potential severity if true: ${n.finding.severity_if_true}.` : "No severity assigned."}` : ""} ${n.kind === "locked" ? "Locked until Level 2." : isActive ? "Selected." : "Press Enter to move here."}`}
                  onClick={() => select(id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(id); } }}>
                  <title>{n.label}</title>
                  <circle r={Math.max(c.r, 0)} style={{ fill: n.kind === "locked" ? "none" : n.kind === "diagnostic" || n.kind === "diagnostic-group" ? `color-mix(in srgb, ${colour(n)} ${isActive ? 40 : 24}%, var(--surface-2))` : isActive ? "url(#selectedSphere)" : "url(#factorSphere)", fillOpacity: isActive ? 1 : 0.96, stroke: colour(n), strokeWidth: isActive ? Math.max(4, branchWidth(n, wide)) : branchWidth(n, wide) }} strokeDasharray={n.kind === "locked" ? "5 6" : undefined} filter={isActive ? "url(#nodeDepth)" : undefined} />
                  <text textAnchor="middle" y={c.r * 0.26} fontSize={c.r * 0.72} fontWeight={700} fill={n.kind === "locked" ? "var(--text)" : "var(--node-ink)"} pointerEvents="none">{glyph(n)}</text>
                  <text x={labelX} y={parent ? 6 : labelY} textAnchor={parent ? "end" : "middle"} fontSize={size} fontWeight={800} fill={parent ? "var(--color-muted)" : "var(--color-ink)"} stroke="var(--color-dark-surface)" strokeWidth={6} strokeLinejoin="round" paintOrder="stroke" style={{ fontFamily: "var(--font-hero)" }}>
                    {lines.map((t, i) => <tspan key={i} x={labelX} dy={i ? lh : 0}>{t}</tspan>)}
                  </text>
                  {sub && <text textAnchor="middle" y={labelY + lh * lines.length + 2} fontSize={lb.sub} fill="var(--color-muted)" stroke="var(--color-dark-surface)" strokeWidth={5} strokeLinejoin="round" paintOrder="stroke">{sub}</text>}
                </g>
              );
            })}
          </g>
        </svg>
       </div>
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 pb-2 pt-3 text-xs text-muted"><span>Select a node to inspect a startup breakpoint or historical model context.</span><span>↑ parent · Home overview</span></div>
        {diagnostics?.findings.length ? <div className="mt-4 border-t border-ink/10 px-2 pt-4" aria-label="Breakpoint color legend">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
            <span className="font-semibold text-text">Node color</span>
            <span className="inline-flex items-center gap-2"><i aria-hidden="true" className="size-2.5 rounded-full" style={{ background: "var(--tree-group)" }}/>Category</span>
            {(["measured", "estimated", "hypothesis", "conflicted", "information", "neutral"] as const).map((state) => <span key={state} className="inline-flex items-center gap-2"><i aria-hidden="true" className="size-2.5 rounded-full" style={{ background: EVIDENCE_COLOURS[state] }}/>{EVIDENCE_LABELS[state]}</span>)}
            {(["Critical", "Major", "Moderate", "Minor"] as const).map((severity) => <span key={severity} className="inline-flex items-center gap-2"><i aria-hidden="true" className="size-2.5 rounded-full" style={{ background: SEVERITY_COLOURS[severity] }}/>{severity} if true</span>)}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-muted">Evidence-state colors distinguish what the profile establishes. Severity colors appear only when a rule has an assigned potential severity; neither encodes likelihood or overall business health.</p>
        </div> : null}
      </div>

      <aside className="z-20 space-y-4">
        {selectedFinding ? <><BreakpointDetail finding={selectedFinding}/><BreakpointResearch key={selectedFinding.diagnostic_id} analysisId={analysisId} finding={selectedFinding}/></> : <div className="rounded-2xl border border-ink/10 bg-dark-surface p-5" aria-live="polite">
            <p className="eyebrow text-coral">{reading.kicker}</p>
            <h2 className="mt-2 break-words font-display text-2xl">{reading.title}</h2>
            <div className="mt-3 space-y-2 text-sm">{reading.lines.map((l) => <p key={l}>{l}</p>)}</div>
        </div>}
        {!selectedFinding && <>
          {M[selectedId].kind === "factor" && <div className="mt-4 rounded-xl border border-ink/10 bg-dark-bg/40 p-3">
            <div className="flex items-center justify-between gap-2 text-xs"><span className="text-muted">Relative contribution in this branch</span><span className="font-semibold tabular-nums">{Math.round(M[selectedId].strength * 100)}%</span></div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink/10"><div className="h-full rounded-full bg-coral" style={{ width: `${Math.max(4, Math.min(100, M[selectedId].strength * 100))}%` }}/></div>
          <p className="mt-2 text-[11px] leading-relaxed text-muted">Relative share of absolute attribution within this branch; not a probability, risk percentage, or business-health rating.</p>
          </div>}
        </>}
        <details className="rounded-2xl bg-dark-surface border border-ink/10 p-3">
          <summary className="cursor-pointer px-2 py-1 text-xs font-bold uppercase tracking-wide text-muted">Outline · {Object.keys(M).length} nodes</summary>
          <nav aria-label="Risk tree outline" className="mt-2 max-h-56 overflow-y-auto">
            <ul>{outline("root")}</ul>
          </nav>
        </details>
      </aside>
    </div>
  );
}
