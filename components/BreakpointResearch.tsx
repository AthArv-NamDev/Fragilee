"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import type { DiagnosticFinding, EvidenceResponse } from "@/lib/types";
import EvidenceResults from "@/components/EvidenceResults";
import { researchStateLabel } from "@/lib/research-presentation.mjs";

function focusForFinding(finding: DiagnosticFinding): "Market" | "Industry" | "Funding" | "Traction" {
  if (finding.category === "market_customer_validation" || finding.category === "marketplace") return "Market";
  if (finding.category === "unit_economics" || finding.category === "funding_runway") return "Funding";
  if (finding.category === "retention_traction") return "Traction";
  return "Industry";
}

export default function BreakpointResearch({ analysisId, finding }: { analysisId: string; finding: DiagnosticFinding }) {
  const [state, setState] = useState<"idle" | "loading" | "ready" | "unavailable">("idle");
  const [research, setResearch] = useState<EvidenceResponse | null>(null);

  async function loadResearch(refresh = false) {
    setState("loading");
    try {
      const focus = focusForFinding(finding);
      const path = `/v1/analyses/${encodeURIComponent(analysisId)}/evidence${refresh ? "/refresh" : ""}?node=${encodeURIComponent(finding.diagnostic_id)}&focus=${focus}`;
      const value = await apiFetch<EvidenceResponse>(path, refresh ? { method: "POST" } : {});
      setResearch(value);
      setState("ready");
    } catch {
      setResearch(null);
      setState("unavailable");
    }
  }

  return <section className="mt-4 rounded-xl border border-ink/10 bg-dark-bg/25 p-4" aria-labelledby="breakpoint-research-title">
    <p className="text-xs font-bold uppercase tracking-wide text-muted">Evidence context</p>
    <h4 id="breakpoint-research-title" className="mt-1 font-semibold">Research for this breakpoint</h4>
    <p className="mt-2 text-xs leading-relaxed text-muted">Search source-linked research for this diagnostic mechanism. Studies can add context, but they cannot establish whether the condition is true for this startup or replace missing founder data.</p>
    {state === "idle" && <button type="button" onClick={() => loadResearch()} className="mt-3 min-h-11 rounded-full border border-ink/15 px-4 text-xs font-semibold text-text hover:border-coral focus-visible:outline-2 focus-visible:outline-coral">Find related research</button>}
    {state === "loading" && <p className="mt-3 text-sm text-muted" role="status">Loading saved research or searching the research index…</p>}
    {state === "unavailable" && <div className="mt-3 space-y-2" role="status"><p className="text-sm text-muted">Research is unavailable for this breakpoint right now. The profile assessment above is unchanged.</p><button type="button" onClick={() => loadResearch()} className="min-h-11 rounded-full border border-ink/15 px-4 text-xs font-semibold text-text hover:border-coral focus-visible:outline-2 focus-visible:outline-coral">Try again</button></div>}
    {state === "ready" && research && <div className="mt-3" aria-live="polite">
      <p className="text-xs text-muted">{researchStateLabel(research.state ?? "provider_error")} · {research.sources.length} source{research.sources.length === 1 ? "" : "s"} · {research.retrieved_at || "retrieval date unavailable"}</p>
      <p className="mt-1 text-xs text-muted">{research.snapshot_persistence_note || "Persistence status unavailable."}</p>
      {research.sources.length ? <EvidenceResults sources={research.sources} compact/> : <p className="mt-3 rounded-lg bg-ink/5 p-3 text-xs leading-relaxed text-muted">{research.note || "No sufficiently relevant abstract excerpts were found. This is not evidence that no research exists."}</p>}
      <button type="button" onClick={() => loadResearch(true)} className="mt-3 min-h-11 rounded-full border border-ink/15 px-4 text-xs font-semibold text-text hover:border-coral focus-visible:outline-2 focus-visible:outline-coral">Refresh this breakpoint’s research</button>
    </div>}
  </section>;
}
