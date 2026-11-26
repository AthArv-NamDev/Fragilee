import test from "node:test";
import assert from "node:assert/strict";
import { formatProfileMetric, formatProfileUpdatedAt, shouldDisplayLegacyTeamSize, shouldDisplayStructuredRevenueModel } from "./profile-presentation.mjs";

test("renders partial numeric ranges without printing undefined", () => {
  assert.equal(formatProfileMetric({ field_id: "cash_balance", range_low: 100, unit: "currency", currency: "INR", provenance: "estimated" }), "at least 100 INR Estimated");
  assert.equal(formatProfileMetric({ field_id: "cash_balance", range_high: 500, unit: "currency", currency: "INR", provenance: "estimated" }), "up to 500 INR Estimated");
  assert.equal(formatProfileMetric({ field_id: "cash_balance", range_low: 100, range_high: 500, unit: "currency", currency: "INR", provenance: "estimated" }), "100–500 INR Estimated");
});

test("renders values, unit, currency, period and provenance with spacing", () => {
  assert.equal(formatProfileMetric({ field_id: "revenue_amount", value: 1200, unit: "currency", currency: "INR", period: "month", provenance: "measured" }), "1200 INR / month Measured");
  assert.equal(formatProfileMetric({ field_id: "customer_acquisition_cost", value: 90, unit: "currency/customer", currency: "USD", provenance: "estimated" }), "90 USD / customer Estimated");
});

test("missing and invalid profile timestamps use a readable fallback", () => {
  assert.equal(formatProfileUpdatedAt(undefined), "date not recorded");
  assert.equal(formatProfileUpdatedAt(null), "date not recorded");
  assert.equal(formatProfileUpdatedAt("not a date"), "date not recorded");
});

test("unknown and not-applicable values never display as zero", () => {
  assert.equal(formatProfileMetric({ field_id: "team_size", value: 0, unit: "people", provenance: "unknown" }), "Unknown");
  assert.equal(formatProfileMetric({ field_id: "team_size", provenance: "not_applicable" }), "Not applicable");
});

test("legacy team-size notes are suppressed when identical and retained when they conflict", () => {
  assert.equal(shouldDisplayLegacyTeamSize(3, { value: 3 }), false);
  assert.equal(shouldDisplayLegacyTeamSize(3, { value: 4 }), true);
  assert.equal(shouldDisplayLegacyTeamSize(3, { provenance: "unknown" }), true);
  assert.equal(shouldDisplayLegacyTeamSize(3, null), true);
});

test("revenue model is shown once unless structured and legacy notes differ", () => {
  assert.equal(shouldDisplayStructuredRevenueModel("Subscription", "Subscription"), false);
  assert.equal(shouldDisplayStructuredRevenueModel("Subscription", "Usage based"), true);
  assert.equal(shouldDisplayStructuredRevenueModel(undefined, "Subscription"), true);
});
