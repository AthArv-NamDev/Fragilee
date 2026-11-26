export function resolveEvidenceReviewPresentation({ loading, recordsUnavailable, associationCount, comparisonCount }) {
  return {
    summary: recordsUnavailable
      ? "Review records unavailable"
      : loading
        ? "Loading review records…"
        : `${associationCount} associations · ${comparisonCount} comparison records`,
    showEmptyAssociations: !loading && !recordsUnavailable && associationCount === 0,
    showEmptyComparisons: !loading && !recordsUnavailable && comparisonCount === 0,
  };
}
