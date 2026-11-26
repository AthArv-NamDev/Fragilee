"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { apiFetch } from "@/lib/api";
import { resolveEvidenceReviewPresentation } from "@/lib/evidence-review-presentation.mjs";
import type { ContradictionAssessment, EvidenceAssociation, EvidenceResponse } from "@/lib/types";

const categories = [
  ["historical_case_fact", "Historical case fact"],
  ["general_research_finding", "General research finding"],
  ["startup_specific_interpretation", "Startup-specific interpretation"],
  ["recommendation", "Recommendation"],
] as const;
const relationships = [
  ["supports", "Supports (proposed)"],
  ["partially_supports", "Partially supports (proposed)"],
  ["contextualizes", "Contextualizes (proposed)"],
  ["contradicts", "Contradicts (proposed)"],
  ["insufficient", "Insufficient evidence"],
] as const;
const contradictionNatures = [
  ["genuine_disagreement", "Possible genuine disagreement"],
  ["different_population", "Different populations"],
  ["different_geography", "Different geographies"],
  ["different_period", "Different periods"],
  ["different_definition", "Different definitions or measures"],
  ["different_methodology", "Different methods"],
  ["complementary", "Potentially complementary findings"],
  ["insufficient_information", "Not enough information to compare"],
] as const;

function label(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (char) => char.toUpperCase());
}

