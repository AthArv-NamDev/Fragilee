export type ProfileMetricPresentation = {
  value?: number | null;
  range_low?: number | null;
  range_high?: number | null;
  unit?: string | null;
  currency?: string | null;
  period?: string | null;
  provenance: string;
};

export function formatProfileMetric(metric: ProfileMetricPresentation): string;
export function formatProfileUpdatedAt(value: unknown): string;
export function shouldDisplayLegacyTeamSize(legacyValue: number | null | undefined, structuredMetric?: { value?: number | null } | null): boolean;
export function shouldDisplayStructuredRevenueModel(legacyValue: string | null | undefined, structuredValue: string | null | undefined): boolean;
