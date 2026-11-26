const PROVENANCE_LABELS = {
  measured: "Measured",
  estimated: "Estimated",
  assumed: "Assumed",
  unknown: "Unknown",
  not_applicable: "Not applicable",
};

function number(value) {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : null;
}

export function formatProfileMetric(metric) {
  if (metric.provenance === "unknown" || metric.provenance === "not_applicable") {
    return PROVENANCE_LABELS[metric.provenance];
  }

  const value = number(metric.value);
  const lower = number(metric.range_low);
  const upper = number(metric.range_high);
  const range = lower !== null && upper !== null
    ? `${lower}–${upper}`
    : lower !== null ? `at least ${lower}`
      : upper !== null ? `up to ${upper}` : null;
  const amount = value !== null
    ? range ? `${value} (range ${range})` : value
    : range ?? "Value not recorded";

  let unit = typeof metric.unit === "string" ? metric.unit.trim() : "";
  const currency = typeof metric.currency === "string" ? metric.currency.trim() : "";
  let parts;
  if (unit === "currency") {
    parts = [amount, currency];
  } else if (unit.startsWith("currency/")) {
    const suffix = unit.slice("currency/".length);
    parts = [amount, currency, `/ ${suffix}`];
    unit = suffix;
  } else {
    parts = [amount, unit, currency];
  }

  if (metric.period && metric.period !== unit) parts.push(`/ ${metric.period}`);
  parts.push(PROVENANCE_LABELS[metric.provenance] ?? "Provenance not recorded");
  return parts.filter(Boolean).join(" ");
}

export function formatProfileUpdatedAt(value) {
  if (typeof value !== "string" || !value.trim()) return "date not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "date not recorded";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  }).format(date);
}

export function shouldDisplayLegacyTeamSize(legacyValue, structuredMetric) {
  if (!structuredMetric) return true;
  if (legacyValue === undefined || legacyValue === null) return false;
  return typeof structuredMetric.value !== "number" || structuredMetric.value !== legacyValue;
}

export function shouldDisplayStructuredRevenueModel(legacyValue, structuredValue) {
  if (typeof structuredValue !== "string" || !structuredValue.trim()) return false;
  return typeof legacyValue !== "string" || structuredValue.trim() !== legacyValue.trim();
}
