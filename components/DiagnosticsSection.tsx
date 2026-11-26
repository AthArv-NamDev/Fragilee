import type { DiagnosticFinding, DiagnosticReport, DiagnosticsState } from "@/lib/types";
import { diagnosticEvidenceLabels, formatDiagnosticCalculatedValue, formatDiagnosticInput, groupDiagnosticFindings, resolveDiagnosticViewState } from "@/lib/diagnostics-presentation.mjs";

type Props = { diagnostics?: DiagnosticReport | null; state?: DiagnosticsState | null };

function FindingCard({ finding, allFindings }: { finding: DiagnosticFinding; allFindings: DiagnosticFinding[] }) {
  const related = finding.related_findings
    .map((id) => allFindings.find((item) => item.finding_id === id)?.title ?? id);
  const inputs = finding.supporting_inputs.map(formatDiagnosticInput);
  const calculations = Object.entries(finding.calculated_values);
  const evidenceLabels = diagnosticEvidenceLabels(finding);

  return <article className="rounded-2xl border border-ink/10 bg-dark-surface p-4 md:p-5">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">{finding.category.replaceAll("_", " ")}</p>
        <h4 className="mt-1 text-lg font-semibold">{finding.title}</h4>
      </div>
      <span className="inline-flex min-h-8 items-center rounded-full border border-ink/20 px-3 text-xs font-semibold text-text" aria-label={`Status ${evidenceLabels.status}`}>
        {evidenceLabels.status}
      </span>
    </div>

    <p className="mt-3 text-sm leading-relaxed text-text">{finding.explanation}</p>
    <p className="mt-2 text-sm leading-relaxed text-muted"><span className="font-semibold text-text">What it examined: </span>{finding.description}</p>

    <dl className="mt-4 grid gap-2 border-t border-ink/10 pt-3 text-sm sm:grid-cols-2">
      <div><dt className="text-xs text-muted">Evidence strength</dt><dd className="mt-0.5 font-medium">{evidenceLabels.evidenceStrength}</dd></div>
      <div><dt className="text-xs text-muted">Severity if true</dt><dd className="mt-0.5 font-medium">{evidenceLabels.severity}</dd></div>
    </dl>

    {inputs.length > 0 && <div className="mt-4">
      <h5 className="text-xs font-semibold uppercase tracking-wide text-muted">Founder-provided inputs</h5>
      <ul className="mt-2 space-y-1.5 text-sm">{inputs.map((input, index) => <li key={`${input.label}-${index}`} className="break-words">
        <span className="font-medium">{input.label}: </span>{input.value}
      </li>)}</ul>
    </div>}

    {finding.missing_inputs.length > 0 && <div className="mt-4 rounded-xl border border-ink/10 p-3">
      <h5 className="text-xs font-semibold uppercase tracking-wide text-muted">Information not available</h5>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{finding.missing_inputs.map((item) => <li key={item} className="break-words">{item}</li>)}</ul>
    </div>}

    {finding.suggested_validation && <p className="mt-4 text-sm leading-relaxed"><span className="font-semibold">Next validation: </span>{finding.suggested_validation}</p>}
    {finding.suggested_next_actions.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">{finding.suggested_next_actions.map((action) => <li key={action}>{action}</li>)}</ul>}

    <details className="mt-4 border-t border-ink/10 pt-3 text-sm">
      <summary className="flex min-h-11 cursor-pointer items-center font-semibold focus-visible:outline-2 focus-visible:outline-coral">Rule details, calculations and limitations</summary>
      <div className="mt-3 space-y-3 text-muted">
        <p><span className="font-semibold text-text">Mechanism: </span>{finding.mechanism}</p>
        <p><span className="font-semibold text-text">Rule: </span>{finding.formula_or_rule}</p>
        {calculations.length > 0 && <dl className="grid gap-x-4 gap-y-2 sm:grid-cols-2">{calculations.map(([key, value]) => <div key={key} className="min-w-0">
          <dt className="break-words text-xs">{key.replaceAll("_", " ")}</dt>
          <dd className="break-words font-medium text-text">{formatDiagnosticCalculatedValue(key, value, finding.calculated_values)}</dd>
        </div>)}</dl>}
        {finding.assumptions.length > 0 && <div><h5 className="font-semibold text-text">Assumptions</h5><ul className="mt-1 list-disc space-y-1 pl-5">{finding.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        {finding.limitations.length > 0 && <div><h5 className="font-semibold text-text">Limitations</h5><ul className="mt-1 list-disc space-y-1 pl-5">{finding.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}
        {finding.evidence_references.length > 0 && <div><h5 className="font-semibold text-text">Evidence references</h5><ul className="mt-1 list-disc space-y-1 pl-5">{finding.evidence_references.map((item) => <li key={item} className="break-all">{item}</li>)}</ul></div>}
        {related.length > 0 && <p><span className="font-semibold text-text">Related checks ({finding.relationship_type.toLowerCase()}): </span>{related.join("; ")}. Related checks are not added together or treated as separate scores.</p>}
        <p className="text-xs">Rule version {finding.diagnostic_version}</p>
      </div>
    </details>
  </article>;
}

function FindingGroup({ title, items, allFindings, description, collapsed = false }: {
  title: string; items: DiagnosticFinding[]; allFindings: DiagnosticFinding[]; description: string; collapsed?: boolean;
}) {
  if (!items.length) return null;
  const cards = <div className="mt-3 grid gap-3">{items.map((item) => <FindingCard key={item.finding_id} finding={item} allFindings={allFindings}/>)}</div>;
  if (collapsed) return <details className="mt-4 rounded-2xl border border-ink/10 p-4">
    <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 font-semibold focus-visible:outline-2 focus-visible:outline-coral"><span>{title} ({items.length})</span><span aria-hidden="true" className="text-coral">＋</span></summary>
    <p className="mt-2 text-sm text-muted">{description}</p>{cards}
  </details>;
  return <div className="mt-6">
    <h3 className="font-display text-xl">{title}</h3>
    <p className="mt-1 text-sm text-muted">{description}</p>
    {cards}
  </div>;
}

export default function DiagnosticsSection({ diagnostics, state }: Props) {
  const viewState = resolveDiagnosticViewState(state, diagnostics);
  return <section id="startup-diagnostics" className="mt-8 scroll-mt-24 rounded-[24px] border border-ink/10 bg-dark-surface p-5 md:p-7" aria-labelledby="startup-diagnostics-title">
    <p className="eyebrow text-coral">Structured profile assessment</p>
    <h2 id="startup-diagnostics-title" className="mt-2 font-display text-3xl">Startup diagnostics</h2>
    <p className="mt-3 max-w-4xl text-sm leading-relaxed text-muted">These diagnostics apply deterministic checks to the information you supplied. They are not a prediction of startup success or failure. Findings depend on the completeness and quality of your inputs.</p>

    {viewState === "unavailable" && <p className="mt-5 rounded-xl border border-ink/10 p-4 text-sm" role="status">Diagnostics are unavailable for this analysis right now. Your saved model explanation, founder information, research and historical examples remain available below.</p>}
    {viewState === "no_profile" && <p className="mt-5 rounded-xl border border-ink/10 p-4 text-sm" role="status">This saved analysis has no structured profile to assess. Founder notes and the rest of the report remain available. Missing profile information is not a negative finding.</p>}
    {viewState === "available" && diagnostics && diagnostics.profile_available && (() => {
      const groups = groupDiagnosticFindings(diagnostics.findings);
      const actionable = groups.supported.length + groups.hypotheses.length + groups.conflicts.length + groups.informationGaps.length;
      return <>
        {actionable === 0 && <p className="mt-5 rounded-xl border border-ink/10 p-4 text-sm" role="status">No applicable findings were triggered by the supplied profile. This is not proof that the business is safe or that no further validation is needed.</p>}
        <FindingGroup title="Supported by supplied information" items={groups.supported} allFindings={diagnostics.findings} description="These findings describe specific supplied inputs under a deterministic rule. CONFIRMED does not predict startup failure."/>
        <FindingGroup title="Hypotheses to validate" items={groups.hypotheses} allFindings={diagnostics.findings} description="These are founder-reported or incomplete hypotheses, not established business weaknesses."/>
        <FindingGroup title="Conflicted inputs" items={groups.conflicts} allFindings={diagnostics.findings} description="The rule withheld a conclusion where supplied values or measurement contexts conflict."/>
        <FindingGroup title="Information gaps" items={groups.informationGaps} allFindings={diagnostics.findings} description="These checks could not be evaluated from the supplied profile. Missing information is not treated as risk." collapsed/>
        <FindingGroup title="Other checks" items={groups.otherChecks} allFindings={diagnostics.findings} description="NOT_TRIGGERED means this rule did not trigger on the supplied inputs; NOT_APPLICABLE means its stated scope does not apply. Neither proves the business is safe." collapsed/>
        <p className="mt-5 border-t border-ink/10 pt-4 text-xs leading-relaxed text-muted">Engine {diagnostics.engine_version}. Diagnostics are recalculated for this saved profile and are separate from the historical model output, external research, and company examples.</p>
        {diagnostics.limitations.length > 0 && <details className="mt-3 text-sm">
          <summary className="flex min-h-11 cursor-pointer items-center font-semibold focus-visible:outline-2 focus-visible:outline-coral">Diagnostic limitations</summary>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">{diagnostics.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </details>}
      </>;
    })()}
    {viewState === "available" && !diagnostics?.profile_available && <p className="mt-5 rounded-xl border border-ink/10 p-4 text-sm" role="status">No applicable diagnostic data was returned. This is not evidence of a business weakness.</p>}
  </section>;
}
