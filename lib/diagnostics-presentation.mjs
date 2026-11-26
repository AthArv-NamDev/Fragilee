import { formatProfileMetric } from "./profile-presentation.mjs";

const STATUS_GROUPS = {
  supported: new Set(["CONFIRMED", "INDICATED"]),
  hypotheses: new Set(["HYPOTHESIS"]),
  conflicts: new Set(["CONFLICTED"]),
  informationGaps: new Set(["INSUFFICIENT_INFORMATION"]),
  otherChecks: new Set(["NOT_TRIGGERED", "NOT_APPLICABLE"]),
};

export function resolveDiagnosticViewState(state, report) {
  if (state === "unavailable" || !state || (state === "available" && !report)) return "unavailable";
  if (state === "no_profile" || report?.profile_available === false) return "no_profile";
  return "available";
}

export function groupDiagnosticFindings(findings) {
  const groups = { supported: [], hypotheses: [], conflicts: [], informationGaps: [], otherChecks: [] };
  for (const finding of Array.isArray(findings) ? findings : []) {
    for (const [group, statuses] of Object.entries(STATUS_GROUPS)) {
      if (statuses.has(finding.status)) {
        groups[group].push(finding);
        break;
      }
    }
  }
  return groups;
}

export function formatDiagnosticInput(input) {
  const value = input?.value;
  if (value && typeof value === "object" && typeof value.field_id === "string") {
    return {
      label: value.field_id.replaceAll("_", " "),
      value: formatProfileMetric(value),
      provenance: value.provenance,
    };
  }
  const leaf = typeof input?.field === "string" ? input.field.split(".").at(-1) : "Founder input";
  const label = leaf.replaceAll("_", " ");
  const formatted = typeof value === "string" || typeof value === "number" || typeof value === "boolean"
    ? String(value)
    : value == null ? "Not provided" : "Input recorded";
  return { label, value: formatted, provenance: input?.provenance };
}

export function formatDiagnosticCalculatedValue(name, value, calculatedValues = {}) {
  if (value == null) return "Not calculated";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value !== "number" || !Number.isFinite(value)) return String(value);
  const number = new Intl.NumberFormat("en", { maximumFractionDigits: 2 }).format(value);
  if (name.includes("ratio")) return number;
  const currency = typeof calculatedValues.currency === "string" ? calculatedValues.currency : "";
  const unit = typeof calculatedValues.unit === "string" ? calculatedValues.unit : "";
  if (currency && unit.startsWith("currency/")) return `${currency} ${number} / ${unit.slice("currency/".length)}`;
  if (currency && unit === "currency") return `${currency} ${number}`;
  return [number, unit].filter(Boolean).join(" ");
}

export function diagnosticEvidenceLabels(finding) {
  return {
    status: finding.status,
    evidenceStrength: finding.evidence_strength,
    severity: finding.severity_if_true ?? "Severity not assigned",
  };
}
