const DOMAIN_LABELS = {
  market_customer_validation: "Customer and market",
  unit_economics: "Unit economics",
  retention_traction: "Retention and traction",
  funding_runway: "Cash and runway",
  marketplace: "Marketplace liquidity",
  hardware_deep_tech: "Production readiness",
  team_execution: "Team execution",
  regulatory_operations: "Operations and regulation",
};

const STATUS_LABELS = {
  CONFIRMED: "Measured input",
  INDICATED: "Estimated input",
  HYPOTHESIS: "Assumption to validate",
  CONFLICTED: "Conflicting inputs",
  INSUFFICIENT_INFORMATION: "Information needed",
  NOT_TRIGGERED: "Rule not triggered",
  NOT_APPLICABLE: "Not applicable",
};

const ACTIONABLE = new Set(["CONFIRMED", "INDICATED", "HYPOTHESIS", "CONFLICTED"]);
const NEUTRAL_VISUAL_STATES = new Set(["INSUFFICIENT_INFORMATION", "NOT_TRIGGERED", "NOT_APPLICABLE"]);

export function breakpointDomainLabel(category) {
  if (typeof category !== "string" || !category) return "Other checks";
  return DOMAIN_LABELS[category] ?? category.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function breakpointStatusLabel(status) {
  return STATUS_LABELS[status] ?? "Status unavailable";
}

export function breakpointVisualSeverity(finding) {
  if (!finding || NEUTRAL_VISUAL_STATES.has(finding.status)) return "unrated";
  return ["Critical", "Major", "Moderate", "Minor"].includes(finding.severity_if_true) ? finding.severity_if_true : "unrated";
}

/** A visual cue for evidence state when no reviewed if-true severity is available. */
export function breakpointVisualState(finding) {
  if (!finding) return "neutral";
  if (breakpointVisualSeverity(finding) !== "unrated") return "severity";
  switch (finding.status) {
    case "CONFIRMED": return "measured";
    case "INDICATED": return "estimated";
    case "HYPOTHESIS": return "hypothesis";
    case "CONFLICTED": return "conflicted";
    case "INSUFFICIENT_INFORMATION": return "information";
    case "NOT_TRIGGERED":
    case "NOT_APPLICABLE":
    default: return "neutral";
  }
}

export function groupBreakpoints(findings) {
  const groups = new Map();
  for (const finding of Array.isArray(findings) ? findings : []) {
    const key = typeof finding?.category === "string" && finding.category ? finding.category : "other_checks";
    if (!groups.has(key)) groups.set(key, { id: key, label: breakpointDomainLabel(key), findings: [] });
    groups.get(key).findings.push(finding);
  }
  return [...groups.values()];
}

export function initialBreakpointId(findings) {
  if (!Array.isArray(findings) || findings.length === 0) return null;
  return findings.find((finding) => ACTIONABLE.has(finding?.status))?.finding_id ?? findings[0]?.finding_id ?? null;
}
