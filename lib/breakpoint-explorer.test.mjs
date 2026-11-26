import test from "node:test";
import assert from "node:assert/strict";
import { breakpointDomainLabel, breakpointStatusLabel, breakpointVisualSeverity, breakpointVisualState, groupBreakpoints, initialBreakpointId } from "./breakpoint-explorer.mjs";

const finding = (finding_id, category, status) => ({ finding_id, category, status });

test("groups findings by business mechanism while preserving engine order", () => {
  const items = [
    finding("market-1", "market_customer_validation", "INSUFFICIENT_INFORMATION"),
    finding("finance-1", "funding_runway", "HYPOTHESIS"),
    finding("market-2", "market_customer_validation", "CONFIRMED"),
  ];
  const groups = groupBreakpoints(items);
  assert.deepEqual(groups.map(({ label }) => label), ["Customer and market", "Cash and runway"]);
  assert.deepEqual(groups[0].findings.map(({ finding_id }) => finding_id), ["market-1", "market-2"]);
});

test("first selection prefers a supplied signal over information gaps without ranking severity", () => {
  const items = [
    finding("gap", "market_customer_validation", "INSUFFICIENT_INFORMATION"),
    finding("assumption", "market_customer_validation", "HYPOTHESIS"),
    finding("conflict", "funding_runway", "CONFLICTED"),
  ];
  assert.equal(initialBreakpointId(items), "assumption");
  assert.equal(initialBreakpointId([items[0]]), "gap");
  assert.equal(initialBreakpointId([]), null);
});

test("labels distinguish input state from a risk judgment", () => {
  assert.equal(breakpointStatusLabel("CONFIRMED"), "Measured input");
  assert.equal(breakpointStatusLabel("HYPOTHESIS"), "Assumption to validate");
  assert.equal(breakpointStatusLabel("INSUFFICIENT_INFORMATION"), "Information needed");
  assert.equal(breakpointDomainLabel("new_domain"), "New Domain");
});

test("tree severity colors use assigned if-true severity and neutralize gaps or untriggered checks", () => {
  assert.equal(breakpointVisualSeverity({ status: "HYPOTHESIS", severity_if_true: "Major" }), "Major");
  assert.equal(breakpointVisualSeverity({ status: "INDICATED", severity_if_true: "Critical" }), "Critical");
  assert.equal(breakpointVisualSeverity({ status: "INSUFFICIENT_INFORMATION", severity_if_true: "Major" }), "unrated");
  assert.equal(breakpointVisualSeverity({ status: "NOT_TRIGGERED", severity_if_true: "Moderate" }), "unrated");
  assert.equal(breakpointVisualSeverity({ status: "CONFLICTED", severity_if_true: null }), "unrated");
});

test("tree can color evidence states without inventing severity", () => {
  assert.equal(breakpointVisualState({ status: "CONFIRMED" }), "measured");
  assert.equal(breakpointVisualState({ status: "INDICATED" }), "estimated");
  assert.equal(breakpointVisualState({ status: "HYPOTHESIS" }), "hypothesis");
  assert.equal(breakpointVisualState({ status: "CONFLICTED" }), "conflicted");
  assert.equal(breakpointVisualState({ status: "INSUFFICIENT_INFORMATION" }), "information");
  assert.equal(breakpointVisualState({ status: "NOT_TRIGGERED" }), "neutral");
  assert.equal(breakpointVisualState({ status: "HYPOTHESIS", severity_if_true: "Major" }), "severity");
});
