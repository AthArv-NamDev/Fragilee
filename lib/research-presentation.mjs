const RESEARCH_STATES = {
  relevant_results: "Relevant records found",
  partial: "Partial results; some requests failed",
  no_results: "No provider records returned",
  filtered_out: "Records returned but filtered out",
  weak_relevance: "Retrieved records were weakly related",
  provider_unavailable: "Research provider unavailable",
  provider_timeout: "Research provider timed out",
  rate_limited: "Research provider rate limited the request",
  provider_error: "Research provider error",
  insufficient_query_context: "Not enough saved context to search",
};

const MATCH_CATEGORIES = {
  direct_business_model: "Explicit business-model overlap",
  industry_adjacent: "Industry-related example",
  mechanism_based: "Shared documented mechanism",
  contextual: "Contextual example",
};

export function researchStateLabel(state) {
  return RESEARCH_STATES[state] ?? "Research status unavailable";
}

export function historicalMatchLabel(category) {
  return MATCH_CATEGORIES[category] ?? MATCH_CATEGORIES.contextual;
}

export function evidenceRelationLabel(relation) {
  if (relation === "direct") return "Direct textual match: submitted profile terms and a selected-factor term occur in one abstract sentence; this does not establish startup-specific applicability.";
  if (relation === "contextual") return "Contextual textual match: profile and factor terms appear in the title or abstract, but not together in one sentence.";
  return "Textual relationship not recorded.";
}

export function evidenceAccessLabel(status) {
  if (status === "abstract_only") return "Abstract only; full text was not reviewed here.";
  if (status === "metadata_only") return "Metadata only; no abstract excerpt available.";
  if (status === "full_text_reviewed") return "Full text reviewed.";
  return "Access status not recorded.";
}
