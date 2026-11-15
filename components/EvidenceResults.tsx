"use client";

import { useState } from "react";
import type { EvidenceSource } from "@/lib/types";

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
            {source.journal || source.publisher}{source.year ? ` · ${source.year}` : source.published ? ` · ${source.published.slice(0, 4)}` : ""} · {source.venue_status} · {source.relation === "direct" ? "direct abstract support" : "contextual evidence"}
          </p>
          {source.doi && <p className="mt-1 break-all text-[11px] text-muted">DOI: {source.doi.replace(/^https?:\/\/doi.org\//, "")}</p>}
          <p className="mt-1 text-xs text-muted">Matched: {source.matched_terms.join(" · ")}</p>
          <details className="mt-2">
            <summary className="cursor-pointer text-xs font-semibold text-muted">View supporting abstract excerpt</summary>
            <p className="mt-2 text-xs leading-relaxed text-ink/80">{source.excerpt}</p>
          </details>
        </li>
      ))}
    </ul>
    {sources.length > 3 && <button type="button" onClick={() => setExpanded((value) => !value)} className="mt-3 min-h-11 rounded-lg px-3 text-sm font-semibold text-coral underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-coral">
      {expanded ? "Show fewer results" : `Show ${sources.length - 3} more results`}
    </button>}
  </>;
}
