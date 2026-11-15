// Mirrors backend/app/schemas.py. Saved analyses are snapshots, so older ones may lack newer fields (marked optional).
export type Band = "Low" | "Medium" | "High" | "Critical";

export type Factor = {
  feature: string;
  label: string;
  value: string | number;
  contribution?: number;
  effect: "raises risk" | "lowers risk";
  impact: number;
};

export type Branch = {
  group: string;
  label: string;
  band: Band | null;
  effect: "raises" | "lowers" | "neutral";
  net_shap: number;
  factors: Factor[];
};

export type CohortSlice = {
  key: string;
  label: string;
  detail: string;
  n: number;
  enough: boolean; // false when there are too few startups to show a percentage
  closed_share: number | null;
  low: number | null;
  high: number | null;
};

export type Cohort = {
  basis: string;
  overall: { n: number; closed_share: number };
  slices: CohortSlice[];
  note: string;
};

/** What the founder wrote. Saved for context only: the risk models never see it. */
export type Context = {
  concept?: string;
  vision?: string;
  customer?: string;
  revenue_model?: string;
  startup_stage?: "idea" | "prototype" | "launched" | "earning";
  team_size?: number;
  biggest_worry?: string;
};

export type PredictionResult = {
  stage: "stage1" | "stage2";
  probability: number;
  band: Band;
  similar_startups_failure_rate: number;
  confidence: "limited" | "moderate" | "low" | null;
  benchmark?: string;
  cohort?: Cohort | null; // Stage 1 only, and missing on analyses saved before it existed
  tree: { label: string; band: Band; probability: number; children: Branch[] };
  notes: string[];
  limitations: string[];
  disclaimer: string;
};

export type Analysis = {
  id: string;
  stage: "stage1" | "stage2";
  title: string;
  band: Band;
  probability: number;
  parent_id: string | null;
  created_at: string;
  input: Record<string, unknown>;
  result: PredictionResult;
  context?: Context | null; // missing on analyses saved before the new questions existed
};

export type Meta = {
  stages: { stage1: { inputs: { countries: string[]; states: string[]; tags: string[] } } };
};

/** One row of the dashboard list. The full analysis (with result and notes) is fetched when you open it. */
export type AnalysisSummary = {
  id: string;
  stage: "stage1" | "stage2";
  title: string;
  band: Band;
  probability: number;
  parent_id: string | null;
  created_at: string;
};

export type CaseSource = { title: string; publisher: string; url: string; published: string; kind: string };

/** A real startup that failed and resembles the idea, summarised from the linked sources. */
export type FailureCase = {
  id: string;
  name: string;
  years: string;
  sector: string;
  what: string;
  how_it_failed: string;
  reasons: string[];
  sources: CaseSource[];
  verified_on: string;
  matched_on: string[];
};

export type CasesResponse = { matched: boolean; cases: FailureCase[]; note: string };

export type EvidenceSource = {
  title: string;
  publisher: string;
  journal?: string;
  authors?: string[];
  doi?: string | null;
  url: string;
  published: string;
  year?: string;
  venue_status: string;
  excerpt: string;
  matched_terms: string[];
  relation?: "direct" | "contextual";
  focus?: string;
};

export type EvidenceResponse = { provider: string; node: string; sources: EvidenceSource[]; note: string };
