import test from "node:test";
import assert from "node:assert/strict";
import { evidenceAccessLabel, evidenceRelationLabel, historicalMatchLabel, researchStateLabel } from "./research-presentation.mjs";

test("research states explain empty, partial, weak, and unavailable results distinctly", () => {
  assert.match(researchStateLabel("no_results"), /No provider records/);
  assert.match(researchStateLabel("filtered_out"), /filtered out/);
  assert.match(researchStateLabel("weak_relevance"), /weakly related/);
  assert.match(researchStateLabel("provider_unavailable"), /unavailable/);
  assert.match(researchStateLabel("provider_timeout"), /timed out/);
  assert.match(researchStateLabel("rate_limited"), /rate limited/);
  assert.match(researchStateLabel("partial"), /Partial/);
  assert.match(researchStateLabel("unknown"), /unavailable/);
});

test("historical match categories stay named and unknown values fall back to contextual", () => {
  assert.match(historicalMatchLabel("direct_business_model"), /business-model/);
  assert.match(historicalMatchLabel("mechanism_based"), /mechanism/);
  assert.match(historicalMatchLabel("industry_adjacent"), /Industry/);
  assert.match(historicalMatchLabel("new_value"), /Contextual/);
});

test("access labels never claim a full-text review from an absent status", () => {
  assert.match(evidenceAccessLabel("abstract_only"), /full text was not reviewed/);
  assert.match(evidenceAccessLabel("metadata_only"), /Metadata only/);
  assert.match(evidenceAccessLabel(undefined), /not recorded/);
});

test("direct abstract matches do not overstate that industry text was present", () => {
  assert.match(evidenceRelationLabel("direct"), /profile terms and a selected-factor term/);
  assert.match(evidenceRelationLabel("direct"), /does not establish startup-specific applicability/);
  assert.match(evidenceRelationLabel("contextual"), /not together in one sentence/);
});
