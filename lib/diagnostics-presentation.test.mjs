import test from "node:test";
import assert from "node:assert/strict";
import { diagnosticEvidenceLabels, formatDiagnosticCalculatedValue, formatDiagnosticInput, groupDiagnosticFindings, resolveDiagnosticViewState } from "./diagnostics-presentation.mjs";

const finding = (status, id = status) => ({ finding_id: id, status });

test("groups every engine status without changing its status vocabulary", () => {
  const groups = groupDiagnosticFindings([
    finding("CONFIRMED"), finding("INDICATED"), finding("HYPOTHESIS"), finding("CONFLICTED"),
    finding("INSUFFICIENT_INFORMATION"), finding("NOT_TRIGGERED"), finding("NOT_APPLICABLE"),
  ]);
  assert.deepEqual(groups.supported.map((item) => item.status), ["CONFIRMED", "INDICATED"]);
  assert.deepEqual(groups.hypotheses.map((item) => item.status), ["HYPOTHESIS"]);
  assert.deepEqual(groups.conflicts.map((item) => item.status), ["CONFLICTED"]);
  assert.deepEqual(groups.informationGaps.map((item) => item.status), ["INSUFFICIENT_INFORMATION"]);
  assert.deepEqual(groups.otherChecks.map((item) => item.status), ["NOT_TRIGGERED", "NOT_APPLICABLE"]);
});

test("founder metric provenance, currency, units, ranges and unknown states remain visible", () => {
  assert.deepEqual(formatDiagnosticInput({ field: "profile.finance.metrics[0]", value: {
    field_id: "cash_balance", range_low: 100, range_high: 200, unit: "currency", currency: "INR", provenance: "estimated",
  } }), { label: "cash balance", value: "100–200 INR Estimated", provenance: "estimated" });
  assert.deepEqual(formatDiagnosticInput({ field: "profile.economics.metrics[0]", value: {
    field_id: "runway", provenance: "unknown",
  } }), { label: "runway", value: "Unknown", provenance: "unknown" });
});

test("calculated contribution values display currency and unit without inventing severity", () => {
  assert.equal(formatDiagnosticCalculatedValue("contribution_low", -4, { currency: "INR", unit: "currency/order" }), "INR -4 / order");
  assert.equal(formatDiagnosticCalculatedValue("buyer_to_seller_ratio", 2.5, {}), "2.5");
  assert.equal(formatDiagnosticCalculatedValue("ratio", null, {}), "Not calculated");
});

test("evidence strength, status, and severity stay separate", () => {
  assert.deepEqual(diagnosticEvidenceLabels({ status: "CONFIRMED", evidence_strength: "High", severity_if_true: null }), {
    status: "CONFIRMED", evidenceStrength: "High", severity: "Severity not assigned",
  });
  assert.deepEqual(diagnosticEvidenceLabels({ status: "HYPOTHESIS", evidence_strength: "Low", severity_if_true: "Major" }), {
    status: "HYPOTHESIS", evidenceStrength: "Low", severity: "Major",
  });
});

test("legacy, empty, and failed diagnostic responses stay distinct", () => {
  assert.equal(resolveDiagnosticViewState("no_profile", { profile_available: false }), "no_profile");
  assert.equal(resolveDiagnosticViewState("available", { profile_available: true }), "available");
  assert.equal(resolveDiagnosticViewState("unavailable", null), "unavailable");
  assert.equal(resolveDiagnosticViewState("available", null), "unavailable");
  assert.equal(resolveDiagnosticViewState(undefined, undefined), "unavailable");
});
