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
  profile?: StartupProfile;
};

export type ProfileStage = "idea_concept" | "validation_customer_discovery" | "mvp_product_development" | "pre_revenue" | "early_revenue" | "early_growth" | "scaling" | "mature_established" | "not_sure_yet";
export type BusinessModelType = "b2b_saas" | "b2c_saas" | "marketplace" | "dtc_ecommerce" | "hardware" | "fintech" | "biotech_medtech" | "services_consulting" | "consumer_application" | "platform_developer_tools" | "other" | "not_yet_determined";
export type Provenance = "measured" | "estimated" | "assumed" | "unknown" | "not_applicable";
export type ProfileMetric = {
  field_id: string; value?: number | null; unit?: string | null; currency?: string | null;
  provenance: Provenance; measurement_date?: string | null;
  period?: "day" | "week" | "month" | "quarter" | "year" | "lifetime" | "custom" | "point_in_time" | null;
  period_start?: string | null; period_end?: string | null; source_reference?: string | null;
  range_low?: number | null; range_high?: number | null; confirmed_by_user: boolean;
  applicability: "applicable" | "unknown" | "not_applicable";
};
export type StartupProfile = {
  profile_schema_version: 1; last_updated_at: string;
  identity?: { business_model?: BusinessModelType | null; stage?: ProfileStage | null; problem?: string | null; proposed_solution?: string | null; operating_geography?: string | null; target_market_geography?: string | null } | null;
  customer_market?: { customer_type?: "b2b" | "b2c" | "b2b2c" | "other" | "not_sure_yet" | null; customer_segment?: string | null; customer_description?: string | null; discovery_evidence?: string | null; willingness_to_pay_evidence?: string | null; existing_alternatives?: string | null; market_size_assumption?: string | null; metrics?: ProfileMetric[] } | null;
  product_traction?: { product_status?: "concept" | "prototype" | "mvp" | "beta" | "launched" | "not_sure_yet" | null; customer_validation?: string | null; acquisition_channel?: string | null; metrics?: ProfileMetric[] } | null;
  economics?: { revenue_model?: string | null; pricing_model?: string | null; acquisition_channel?: string | null; metrics?: ProfileMetric[] } | null;
  finance?: { funding_status?: string | null; funding_sources?: string | null; upcoming_milestones?: string | null; metrics?: ProfileMetric[] } | null;
  team_operations?: { team_capabilities?: string | null; capability_gaps?: string | null; critical_dependencies?: string | null; suppliers_or_distribution?: string | null; technology_constraints?: string | null; regulatory_context?: string | null; metrics?: ProfileMetric[] } | null;
  business_model_details?: ({ kind: "b2b_saas"; sales_cycle_notes?: string | null; renewal_notes?: string | null } | { kind: "marketplace"; buyer_group?: string | null; seller_group?: string | null; liquidity_notes?: string | null; metrics?: ProfileMetric[] } | { kind: "dtc_ecommerce"; fulfilment_notes?: string | null; metrics?: ProfileMetric[] } | { kind: "hardware"; manufacturing_readiness?: string | null; tooling_and_production?: string | null; supply_chain_dependencies?: string | null; metrics?: ProfileMetric[] } | { kind: "fintech"; product_category?: string | null; regulatory_jurisdiction?: string | null; licensing_status?: string | null; infrastructure_dependencies?: string | null } | { kind: "biotech_medtech"; development_or_validation_stage?: string | null; regulatory_pathway?: string | null; capital_and_development_milestones?: string | null } | { kind: "services_consulting"; service_type?: string | null; delivery_capacity_notes?: string | null; metrics?: ProfileMetric[] }) | null;
};

export type PredictionResult = {
  stage: "stage1" | "stage2";
  inference_status?: "legacy_descriptive_only";
  model_version?: string;
  feature_schema_version?: string;
  prediction_horizon?: null;
  output_semantics?: "historical_terminal_outcome_association";
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

export type DiagnosticStatus = "CONFIRMED" | "INDICATED" | "HYPOTHESIS" | "NOT_TRIGGERED" | "INSUFFICIENT_INFORMATION" | "CONFLICTED" | "NOT_APPLICABLE";
export type DiagnosticFinding = {
  finding_id: string;
  diagnostic_id: string;
  title: string;
  category: string;
  description: string;
  mechanism: string;
  startup_stage: string | null;
  business_model: string | null;
  applicability: "applicable" | "unknown" | "not_applicable";
  status: DiagnosticStatus;
  severity_if_true: "Critical" | "Major" | "Moderate" | "Minor" | null;
  evidence_strength: "High" | "Moderate" | "Low" | "Insufficient";
  supporting_inputs: { field: string; value: unknown; provenance?: string }[];
  missing_inputs: string[];
  assumptions: string[];
  formula_or_rule: string;
  calculated_values: Record<string, number | string | boolean | null>;
  explanation: string;
  limitations: string[];
  related_findings: string[];
  relationship_type: "INDEPENDENT" | "SUPPORTING" | "DERIVED" | "OVERLAPPING" | "CONTRADICTORY";
  evidence_references: string[];
  suggested_validation: string | null;
  suggested_next_actions: string[];
  diagnostic_version: string;
  evaluated_at: string;
};
export type DiagnosticReport = {
  engine_version: string;
  profile_schema_version: number | null;
  profile_available: boolean;
  evaluated_at: string;
  findings: DiagnosticFinding[];
  limitations: string[];
};
export type DiagnosticsState = "available" | "no_profile" | "unavailable";

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
  diagnostics?: DiagnosticReport | null;
  diagnostics_state?: DiagnosticsState | null;
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
  match_category?: "direct_business_model" | "industry_adjacent" | "mechanism_based" | "contextual";
  shared_characteristics?: string[];
  important_differences?: string[];
  outcome_status?: string;
  historical_outcome?: string;
  documented_lesson?: string;
  comparison_limitations?: string[];
};

