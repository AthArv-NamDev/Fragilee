import test from "node:test";
import assert from "node:assert/strict";
import { resolveEvidenceReviewPresentation } from "./evidence-review-presentation.mjs";

test("failed evidence review reads never appear as confirmed empty records", () => {
  assert.deepEqual(resolveEvidenceReviewPresentation({
    loading: false, recordsUnavailable: true, associationCount: 0, comparisonCount: 0,
  }), {
    summary: "Review records unavailable",
    showEmptyAssociations: false,
    showEmptyComparisons: false,
  });
});

test("successful empty evidence review reads show explicit empty states", () => {
  assert.deepEqual(resolveEvidenceReviewPresentation({
    loading: false, recordsUnavailable: false, associationCount: 0, comparisonCount: 0,
  }), {
    summary: "0 associations · 0 comparison records",
    showEmptyAssociations: true,
    showEmptyComparisons: true,
  });
});

test("loading a different snapshot does not show stale counts or empty states", () => {
  assert.deepEqual(resolveEvidenceReviewPresentation({
    loading: true, recordsUnavailable: false, associationCount: 0, comparisonCount: 0,
  }), {
    summary: "Loading review records…",
    showEmptyAssociations: false,
    showEmptyComparisons: false,
  });
});

test("a failed write does not mark successfully loaded records unavailable", () => {
  assert.deepEqual(resolveEvidenceReviewPresentation({
    loading: false, recordsUnavailable: false, associationCount: 2, comparisonCount: 1,
  }), {
    summary: "2 associations · 1 comparison records",
    showEmptyAssociations: false,
    showEmptyComparisons: false,
  });
});
