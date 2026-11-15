"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { BAND_STYLE } from "@/lib/format";
import { DIMS, buildModel, describe, layout, short, wrap, type Mode, type Role, type Slot, type TModel, type TNode } from "@/lib/tree";
import { apiFetch } from "@/lib/api";
import type { Context, EvidenceResponse, PredictionResult } from "@/lib/types";
import EvidenceResults from "@/components/EvidenceResults";

type Cur = { x: number; y: number; r: number; op: number; role: Role };
const ease = (u: number) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const LOCKED = "#5E616D";
const colour = (n: TNode) => n.kind === "locked" ? LOCKED : n.kind === "root" && n.band ? BAND_STYLE[n.band].color : n.effect === "raises" ? "var(--color-high)" : n.effect === "lowers" ? "var(--color-low)" : "var(--color-muted)";
const glyph = (n: TNode) => (n.kind === "locked" ? "🔒" : n.kind === "root" && n.band ? BAND_STYLE[n.band].glyph : n.effect === "raises" ? "↑" : n.effect === "lowers" ? "↓" : "·");
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

export default function PlexTree({ result, title, analysisId, context }: { result: PredictionResult; title: string; analysisId: string; context?: Context | null }) {
  const reduce = useReducedMotion() ?? false;
  const M: TModel = useMemo(() => buildModel(result, title), [result, title]);
  const [active, setActive] = useState("root");
  const [selected, setSelected] = useState("root");
  const [evidence, setEvidence] = useState<EvidenceResponse | null>(null);
  const [evidenceState, setEvidenceState] = useState<"idle" | "loading" | "ready" | "unavailable">("idle");
  const [researchFocus, setResearchFocus] = useState<"Market" | "Industry">("Industry");
  const [mode, setMode] = useState<Mode>("wide");
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {        // phones get a taller, narrower tree with bigger writing
    const el = box.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([e]) => { if (e.contentRect.width > 0) setMode(e.contentRect.width < 640 ? "compact" : "wide"); });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const target = useMemo(() => layout(M, active, mode), [M, active, mode]);
  const origin = useMemo(() => ({ x: DIMS[mode].CX, y: DIMS[mode].CY }), [mode]);
  const cur = useGlide(target, origin, reduce);
  const { W, H } = DIMS[mode];
  const wide = mode === "wide";

  useEffect(() => {
    const node = M[selected];
    if (!node || node.kind === "root" || node.kind === "locked") return;
    let current = true;
    apiFetch<EvidenceResponse>(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence?node=${encodeURIComponent(short(node.label))}&focus=${researchFocus}`)
      .then((data) => { if (current) { setEvidence(data); setEvidenceState("ready"); } })
      .catch(() => { if (current) setEvidenceState("unavailable"); });
    return () => { current = false; };
  }, [analysisId, M, selected, researchFocus]);

  function select(id: string) {
    setSelected(id);
    setEvidence(null);
    setEvidenceState(M[id].kind === "root" || M[id].kind === "locked" ? "idle" : "loading");
    if (M[id].kind !== "locked") setActive(id);   // a locked branch only explains itself
  }
  function onKey(e: React.KeyboardEvent) {
    const parent = M[active].parent;
    if ((e.key === "ArrowUp" || e.key === "Backspace") && parent) { e.preventDefault(); select(parent); (box.current?.querySelector(`[data-id="${parent}"]`) as SVGElement | null)?.focus(); }
    if (e.key === "Home") { e.preventDefault(); select("root"); }
  }
  const reading = describe(M, selected);

  const outline = (id: string): React.ReactNode => {
    const n = M[id];
    return (
      <li key={id}>
        <button type="button" data-outline={id} aria-current={id === active ? "true" : undefined} aria-disabled={n.kind === "locked" || undefined} onClick={() => select(id)}
          className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs hover:bg-ink/5 aria-[current=true]:bg-coral/15 aria-disabled:text-muted">
          <i className="size-2.5 rounded-full shrink-0" style={{ background: n.kind === "locked" ? "transparent" : colour(n), border: n.kind === "locked" ? "1.5px dashed #8A8D99" : undefined }} />
          <span className="flex-1 break-words">{short(n.label)}</span>
          <em className="text-xs not-italic text-muted whitespace-nowrap">{n.kind === "locked" ? "Level 2" : n.kind === "root" ? "model trace" : n.effect === "raises" ? "↑ score" : n.effect === "lowers" ? "↓ score" : "neutral"}</em>
        </button>
        {n.children.length > 0 && <ul className="ml-3 border-l border-ink/10 pl-1.5">{n.children.map(outline)}</ul>}
      </li>
    );
  };

  const lb = wide ? { active: 30, other: 22, sub: 17, sib: 19 } : { active: 28, other: 22, sub: 17, sib: 18 };
  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(300px,.58fr)]">
      <div ref={box} onPointerMove={(event) => {
        if (reduce || event.pointerType !== "mouse") return;
        const rect = event.currentTarget.getBoundingClientRect();
        setTilt({ x: ((event.clientY - rect.top) / rect.height - .5) * -1.6, y: ((event.clientX - rect.left) / rect.width - .5) * 1.6 });
      }} onPointerLeave={() => setTilt({ x: 0, y: 0 })}
        className="analysis-grid-bg overflow-hidden rounded-[24px] border border-ink/10 bg-dark-surface p-2 surface-lift md:p-4" style={{ perspective: "1400px" }}>
       <div style={{ transform: reduce ? undefined : `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`, transition: reduce ? undefined : "transform 280ms ease-out", transformStyle: "preserve-3d" }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="block w-full h-auto" role="group" aria-label="Historical model contribution tree. The outline on the page has the same content as a list." onKeyDown={onKey}>
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
                style={{ stroke: colour(n), strokeWidth: (n.kind === "locked" ? 2 : 1.5 + 9 * n.strength) * (wide ? 1 : 1.3), opacity: Math.min(par.op, c.op) * (n.kind === "locked" ? 0.55 : 0.55) }} strokeDasharray={n.kind === "locked" ? "6 7" : undefined} />;
            })}
          </g>
          <g>
            {[...cur].map(([id, c]) => {
              const n = M[id];
              if (!n) return null;
              const parent = c.role === "parent", isActive = c.role === "active";
              const lines = parent ? [short(n.label)] : wrap(short(n.label), isActive ? (wide ? 24 : 20) : c.role === "child" ? (wide ? 16 : 13) : 12, 2);
              const size = isActive ? lb.active : c.role === "sib" ? lb.sib : lb.other, lh = size * 1.15;
              const sub = parent ? "" : n.kind === "root" ? "historical model trace · not a forecast" : n.kind === "locked" ? "unlocks at Level 2" : n.kind === "branch" ? (n.effect === "raises" ? "↑ raises model score" : n.effect === "lowers" ? "↓ lowers model score" : "· no change") : `${n.effect === "raises" ? "↑ raises model score" : "↓ lowers model score"}${n.value !== undefined ? ` · ${n.value}` : ""}`;
              const labelY = c.r + size + 6;
              return (
                <g key={id} data-id={id} data-role={c.role} transform={`translate(${c.x.toFixed(1)} ${c.y.toFixed(1)})`} style={{ opacity: c.op, cursor: "pointer", outline: "none" }}
                  tabIndex={0} role="button" aria-current={isActive ? "true" : undefined} aria-label={`${short(n.label)}${n.band ? ", " + n.band : ""}. ${n.kind === "locked" ? "Locked until Level 2." : isActive ? "Selected." : "Press Enter to move here."}`}
                  onClick={() => select(id)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(id); } }}>
                  <title>{n.label}</title>
                  <circle r={Math.max(c.r, 0)} style={{ fill: n.kind === "locked" ? "none" : isActive ? "url(#selectedSphere)" : "url(#factorSphere)", fillOpacity: isActive ? 1 : 0.96, stroke: colour(n), strokeWidth: isActive ? 4 : 2 }} strokeDasharray={n.kind === "locked" ? "5 6" : undefined} filter={isActive ? "url(#nodeDepth)" : undefined} />
                  <text textAnchor="middle" y={c.r * 0.26} fontSize={c.r * 0.72} fontWeight={700} fill={n.kind === "locked" ? "var(--text)" : "var(--node-ink)"} pointerEvents="none">{glyph(n)}</text>
                  <text x={parent ? c.r + 12 : 0} y={parent ? 6 : labelY} textAnchor={parent ? "start" : "middle"} fontSize={size} fontWeight={800} fill={parent ? "var(--color-muted)" : "var(--color-ink)"} stroke="var(--color-dark-surface)" strokeWidth={6} strokeLinejoin="round" paintOrder="stroke" style={{ fontFamily: "var(--font-hero)" }}>
                    {lines.map((t, i) => <tspan key={i} x={parent ? c.r + 12 : 0} dy={i ? lh : 0}>{t}</tspan>)}
                  </text>
                  {sub && <text textAnchor="middle" y={labelY + lh * lines.length + 2} fontSize={lb.sub} fill="var(--color-muted)" stroke="var(--color-dark-surface)" strokeWidth={5} strokeLinejoin="round" paintOrder="stroke">{sub}</text>}
                </g>
              );
            })}
          </g>
        </svg>
       </div>
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 pb-2 pt-1 text-xs text-muted"><span>Select a sphere to explore its input and contribution.</span><span>↑ parent · Home overview</span></div>
      </div>

      <aside className="sticky bottom-[calc(4.5rem+env(safe-area-inset-bottom))] z-20 max-h-[54dvh] space-y-3 overflow-y-auto overscroll-contain rounded-2xl border border-coral/20 bg-dark-surface/95 p-4 shadow-2xl backdrop-blur-md lg:static lg:max-h-none lg:overflow-visible lg:rounded-none lg:border-0 lg:bg-transparent lg:p-0 lg:shadow-none lg:backdrop-blur-none">
        <div className="rounded-2xl border border-ink/10 bg-dark-surface p-5" aria-live="polite">
          <p className="eyebrow text-coral">{reading.kicker}</p>
          <h2 className="mt-2 break-words font-display text-2xl">{reading.title}</h2>
          <div className="mt-3 space-y-2 text-sm">{reading.lines.map((l) => <p key={l}>{l}</p>)}</div>
          {M[selected].kind === "factor" && <div className="mt-4 rounded-xl border border-ink/10 bg-dark-bg/40 p-3">
            <div className="flex items-center justify-between gap-2 text-xs"><span className="text-muted">Relative contribution in this branch</span><span className="font-semibold tabular-nums">{Math.round(M[selected].strength * 100)}%</span></div>
            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ink/10"><div className="h-full rounded-full bg-coral" style={{ width: `${Math.max(4, Math.min(100, M[selected].strength * 100))}%` }}/></div>
            <p className="mt-2 text-[11px] leading-relaxed text-muted">Relative share of absolute feature impact within this displayed branch; not a probability or risk percentage.</p>
          </div>}
          {M[selected].kind === "factor" && (context?.concept || context?.customer || context?.revenue_model) && <div className="mt-3 rounded-xl bg-ink/5 p-3 text-xs leading-relaxed">
            <p className="font-semibold">Your startup context · founder-provided, unverified</p>
            {context.concept && <p className="mt-1"><span className="text-muted">Offer:</span> {context.concept}</p>}
            {context.customer && <p className="mt-1"><span className="text-muted">Target customer:</span> {context.customer}</p>}
            {context.revenue_model && <p className="mt-1"><span className="text-muted">Revenue model:</span> {context.revenue_model}</p>}
            <p className="mt-2 text-muted">These notes help frame the selected research topic; they did not change the model score and are not independently verified.</p>
          </div>}
          {M[selected].kind !== "root" && M[selected].kind !== "locked" && (
            <section className="mt-5 border-t border-ink/10 pt-4" aria-live="polite">
              <p className="eyebrow text-coral">Separate research lens</p>
              <p className="mt-1 text-xs text-muted">Research evidence · independent from the model score</p>
              <div className="mt-2 flex gap-2" role="group" aria-label="Research focus">
                {(["Market", "Industry"] as const).map((focus) => <button key={focus} type="button" aria-pressed={researchFocus === focus} onClick={() => { setResearchFocus(focus); setEvidence(null); setEvidenceState("loading"); }} className="min-h-11 rounded-full border border-ink/15 px-3 text-xs aria-pressed:bg-coral aria-pressed:text-coral-ink focus-visible:outline-2 focus-visible:outline-coral">{focus}</button>)}
              </div>
              {evidenceState === "loading" && <p className="mt-2 text-sm text-muted">Searching recent research for this field and risk…</p>}
              {evidenceState === "unavailable" && <p className="mt-2 text-sm text-muted">Research could not be reached right now. The model explanation above is still available.</p>}
              {evidenceState === "ready" && evidence && <>
                <p className="mt-2 text-sm text-muted">{evidence.note}</p>
                {evidence.sources.length > 0 && <EvidenceResults sources={evidence.sources} compact />}
              </>}
            </section>
          )}
        </div>
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
