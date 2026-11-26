export function resolveEvidenceReviewPresentation(input: {
  loading: boolean;
  recordsUnavailable: boolean;
  associationCount: number;
  comparisonCount: number;
}): {
  summary: string;
  showEmptyAssociations: boolean;
  showEmptyComparisons: boolean;
};
