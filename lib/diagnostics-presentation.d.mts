import type { DiagnosticFinding } from "./types";

export function resolveDiagnosticViewState(state: "available" | "no_profile" | "unavailable" | null | undefined, report?: { profile_available?: boolean } | null): "available" | "no_profile" | "unavailable";
export function groupDiagnosticFindings(findings: DiagnosticFinding[]): {
  supported: DiagnosticFinding[];
  hypotheses: DiagnosticFinding[];
  conflicts: DiagnosticFinding[];
  informationGaps: DiagnosticFinding[];
  otherChecks: DiagnosticFinding[];
};
export function formatDiagnosticInput(input: { field: string; value: unknown; provenance?: string }): {
  label: string; value: string; provenance?: string;
};
export function formatDiagnosticCalculatedValue(name: string, value: unknown, calculatedValues?: Record<string, unknown>): string;
export function diagnosticEvidenceLabels(finding: Pick<DiagnosticFinding, "status" | "evidence_strength" | "severity_if_true">): {
  status: DiagnosticFinding["status"];
  evidenceStrength: DiagnosticFinding["evidence_strength"];
  severity: NonNullable<DiagnosticFinding["severity_if_true"]> | "Severity not assigned";
};
