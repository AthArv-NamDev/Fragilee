"use client";

import { useState } from "react";
import type { DiagnosticFinding, DiagnosticReport, DiagnosticsState } from "@/lib/types";
import { diagnosticEvidenceLabels, formatDiagnosticCalculatedValue, formatDiagnosticInput, resolveDiagnosticViewState } from "@/lib/diagnostics-presentation.mjs";
import { breakpointStatusLabel, groupBreakpoints, initialBreakpointId } from "@/lib/breakpoint-explorer.mjs";

function statusTone(status: DiagnosticFinding["status"]) {
  if (status === "CONFIRMED" || status === "INDICATED") return "border-coral/40 bg-coral/10";
  if (status === "CONFLICTED") return "border-violet/40 bg-violet/10";
  if (status === "HYPOTHESIS") return "border-ink/20 bg-ink/5";
  return "border-ink/10 bg-dark-surface";
}

export function BreakpointDetail({ finding }: { finding: DiagnosticFinding }) {
  const labels = diagnosticEvidenceLabels(finding);
  const inputs = finding.supporting_inputs.map(formatDiagnosticInput);
  const calculations = Object.entries(finding.calculated_values);

  return <article className="min-w-0 rounded-2xl border border-coral/20 bg-dark-surface p-5 md:p-6" aria-live="polite" aria-labelledby="selected-breakpoint-title">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <p className="eyebrow text-coral">Selected breakpoint</p>
        <h3 id="selected-breakpoint-title" className="mt-2 break-words font-display text-2xl">{finding.title}</h3>
      </div>
      <span className={`inline-flex min-h-9 items-center rounded-full border px-3 text-xs font-semibold ${statusTone(finding.status)}`} aria-label={`Finding state: ${breakpointStatusLabel(finding.status)}`}>
        {breakpointStatusLabel(finding.status)}
      </span>
    </div>

    <div className="mt-5 rounded-xl border border-ink/10 p-4">
      <h4 className="text-xs font-bold uppercase tracking-wide text-muted">Assessment from submitted profile</h4>
      <p className="mt-2 text-sm leading-relaxed">{finding.explanation}</p>
      {inputs.length > 0 && <ul className="mt-3 space-y-2 text-sm">
        {inputs.map((input, index) => <li key={`${input.label}-${index}`} className="break-words">
          <span className="font-semibold">{input.label}: </span>{input.value}
          {input.provenance && <span className="ml-1 text-muted">({input.provenance.replaceAll("_", " ")})</span>}
        </li>)}
      </ul>}
      {inputs.length === 0 && <p className="mt-2 text-sm text-muted">No founder-provided input supports a positive claim for this check.</p>}
    </div>

    <div className="mt-3 rounded-xl border border-ink/10 p-4">
      <h4 className="text-xs font-bold uppercase tracking-wide text-muted">How this could break in practice</h4>
      <p className="mt-2 text-sm leading-relaxed">{finding.mechanism}</p>
      <p className="mt-2 text-xs leading-relaxed text-muted">This is a possible business mechanism, not a claim that it is happening. The finding state above shows what the submitted inputs do and do not establish.</p>
    </div>

    {finding.missing_inputs.length > 0 && <div className="mt-3 rounded-xl border border-ink/10 p-4">
      <h4 className="text-xs font-bold uppercase tracking-wide text-muted">Information still needed</h4>
      <p className="mt-1 text-xs text-muted">A gap is not evidence of risk.</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{finding.missing_inputs.map((item) => <li key={item} className="break-words">{item}</li>)}</ul>
    </div>}

    {(finding.suggested_validation || finding.suggested_next_actions.length > 0) && <div className="mt-3 rounded-xl border border-lime/25 bg-lime/5 p-4">
      <h4 className="text-xs font-bold uppercase tracking-wide text-muted">What to validate next</h4>
      {finding.suggested_validation && <p className="mt-2 text-sm leading-relaxed">{finding.suggested_validation}</p>}
      {finding.suggested_next_actions.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{finding.suggested_next_actions.map((action) => <li key={action}>{action}</li>)}</ul>}
    </div>}

    <dl className="mt-4 grid gap-3 border-t border-ink/10 pt-4 text-sm sm:grid-cols-2">
      <div><dt className="text-xs text-muted">Evidence strength</dt><dd className="mt-1 font-medium">{labels.evidenceStrength}</dd></div>
      <div><dt className="text-xs text-muted">Severity if true</dt><dd className="mt-1 font-medium">{labels.severity}</dd></div>
    </dl>

    <details className="mt-4 border-t border-ink/10 pt-3 text-sm">
      <summary className="flex min-h-11 cursor-pointer items-center font-semibold focus-visible:outline-2 focus-visible:outline-coral">Rule, calculations and limits</summary>
      <div className="mt-3 space-y-3 text-muted">
        <p>{finding.formula_or_rule}</p>
        {calculations.length > 0 && <dl className="grid gap-3 sm:grid-cols-2">{calculations.map(([key, value]) => <div key={key}><dt className="text-xs">{key.replaceAll("_", " ")}</dt><dd className="mt-1 break-words font-medium text-text">{formatDiagnosticCalculatedValue(key, value, finding.calculated_values)}</dd></div>)}</dl>}
        {finding.assumptions.length > 0 && <div><h5 className="font-semibold text-text">Assumptions</h5><ul className="mt-1 list-disc space-y-1 pl-5">{finding.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        {finding.limitations.length > 0 && <div><h5 className="font-semibold text-text">Limitations</h5><ul className="mt-1 list-disc space-y-1 pl-5">{finding.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        <p className="text-xs">Rule version {finding.diagnostic_version}. Research sources and historical company cases are separate context and are not used to verify this profile finding.</p>
      </div>
    </details>
  </article>;
}

export default function BreakpointTree({ diagnostics, state, startupName }: {
  diagnostics?: DiagnosticReport | null;
  state?: DiagnosticsState | null;
  startupName: string;
}) {
  const viewState = resolveDiagnosticViewState(state, diagnostics);
  const findings = diagnostics?.findings ?? [];
  const sections = [
    {
      id: "signals",
      label: "Supplied signals, assumptions and conflicts",
      groups: groupBreakpoints(findings.filter((finding) => ["CONFIRMED", "INDICATED", "HYPOTHESIS", "CONFLICTED"].includes(finding.status))),
    },
    {
      id: "gaps",
      label: "Information needed · not a risk finding",
      groups: groupBreakpoints(findings.filter((finding) => finding.status === "INSUFFICIENT_INFORMATION")),
    },
    {
      id: "other",
      label: "Checks not triggered or not applicable",
      groups: groupBreakpoints(findings.filter((finding) => ["NOT_TRIGGERED", "NOT_APPLICABLE"].includes(finding.status))),
    },
  ].filter((section) => section.groups.length > 0);
  const [selectedId, setSelectedId] = useState<string | null>(() => initialBreakpointId(findings));
  const selected = findings.find((finding) => finding.finding_id === selectedId) ?? findings[0];

  if (viewState === "unavailable" || viewState === "no_profile") return <section className="rounded-[24px] border border-ink/10 bg-dark-surface p-5 md:p-7" aria-labelledby="breakpoint-tree-title">
    <p className="eyebrow text-coral">Founder-facing assessment</p>
    <h2 id="breakpoint-tree-title" className="mt-2 font-display text-2xl">Breakpoints to investigate</h2>
    <p className="mt-3 max-w-3xl text-sm leading-relaxed text-muted">Startup-specific breakpoints are built from the structured profile. Historical model attribution, research and company examples do not fill in missing founder facts.</p>
    <p className="mt-5 rounded-xl border border-ink/10 p-4 text-sm" role="status">{viewState === "no_profile" ? "This saved analysis has no structured profile, so the application cannot produce startup-specific breakpoints. Missing information is not a risk finding." : "Diagnostics are unavailable for this analysis. No business conclusion has been inferred; the rest of the report remains available."}</p>
  </section>;

  if (!diagnostics?.profile_available) return <section className="rounded-[24px] border border-ink/10 bg-dark-surface p-5 md:p-7" aria-labelledby="breakpoint-tree-title">
    <h2 id="breakpoint-tree-title" className="font-display text-2xl">Breakpoints to investigate</h2>
    <p className="mt-3 text-sm text-muted" role="status">No structured profile findings are available for this analysis.</p>
  </section>;

  const actionableCount = findings.filter((finding) => !["NOT_TRIGGERED", "NOT_APPLICABLE"].includes(finding.status)).length;
  return <section className="rounded-[24px] border border-ink/10 bg-dark-surface p-5 md:p-7" aria-labelledby="breakpoint-tree-title">
    <div className="max-w-4xl">
      <p className="eyebrow text-coral">Structured profile assessment · {actionableCount} findings and gaps</p>
      <h2 id="breakpoint-tree-title" className="mt-2 font-display text-3xl">Startup breakpoints to inspect</h2>
      <p className="mt-3 text-sm leading-relaxed text-muted">Select a node to see what {startupName}&apos;s submitted profile says, the practical mechanism to consider, and what to validate next. Information gaps appear in their own branch and are not risk findings. This map is not an overall risk score or failure prediction.</p>
    </div>

    {findings.length === 0 ? <p className="mt-5 rounded-xl border border-ink/10 p-4 text-sm" role="status">No checks were returned for this profile. That is not evidence that the business is safe.</p> : <>
      <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(260px,.8fr)_minmax(0,1.2fr)]">
        <div className="min-w-0">
          <div className="mx-auto mb-4 w-fit max-w-full rounded-2xl border border-coral/30 bg-coral/10 px-5 py-3 text-center">
            <span className="block text-[10px] font-bold uppercase tracking-[.16em] text-coral">Startup</span>
            <span className="mt-1 block max-w-[240px] truncate font-semibold" title={startupName}>{startupName}</span>
          </div>
          <div className="mx-auto mb-1 h-4 w-px bg-ink/20" aria-hidden="true"/>
          <ul className="space-y-4" aria-label="Startup breakpoint tree">
            {sections.map((section) => <li key={section.id} className="relative border-l border-coral/25 pl-4">
              <div className="absolute -left-px top-5 h-px w-3 bg-coral/30" aria-hidden="true"/>
              <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-text">{section.label}</h3>
              <ul className="space-y-3">
                {section.groups.map((group) => <li key={group.id} className="relative border-l border-ink/15 pl-3">
                  <div className="absolute -left-px top-4 h-px w-2 bg-ink/20" aria-hidden="true"/>
                  <h4 className="mb-2 text-[11px] font-bold uppercase tracking-wide text-muted">{group.label}</h4>
                  <ul className="space-y-2">
                    {group.findings.map((finding) => <li key={finding.finding_id} className="relative border-l border-ink/10 pl-3 last:border-transparent">
                      <div className="absolute -left-px top-5 h-px w-2 bg-ink/15" aria-hidden="true"/>
                      <button type="button" aria-pressed={finding.finding_id === selected?.finding_id} onClick={() => setSelectedId(finding.finding_id)} className={`flex min-h-11 w-full items-start gap-2 rounded-xl border px-3 py-2 text-left transition-colors hover:border-coral/40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral aria-pressed:border-coral aria-pressed:bg-coral/10 ${statusTone(finding.status)}`}>
                        <span aria-hidden="true" className={`mt-1.5 size-2 shrink-0 rounded-full ${finding.status === "INSUFFICIENT_INFORMATION" ? "border border-muted" : finding.status === "CONFLICTED" ? "bg-violet" : finding.status === "NOT_TRIGGERED" || finding.status === "NOT_APPLICABLE" ? "bg-ink/30" : "bg-coral"}`}/>
                        <span className="min-w-0 flex-1"><span className="block break-words text-sm font-medium">{finding.title}</span><span className="mt-0.5 block text-[11px] leading-snug text-muted">{breakpointStatusLabel(finding.status)}</span></span>
                      </button>
                    </li>)}
                  </ul>
                </li>)}
              </ul>
            </li>)}
          </ul>
          <p className="mt-4 text-xs leading-relaxed text-muted">Nodes follow diagnostic engine order. Their position is not a ranking of likelihood, urgency, or severity.</p>
        </div>
        {selected ? <BreakpointDetail finding={selected}/> : <p className="rounded-xl border border-ink/10 p-4 text-sm text-muted">Select a breakpoint to inspect its reasoning.</p>}
      </div>
      <p className="mt-5 border-t border-ink/10 pt-4 text-xs leading-relaxed text-muted">Engine {diagnostics.engine_version}. Missing inputs remain unknown; assumed inputs remain hypotheses. Historical model output, external research, and company examples are separate evidence streams.</p>
    </>}
  </section>;
}