export type CasesResponse = { matched: boolean; cases: FailureCase[]; note: string; library_status?: "available" | "limited" | "unavailable"; library_count?: number };

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
  openalex_id?: string | null;
  publication_type?: string;
  metadata_status?: string;
  access_status?: "abstract_only" | "metadata_only" | "full_text_reviewed";
  open_access_url?: string | null;
  retrieved_at?: string;
  relevance_dimensions?: string[];
  source_type?: string;
};

export type EvidenceResponse = {
  provider: string; node: string; sources: EvidenceSource[]; note: string;
  state?: "relevant_results" | "partial" | "no_results" | "filtered_out" | "weak_relevance" | "provider_unavailable" | "provider_timeout" | "rate_limited" | "provider_error" | "insufficient_query_context";
  queries_attempted?: number; query_results?: { query_index: number; page?: number; state: string; records: number; accepted: number }[];
  records_retrieved?: number; candidates_filtered?: number; retrieved_at?: string;
  weak_candidates?: number;
  snapshot_id?: string | null;
  snapshot_saved?: boolean;
  snapshot_persistence_note?: string;
};

export type EvidenceSnapshotSummary = {
  id: string;
  retrieved_at: string;
  created_at: string;
  state: string;
};

export type EvidenceAssociation = {
  contract_version: "1.0";
  record_id: string;
  analysis_id: string;
  snapshot_id: string;
  claim_text: string;
  claim_category: "historical_case_fact" | "general_research_finding" | "startup_specific_interpretation" | "recommendation";
  source_id: string;
  source_access: "abstract_excerpt" | "full_text_passage" | "metadata_only" | "inaccessible";
  exact_passage_text: string | null;
  passage_location: string | null;
  source_url: string;
  publication: { title: string; url: string; publisher?: string | null; journal?: string | null; authors: string[]; doi?: string | null; published?: string | null; year?: string | null };
  relationship: "supports" | "partially_supports" | "contextualizes" | "contradicts" | "insufficient";
  verification_state: "pending_review" | "verified" | "rejected" | "not_assessed";
  verification_method: "human_review" | "ai_assisted" | "system_validation" | "none";
  reviewer_id?: string | null;
  supersedes_record_id?: string | null;
  limitations: string[];
  created_at: string;
  retrieved_at?: string | null;
  reviewed_at?: string | null;
  verified_at?: string | null;
  is_current?: boolean;
};

export type ContradictionAssessment = {
  contract_version: "1.0";
  record_id: string;
  analysis_id: string;
  association_ids: [string, string];
  compared_evidence: { association_id: string; snapshot_id: string; source_id: string; claim_text: string; exact_passage_text: string; passage_location?: string | null; source_access: "abstract_excerpt" | "full_text_passage"; source_url: string; publication: EvidenceAssociation["publication"] }[];
  nature: "genuine_disagreement" | "different_population" | "different_geography" | "different_period" | "different_definition" | "different_methodology" | "complementary" | "insufficient_information";
  assessment_text: string;
  relationship?: "supports" | "partially_supports" | "contextualizes" | "contradicts" | "insufficient";
  context_differences?: string[];
  methodological_differences?: string[];
  measurement_differences?: string[];
  population_differences?: string[];
  geographic_differences?: string[];
  time_period_differences?: string[];
  uncertainty_explanation?: string;
  source_access_limitations?: string[];
  detection_method?: "deterministic_excerpt_rules" | "manual_review";
  reviewer_explanation?: string | null;
  verification_state: "pending_review" | "verified" | "rejected" | "not_assessed";
  verification_method: "human_review" | "ai_assisted" | "system_validation" | "none";
  reviewer_id?: string | null;
  limitations: string[];
  supersedes_record_id?: string | null;
  created_at: string;
  reviewed_at?: string | null;
  linked_evidence?: EvidenceAssociation[];
  is_current?: boolean;
};
