"use client";

import { useState } from "react";
import type { EvidenceSource } from "@/lib/types";
import { evidenceAccessLabel, evidenceRelationLabel } from "@/lib/research-presentation.mjs";

export default function EvidenceResults({ sources, compact = false }: { sources: EvidenceSource[]; compact?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? sources : sources.slice(0, 3);
  return <>
    <ul className={compact ? "mt-3 space-y-2" : "mt-4 grid gap-3 md:grid-cols-2"}>
      {shown.map((source) => (
        <li key={source.doi || source.url} className="rounded-xl bg-ink/5 p-3">
          <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-sm font-semibold underline underline-offset-4 hover:text-coral">{source.title}</a>
          <p className="mt-1 text-xs text-muted">
            {source.authors?.length ? `${source.authors.slice(0, 2).join(", ")}${source.authors.length > 2 ? " et al." : ""} · ` : ""}
            {[source.journal || source.publisher, source.year || source.published?.slice(0, 4), source.publication_type !== "unknown" ? source.publication_type : "", source.venue_status].filter(Boolean).join(" · ")}
          </p>
          <p className="mt-2 text-xs text-muted">{evidenceRelationLabel(source.relation)}</p>
          {(source.relevance_dimensions?.length ?? 0) > 0 && <p className="mt-1 text-xs text-muted">Retrieved for: {(source.relevance_dimensions ?? []).join(" · ")}</p>}
          {(source.matched_terms?.length ?? 0) > 0 && <p className="mt-1 text-xs text-muted">Matched title/abstract terms: {(source.matched_terms ?? []).join(", ")}</p>}
          {source.doi && <p className="mt-1 break-all text-[11px] text-muted">DOI: {source.doi.replace(/^https?:\/\/doi.org\//, "")}</p>}
          <details className="mt-3 border-t border-ink/10 pt-2">
            <summary className="min-h-11 cursor-pointer py-2 text-xs font-semibold text-muted focus-visible:outline-2 focus-visible:outline-coral">Source excerpt and record limits</summary>
            <p className="mt-1 text-xs font-semibold">Abstract excerpt (source text)</p>
            <p className="mt-1 text-xs leading-relaxed text-muted">{source.excerpt}</p>
            <dl className="mt-3 grid gap-1 text-[11px] text-muted">
              {source.metadata_status && <div><dt className="inline font-semibold">Record: </dt><dd className="inline">{source.metadata_status}</dd></div>}
              {source.access_status && <div><dt className="inline font-semibold">Access: </dt><dd className="inline">{evidenceAccessLabel(source.access_status)}</dd></div>}
              {source.openalex_id && <div><dt className="inline font-semibold">OpenAlex ID: </dt><dd className="inline break-all">{source.openalex_id}</dd></div>}
              {source.retrieved_at && <div><dt className="inline font-semibold">Retrieved: </dt><dd className="inline">{source.retrieved_at}</dd></div>}
              {source.open_access_url && <div><dt className="inline font-semibold">Access link: </dt><dd className="inline"><a href={source.open_access_url} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:text-coral">Open access location</a></dd></div>}
            </dl>
          </details>
        </li>
      ))}
    </ul>
    {sources.length > 3 && <button type="button" onClick={() => setExpanded((value) => !value)} className="mt-3 min-h-11 rounded-lg px-3 text-sm font-semibold text-coral underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-coral">
      {expanded ? "Show fewer results" : `Show ${sources.length - 3} more results`}
    </button>}
  </>;
}