export default function EvidenceTraceability({ analysisId, research }: { analysisId: string; research: EvidenceResponse }) {
  const [associations, setAssociations] = useState<EvidenceAssociation[]>([]);
  const [contradictions, setContradictions] = useState<ContradictionAssessment[]>([]);
  const [loadedDataKey, setLoadedDataKey] = useState<string | null>(null);
  const [unavailableDataKey, setUnavailableDataKey] = useState<string | null>(null);
  const dataKey = `${analysisId}:${research.snapshot_id ?? "none"}`;
  const loading = loadedDataKey !== dataKey;
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [claim, setClaim] = useState("");
  const [category, setCategory] = useState<(typeof categories)[number][0]>("general_research_finding");
  const [sourceId, setSourceId] = useState("");
  const [relationship, setRelationship] = useState<(typeof relationships)[number][0]>("contextualizes");
  const [saving, setSaving] = useState(false);
  const [firstAssociation, setFirstAssociation] = useState("");
  const [secondAssociation, setSecondAssociation] = useState("");
  const [contradictionNature, setContradictionNature] = useState<(typeof contradictionNatures)[number][0]>("insufficient_information");
  const [contradictionText, setContradictionText] = useState("");
  const [reviewRelationship, setReviewRelationship] = useState<Record<string, (typeof relationships)[number][0]>>({});
  const [reviewNature, setReviewNature] = useState<Record<string, (typeof contradictionNatures)[number][0]>>({});
  const [reviewerNotes, setReviewerNotes] = useState<Record<string, string>>({});
  const [scanCursor, setScanCursor] = useState<{ snapshotId: string | null; offset: number }>({ snapshotId: null, offset: 0 });
  const currentSnapshotId = research.snapshot_id ?? null;
  const scanOffset = scanCursor.snapshotId === currentSnapshotId ? scanCursor.offset : 0;

  const savedSources = research.sources ?? [];
  const selectedSource = savedSources.find((source) => (source.openalex_id || source.doi || source.url) === sourceId) ?? savedSources[0];
  const activeSourceId = selectedSource ? (selectedSource.openalex_id || selectedSource.doi || selectedSource.url) : "";
  const recordsUnavailable = unavailableDataKey === dataKey;
  const visibleAssociations = useMemo(
    () => loadedDataKey === dataKey && !recordsUnavailable ? associations : [],
    [loadedDataKey, dataKey, recordsUnavailable, associations],
  );
  const visibleContradictions = loadedDataKey === dataKey && !recordsUnavailable ? contradictions : [];
  const reviewPresentation = resolveEvidenceReviewPresentation({
    loading, recordsUnavailable, associationCount: visibleAssociations.length, comparisonCount: visibleContradictions.length,
  });
  const passageAssociations = useMemo(() => visibleAssociations.filter((item) => item.is_current && item.exact_passage_text), [visibleAssociations]);

  async function reload() {
    const snapshotId = research.snapshot_id;
    const currentDataKey = `${analysisId}:${snapshotId ?? "none"}`;
    try {
      const [links, disagreements] = await Promise.all([
        apiFetch<{ associations: EvidenceAssociation[] }>(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/associations${snapshotId ? `?snapshot_id=${encodeURIComponent(snapshotId)}` : ""}`),
        apiFetch<{ assessments: ContradictionAssessment[] }>(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/contradictions`),
      ]);
      setAssociations(links.associations);
      setContradictions(disagreements.assessments);
      setUnavailableDataKey(null);
      setError("");
      setLoadedDataKey(currentDataKey);
    } catch {
      setUnavailableDataKey(currentDataKey);
      setLoadedDataKey(currentDataKey);
      setError("Saved evidence review data is unavailable. Existing research remains unchanged.");
    }
  }

  useEffect(() => {
    const snapshotId = research.snapshot_id;
    const currentDataKey = `${analysisId}:${snapshotId ?? "none"}`;
    let current = true;
    const snapshotQuery = snapshotId ? `?snapshot_id=${encodeURIComponent(snapshotId)}` : "";
    Promise.all([
      apiFetch<{ associations: EvidenceAssociation[] }>(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/associations${snapshotQuery}`),
      apiFetch<{ assessments: ContradictionAssessment[] }>(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/contradictions`),
    ]).then(([links, disagreements]) => {
      if (!current) return;
      setAssociations(links.associations);
      setContradictions(disagreements.assessments);
      setUnavailableDataKey(null);
      setError("");
      setLoadedDataKey(currentDataKey);
    }).catch(() => {
      if (current) {
        setUnavailableDataKey(currentDataKey);
        setLoadedDataKey(currentDataKey);
        setError("Saved evidence review data is unavailable. Existing research remains unchanged.");
      }
    });
    return () => { current = false; };
  }, [analysisId, research.snapshot_id]);

  async function submitAssociation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!research.snapshot_id || !research.snapshot_saved || !selectedSource) return;
    setSaving(true); setError(""); setNotice("");
    const id = selectedSource.openalex_id || selectedSource.doi || selectedSource.url;
    try {
      await apiFetch(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/associations`, {
        method: "POST",
        body: JSON.stringify({
          snapshot_id: research.snapshot_id,
          claim_text: claim.trim(), claim_category: category, source_id: id,
          source_access: selectedSource.access_status === "metadata_only" ? "metadata_only" : "abstract_excerpt",
          exact_passage_text: selectedSource.access_status === "metadata_only" ? null : selectedSource.excerpt,
          passage_location: selectedSource.access_status === "metadata_only" ? null : "Abstract",
          source_url: selectedSource.url,
          publication: {
            title: selectedSource.title, url: selectedSource.url,
            publisher: selectedSource.publisher || null, journal: selectedSource.journal || null,
            authors: selectedSource.authors || [], doi: selectedSource.doi || null,
            published: selectedSource.published || null, year: selectedSource.year || null,
          },
          relationship, limitations: ["Founder-submitted relationship is pending human review."],
        }),
      });
      setClaim(""); setNotice("Evidence association saved as pending review.");
      await reload();
    } catch {
      setError("The evidence association was not saved. Please retry; no saved evidence was overwritten.");
    } finally { setSaving(false); }
  }

  async function reviewAssociation(item: EvidenceAssociation, state: "verified" | "rejected") {
    setError(""); setNotice("");
    try {
      await apiFetch(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/associations/${encodeURIComponent(item.record_id)}/review`, {
        method: "POST", body: JSON.stringify({ relationship: item.relationship, verification_state: state,
          limitations: state === "verified" ? ["Human review confirms only the stated passage-to-claim relationship; it does not establish startup-specific causality."] : ["Human reviewer rejected this proposed relationship."] }),
      });
      setNotice(state === "verified" ? "A human-reviewed version was appended." : "A rejection record was appended.");
      await reload();
    } catch { setError("Review could not be saved. The prior record remains unchanged."); }
  }

  async function submitContradiction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!firstAssociation || !secondAssociation || firstAssociation === secondAssociation) return;
    setSaving(true); setError(""); setNotice("");
    try {
      await apiFetch(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/contradictions`, {
        method: "POST", body: JSON.stringify({ association_ids: [firstAssociation, secondAssociation],
          nature: contradictionNature, assessment_text: contradictionText.trim(),
          limitations: ["Manual abstract-based candidate; this is not a finding that the studies genuinely conflict."] }),
      });
      setContradictionText(""); setNotice("Contradiction candidate saved as pending review.");
      await reload();
    } catch { setError("The contradiction candidate was not saved. Previously saved assessments remain unchanged."); }
    finally { setSaving(false); }
  }

  async function comparePassages(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!firstAssociation || !secondAssociation || firstAssociation === secondAssociation) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const result = await apiFetch<ContradictionAssessment & { reused_existing?: boolean }>(
        `/v1/analyses/${encodeURIComponent(analysisId)}/evidence/contradictions/compare`,
        { method: "POST", body: JSON.stringify({ association_ids: [firstAssociation, secondAssociation] }) },
      );
      setNotice(result.reused_existing
        ? "This evidence pair already has a comparison; its saved review history was kept."
        : "A provisional excerpt comparison was saved for human review. It is not a scientific conclusion.");
      await reload();
    } catch {
      setError("The comparison could not be saved. Existing evidence and review history remain unchanged.");
    } finally { setSaving(false); }
  }

  async function scanSnapshot() {
    if (!research.snapshot_id || !research.snapshot_saved || passageAssociations.length === 0) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const result = await apiFetch<{
        state: "complete" | "partial"; created: number; reused_existing: number;
        skipped_insufficient: number; skipped_not_disagreement: number; truncated: boolean; next_offset: number; message: string;
      }>(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/contradictions/detect`, {
        method: "POST", body: JSON.stringify({ snapshot_id: research.snapshot_id, offset: scanOffset }),
      });
      setScanCursor({ snapshotId: currentSnapshotId, offset: result.truncated ? result.next_offset : 0 });
      setNotice(`${result.message}${result.truncated ? " Scan was bounded; repeat after reviewing saved candidates to continue." : ""}`);
      await reload();
    } catch {
      setError("The scan could not read or save comparison data. Existing source snapshots and review records remain unchanged.");
    } finally { setSaving(false); }
  }

  async function reviewContradiction(item: ContradictionAssessment, state: "verified" | "rejected", forceInsufficient = false) {
    setError(""); setNotice("");
    const chosenRelationship = forceInsufficient ? "insufficient" : (reviewRelationship[item.record_id] || item.relationship || "insufficient");
    const chosenNature = forceInsufficient ? "insufficient_information" : (reviewNature[item.record_id] || item.nature);
    const reviewerExplanation = reviewerNotes[item.record_id]?.trim();
    if (!reviewerExplanation) {
      setError("Add a short reviewer explanation before recording a decision.");
      return;
    }
    try {
      await apiFetch(`/v1/analyses/${encodeURIComponent(analysisId)}/evidence/contradictions/${encodeURIComponent(item.record_id)}/review`, {
        method: "POST", body: JSON.stringify({ verification_state: state, nature: chosenNature,
          relationship: chosenRelationship, reviewer_explanation: reviewerExplanation,
          assessment_text: reviewerExplanation,
          limitations: [...item.limitations, state === "verified" ? "Human-reviewed comparison; conclusions remain limited to the available excerpts." : "Human reviewer rejected this comparison candidate."] }),
      });
      setNotice("A new contradiction review version was appended."); await reload();
    } catch { setError("Contradiction review could not be saved. The previous assessment remains unchanged."); }
  }

  return <details className="mt-5 rounded-2xl border border-ink/10 bg-dark-surface/70 p-4 md:p-5">
    <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 font-semibold focus-visible:outline-2 focus-visible:outline-coral">
      <span>Evidence traceability and review</span><span className="text-xs font-normal text-muted">{reviewPresentation.summary}</span>
    </summary>
    <div className="mt-3 space-y-4 text-sm">
      <p className="text-xs leading-relaxed text-muted">Retrieved sources and abstract excerpts are not automatically evidence for a claim. New links remain pending until a person reviews them. No full-text passages are available in this saved retrieval.</p>
      {!research.snapshot_saved || !research.snapshot_id ? <p className="rounded-xl border border-ink/10 p-3 text-xs" role="status">This retrieval is not a saved snapshot, so claim links cannot be persisted against it.</p> : savedSources.length === 0 ? <p className="rounded-xl border border-ink/10 p-3 text-xs text-muted" role="status">This snapshot contains no source passages to associate with a claim.</p> : <form className="grid gap-3 rounded-xl border border-ink/10 p-3 md:grid-cols-2" onSubmit={submitAssociation}>
        <label className="md:col-span-2"><span className="mb-1 block text-xs font-semibold">Statement to trace</span><textarea required maxLength={10000} value={claim} onChange={(event) => setClaim(event.target.value)} className="min-h-20 w-full rounded-xl border border-ink/15 bg-dark-surface p-3 text-sm focus-visible:outline-2 focus-visible:outline-coral" placeholder="Enter a specific statement and keep it separate from its source."/></label>
        <label className="grid gap-1 text-xs font-semibold">Claim category<select value={category} onChange={(event) => setCategory(event.target.value as typeof category)} className="min-h-11 rounded-xl border border-ink/15 bg-dark-surface px-3 text-sm">{categories.map(([value, text]) => <option key={value} value={value} disabled={value === "historical_case_fact"}>{value === "historical_case_fact" ? `${text} (case passages not available here)` : text}</option>)}</select></label>
        <label className="grid gap-1 text-xs font-semibold">Saved source<select value={activeSourceId} onChange={(event) => setSourceId(event.target.value)} className="min-h-11 rounded-xl border border-ink/15 bg-dark-surface px-3 text-sm">{savedSources.map((source) => { const id = source.openalex_id || source.doi || source.url; return <option key={id} value={id}>{source.title}</option>; })}</select></label>
        <label className="grid gap-1 text-xs font-semibold md:col-span-2">Proposed relationship<select value={relationship} onChange={(event) => setRelationship(event.target.value as typeof relationship)} className="min-h-11 rounded-xl border border-ink/15 bg-dark-surface px-3 text-sm">{relationships.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>
        <button type="submit" disabled={saving || !savedSources.length} className="min-h-11 rounded-full bg-coral px-5 font-semibold text-coral-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral disabled:opacity-60">{saving ? "Saving…" : "Save pending evidence link"}</button>
      </form>}

      {loading && <p className="text-xs text-muted" role="status">Loading saved evidence review records…</p>}
      {error && <p className="rounded-xl border border-coral/30 p-3 text-xs text-coral" role="alert">{error}</p>}
      {notice && <p className="rounded-xl border border-ink/10 p-3 text-xs" role="status">{notice}</p>}
      {reviewPresentation.showEmptyAssociations && <p className="rounded-xl border border-dashed border-ink/15 p-3 text-xs text-muted">No claim-level associations have been saved for this analysis or snapshot.</p>}
      {visibleAssociations.length > 0 && <ul className="space-y-3">{visibleAssociations.map((item) => <li key={item.record_id} className="rounded-xl border border-ink/10 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-semibold">{label(item.claim_category)} · {label(item.relationship)}</p><span className="rounded-full border border-ink/15 px-2.5 py-1 text-[11px]">{item.verification_state === "verified" ? "Human verified" : label(item.verification_state)}</span></div>
        <p className="mt-2">{item.claim_text}</p>
        {item.exact_passage_text ? <blockquote className="mt-3 border-l-2 border-coral/60 pl-3 text-xs leading-relaxed text-muted"><span className="font-semibold text-text">{item.source_access === "abstract_excerpt" ? "Abstract excerpt" : "Full-text passage"} · {item.publication.title}</span><br/>{item.exact_passage_text}{item.passage_location ? <span className="block mt-1">Location: {item.passage_location}</span> : <span className="block mt-1">Passage location not recorded.</span>}</blockquote> : <p className="mt-2 text-xs text-muted">Metadata only; no passage was inspected.</p>}
        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted"><span>{item.publication.authors?.join(", ") || "Authors unavailable"}</span><span>{item.publication.year || item.publication.published || "Date unavailable"}</span><span>{label(item.source_access)}</span><a className="underline underline-offset-2" href={item.source_url} target="_blank" rel="noopener noreferrer">Open source</a><span>Snapshot {item.snapshot_id.slice(0, 8)}</span></div>
        {item.limitations.length > 0 && <p className="mt-2 text-xs text-muted">Limits: {item.limitations.join(" ")}</p>}
        {item.is_current && item.verification_state === "pending_review" && <div className="mt-3 flex flex-wrap gap-2"><button type="button" onClick={() => void reviewAssociation(item, "verified")} className="min-h-11 rounded-full border border-ink/15 px-3 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-coral">Human review: verify relationship</button><button type="button" onClick={() => void reviewAssociation(item, "rejected")} className="min-h-11 rounded-full border border-ink/15 px-3 text-xs font-semibold text-muted focus-visible:outline-2 focus-visible:outline-coral">Reject relationship</button></div>}
        {!item.is_current && <p className="mt-2 text-[11px] text-muted">Historical version · retained for review history.</p>}
      </li>)}</ul>}

      <section className="rounded-xl border border-ink/10 p-3" aria-labelledby="contradiction-heading">
        <h3 id="contradiction-heading" className="font-semibold">Compare two saved passages</h3>
        <p className="mt-1 text-xs text-muted">The comparison uses only exact saved passages and linked claim text. Its phrase rules are conservative; all results remain provisional until a person reviews them. Reopening the report does not generate comparisons. A new snapshot must have new evidence links before it can be compared; old comparisons remain tied to their original snapshots.</p>
        <button type="button" onClick={() => void scanSnapshot()} disabled={saving || !research.snapshot_id || !research.snapshot_saved || passageAssociations.length === 0} className="mt-3 min-h-11 rounded-full bg-coral px-4 text-xs font-semibold text-coral-ink focus-visible:outline-2 focus-visible:outline-coral disabled:opacity-50">{saving ? "Scanning…" : scanOffset ? `Continue scan from pair ${scanOffset + 1}` : "Scan this snapshot for disagreements"}</button>
        <p className="mt-2 text-xs text-muted">The scan compares this snapshot&apos;s current passage links with each other and current links from earlier snapshots. It stores only potential disagreements/context candidates; support and insufficient pairs are not treated as conflicts.</p>
        {passageAssociations.length < 2 ? <p className="mt-3 rounded-lg border border-dashed border-ink/15 p-3 text-xs text-muted">Save claim links for two inspected passages to compare them. Metadata-only sources cannot be compared as findings.</p> : <form className="mt-3 grid gap-2 md:grid-cols-2" onSubmit={comparePassages}>
          {[{ value: firstAssociation, set: setFirstAssociation, label: "First statement" }, { value: secondAssociation, set: setSecondAssociation, label: "Second statement" }].map((select) => <label key={select.label} className="grid gap-1 text-xs font-semibold">{select.label}<select required value={select.value} onChange={(event) => select.set(event.target.value)} className="min-h-11 rounded-xl border border-ink/15 bg-dark-surface px-3 text-xs"><option value="">Choose a saved passage</option>{passageAssociations.map((item) => <option key={item.record_id} value={item.record_id}>{item.claim_text.slice(0, 90)} · {item.publication.title.slice(0, 55)}</option>)}</select></label>)}
          <button type="submit" disabled={saving || firstAssociation === secondAssociation} className="min-h-11 rounded-full bg-coral px-4 text-xs font-semibold text-coral-ink focus-visible:outline-2 focus-visible:outline-coral disabled:opacity-50">{saving ? "Comparing…" : "Compare saved excerpts"}</button>
        </form>}
        {passageAssociations.length >= 2 && <>
        <details className="mt-3 rounded-lg border border-ink/10 p-3">
          <summary className="min-h-11 cursor-pointer py-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-coral">Record a manual comparison</summary>
          <form className="mt-2 grid gap-2" onSubmit={submitContradiction}>
            <label className="grid gap-1 text-xs font-semibold">Possible explanation<select value={contradictionNature} onChange={(event) => setContradictionNature(event.target.value as typeof contradictionNature)} className="min-h-11 rounded-xl border border-ink/15 bg-dark-surface px-3 text-sm">{contradictionNatures.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label>
            <label className="grid gap-1 text-xs font-semibold">Why should these be compared?<textarea required maxLength={5000} value={contradictionText} onChange={(event) => setContradictionText(event.target.value)} className="min-h-16 rounded-xl border border-ink/15 bg-dark-surface p-3 text-sm"/></label>
            <button type="submit" disabled={saving || firstAssociation === secondAssociation || !firstAssociation} className="min-h-11 w-fit rounded-full border border-ink/15 px-4 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-coral disabled:opacity-50">Save manual candidate for review</button>
          </form>
        </details>
        </>}
      </section>
      {reviewPresentation.showEmptyComparisons && <p className="rounded-xl border border-dashed border-ink/15 p-3 text-xs text-muted">No research comparisons have been recorded. Comparing passages is an explicit action.</p>}
      {visibleContradictions.length > 0 && <div><h3 className="font-semibold">Research disagreements and comparisons</h3><ul className="mt-2 space-y-3">{visibleContradictions.map((item) => <li key={item.record_id} className="rounded-xl border border-ink/10 p-3 text-xs">
        <div className="flex flex-wrap justify-between gap-2"><strong>{item.relationship === "contradicts" ? "Potential contradiction" : item.relationship === "partially_supports" ? "Partial disagreement" : item.relationship === "contextualizes" ? "Contextual difference" : item.relationship === "supports" ? "Potentially complementary evidence" : item.relationship ? "Insufficient evidence" : label(item.nature)}</strong><span className="rounded-full border border-ink/15 px-2 py-1">{item.verification_state === "verified" ? "Human reviewed" : label(item.verification_state)} · {item.is_current ? "Current" : "Historical version"}</span></div>
        <p className="mt-2">{item.assessment_text}</p>
        {item.compared_evidence?.length === 2 && <p className="mt-2 text-muted">Linked claim A: {item.compared_evidence[0].claim_text} Linked claim B: {item.compared_evidence[1].claim_text}</p>}
        {item.context_differences?.length ? <div className="mt-2"><strong>Context differences:</strong> {item.context_differences.join(" ")}</div> : null}
        {item.uncertainty_explanation && <p className="mt-2"><strong>Uncertainty:</strong> {item.uncertainty_explanation}</p>}
        {item.reviewer_explanation && <p className="mt-2"><strong>Reviewer explanation:</strong> {item.reviewer_explanation}</p>}
        {item.reviewer_id && item.reviewed_at && <p className="mt-2 text-muted">Reviewed by the authenticated analysis owner · {new Date(item.reviewed_at).toLocaleDateString()}</p>}
        <details className="mt-2 rounded-lg border border-ink/10 p-3"><summary className="min-h-11 cursor-pointer py-2 font-semibold focus-visible:outline-2 focus-visible:outline-coral">Inspect exact source excerpts and provenance</summary>{item.compared_evidence?.map((evidence) => <blockquote key={evidence.association_id} className="mt-3 max-h-64 overflow-auto break-words border-l-2 border-coral/60 pl-3 leading-relaxed text-muted"><span className="font-semibold text-text">{evidence.publication.title} · {label(evidence.source_access)}</span><br/><span className="text-text">Linked claim: {evidence.claim_text}</span><br/>{evidence.exact_passage_text}<span className="mt-1 block">{evidence.publication.authors?.join(", ") || "Authors unavailable"} · {evidence.publication.year || evidence.publication.published || "Publication date unavailable"} · Snapshot {evidence.snapshot_id.slice(0, 8)} · {evidence.passage_location || "location not recorded"} · <a className="underline underline-offset-2" href={evidence.source_url} target="_blank" rel="noopener noreferrer">Open source</a></span></blockquote>)}<p className="mt-2 text-muted">{item.limitations.join(" ")} {item.source_access_limitations?.join(" ")}</p></details>
        {item.is_current && item.verification_state === "pending_review" && <div className="mt-3 space-y-2 rounded-lg bg-ink/5 p-3">
          <p className="font-semibold">Review this provisional comparison</p>
          <div className="grid gap-2 md:grid-cols-2"><label className="grid gap-1">Classification<select aria-label="Correct comparison classification" value={reviewRelationship[item.record_id] || item.relationship || "insufficient"} onChange={(event) => setReviewRelationship((current) => ({ ...current, [item.record_id]: event.target.value as (typeof relationships)[number][0] }))} className="min-h-11 rounded-lg border border-ink/15 bg-dark-surface px-2">{relationships.map(([value, text]) => <option key={value} value={value}>{text.replace(" (proposed)", "")}</option>)}</select></label>
            <label className="grid gap-1">Context assessment<select aria-label="Context difference classification" value={reviewNature[item.record_id] || item.nature} onChange={(event) => setReviewNature((current) => ({ ...current, [item.record_id]: event.target.value as (typeof contradictionNatures)[number][0] }))} className="min-h-11 rounded-lg border border-ink/15 bg-dark-surface px-2">{contradictionNatures.map(([value, text]) => <option key={value} value={value}>{text}</option>)}</select></label></div>
          <label className="grid gap-1">Reviewer explanation <textarea maxLength={5000} value={reviewerNotes[item.record_id] || ""} onChange={(event) => setReviewerNotes((current) => ({ ...current, [item.record_id]: event.target.value }))} className="min-h-16 rounded-lg border border-ink/15 bg-dark-surface p-2" placeholder="What did you inspect, and what limitations remain?"/></label>
          <div className="flex flex-wrap gap-2"><button type="button" onClick={() => void reviewContradiction(item, "verified")} className="min-h-11 rounded-full border border-ink/15 px-3 font-semibold focus-visible:outline-2 focus-visible:outline-coral">Save human-reviewed classification</button><button type="button" onClick={() => void reviewContradiction(item, "verified", true)} className="min-h-11 rounded-full border border-ink/15 px-3 focus-visible:outline-2 focus-visible:outline-coral">Mark insufficient evidence</button><button type="button" onClick={() => void reviewContradiction(item, "rejected")} className="min-h-11 rounded-full border border-ink/15 px-3 text-muted focus-visible:outline-2 focus-visible:outline-coral">Reject candidate</button></div>
        </div>}
      </li>)}</ul></div>}
    </div>
  </details>;
}
