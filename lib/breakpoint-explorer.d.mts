import type { DiagnosticFinding } from "./types";

export function breakpointDomainLabel(category: string | null | undefined): string;
export function breakpointStatusLabel(status: DiagnosticFinding["status"] | string): string;
export function breakpointVisualSeverity(finding: Pick<DiagnosticFinding, "status" | "severity_if_true"> | null | undefined): "Critical" | "Major" | "Moderate" | "Minor" | "unrated";
export function breakpointVisualState(finding: Pick<DiagnosticFinding, "status" | "severity_if_true"> | null | undefined): "severity" | "measured" | "estimated" | "hypothesis" | "conflicted" | "information" | "neutral";
export function groupBreakpoints(findings: DiagnosticFinding[] | null | undefined): Array<{
  id: string;
  label: string;
  findings: DiagnosticFinding[];
}>;
export function initialBreakpointId(findings: DiagnosticFinding[] | null | undefined): string | null;
