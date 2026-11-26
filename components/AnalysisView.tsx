"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import type { Analysis, CasesResponse, Context, ProfileMetric, StartupProfile } from "@/lib/types";
import { COUNTRY_NAMES, STATE_NAMES } from "@/lib/geo";
import { formatProfileMetric, formatProfileUpdatedAt, shouldDisplayLegacyTeamSize, shouldDisplayStructuredRevenueModel } from "@/lib/profile-presentation.mjs";
import PlexTree from "./tree/PlexTree";
import CasesPanel from "./CasesPanel";

const STAGE_LABEL: Record<NonNullable<Context["startup_stage"]>, string> = { idea: "Idea", prototype: "Prototype", launched: "Launched", earning: "Earning money" };
const CONTEXT_FIELDS: [keyof Context, string][] = [
  ["concept", "What it does"], ["vision", "Vision"], ["customer", "Target customer"],
  ["revenue_model", "Revenue model (founder note)"], ["startup_stage", "Current stage"], ["team_size", "Team size"],
  ["biggest_worry", "Biggest worry"],
];

function founderValue(field: keyof Context, value: Context[keyof Context] | undefined) {
  if (value === undefined || value === null || value === "") return "Not provided";
  if (field === "startup_stage") return STAGE_LABEL[value as NonNullable<Context["startup_stage"]>] ?? String(value);
  return String(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isOptionalStringFields(value: unknown, fields: string[]): boolean {
  if (value == null) return true;
  return isRecord(value) && fields.every((field) => value[field] == null || typeof value[field] === "string");
}

function isProfileMetric(value: unknown): value is ProfileMetric {
  if (!isRecord(value)) return false;
  const optionalStrings = ["unit", "currency", "measurement_date", "period", "period_start", "period_end", "source_reference"];
  const optionalNumbers = ["value", "range_low", "range_high"];
  return typeof value.field_id === "string"
    && ["measured", "estimated", "assumed", "unknown", "not_applicable"].includes(String(value.provenance))
    && ["applicable", "unknown", "not_applicable"].includes(String(value.applicability))
    && typeof value.confirmed_by_user === "boolean"
    && optionalStrings.every((field) => value[field] == null || typeof value[field] === "string")
    && optionalNumbers.every((field) => value[field] == null || (typeof value[field] === "number" && Number.isFinite(value[field])))
    && ["field_id", "provenance", "applicability", "confirmed_by_user"].every((field) => field in value);
}

function isMetricGroup(value: unknown, fields: string[]): boolean {
  if (value == null) return true;
  if (!isRecord(value) || !isOptionalStringFields(value, fields)) return false;
  return value.metrics == null || (Array.isArray(value.metrics) && value.metrics.every(isProfileMetric));
}

function isDisplayableProfile(value: unknown): value is StartupProfile {
  if (!isRecord(value) || value.profile_schema_version !== 1 || typeof value.last_updated_at !== "string") return false;
  const identityFields = ["business_model", "stage", "problem", "proposed_solution", "operating_geography", "target_market_geography"];
  if (!isOptionalStringFields(value.identity, identityFields)) return false;
  if (!isMetricGroup(value.customer_market, ["customer_type", "customer_segment", "customer_description", "discovery_evidence", "willingness_to_pay_evidence", "existing_alternatives", "market_size_assumption"])) return false;
  if (!isMetricGroup(value.product_traction, ["product_status", "customer_validation", "acquisition_channel"])) return false;
  if (!isMetricGroup(value.economics, ["revenue_model", "pricing_model", "acquisition_channel"])) return false;
  if (!isMetricGroup(value.finance, ["funding_status", "funding_sources", "upcoming_milestones"])) return false;
  if (!isMetricGroup(value.team_operations, ["team_capabilities", "capability_gaps", "critical_dependencies", "suppliers_or_distribution", "technology_constraints", "regulatory_context"])) return false;
  const details = value.business_model_details;
  if (details == null) return true;
  if (!isRecord(details) || typeof details.kind !== "string") return false;
  return isMetricGroup(details, ["buyer_group", "seller_group", "liquidity_notes", "fulfilment_notes", "manufacturing_readiness", "tooling_and_production", "supply_chain_dependencies", "sales_cycle_notes", "renewal_notes", "product_category", "regulatory_jurisdiction", "licensing_status", "infrastructure_dependencies", "development_or_validation_stage", "regulatory_pathway", "capital_and_development_milestones", "service_type", "delivery_capacity_notes"]);
}

function ProfileSection({ profile, legacyRevenueModel }: { profile: NonNullable<Context["profile"]>; legacyRevenueModel?: string }) {
  const rows: [string, string][] = [];
  const identity = profile.identity;
  if (identity?.business_model) rows.push(["Business model", identity.business_model.replaceAll("_", " ")]);
  if (identity?.stage) rows.push(["Structured stage", identity.stage.replaceAll("_", " ")]);
  if (identity?.problem) rows.push(["Problem", identity.problem]);
  if (identity?.proposed_solution) rows.push(["Proposed solution", identity.proposed_solution]);
  if (identity?.operating_geography) rows.push(["Operating geography", identity.operating_geography]);
  if (identity?.target_market_geography) rows.push(["Target geography", identity.target_market_geography]);
  if (profile.customer_market?.customer_type) rows.push(["Customer type", profile.customer_market.customer_type.toUpperCase()]);
  if (profile.customer_market?.customer_segment) rows.push(["Customer segment", profile.customer_market.customer_segment]);
  if (profile.customer_market?.customer_description) rows.push(["Customer description", profile.customer_market.customer_description]);
  if (profile.product_traction?.product_status) rows.push(["Product status", profile.product_traction.product_status.replaceAll("_", " ")]);
  if (profile.customer_market?.discovery_evidence) rows.push(["Customer discovery evidence", profile.customer_market.discovery_evidence]);
  if (profile.customer_market?.willingness_to_pay_evidence) rows.push(["Willingness-to-pay evidence", profile.customer_market.willingness_to_pay_evidence]);
  if (profile.customer_market?.existing_alternatives) rows.push(["Existing alternatives", profile.customer_market.existing_alternatives]);
  if (profile.customer_market?.market_size_assumption) rows.push(["Market-size assumption", profile.customer_market.market_size_assumption]);
  if (profile.product_traction?.customer_validation) rows.push(["Customer validation", profile.product_traction.customer_validation]);
  if (profile.product_traction?.acquisition_channel) rows.push(["Acquisition channel", profile.product_traction.acquisition_channel]);
  if (shouldDisplayStructuredRevenueModel(legacyRevenueModel, profile.economics?.revenue_model)) rows.push(["Structured revenue model", profile.economics!.revenue_model!]);
  if (profile.economics?.pricing_model) rows.push(["Pricing model", profile.economics.pricing_model]);
  if (profile.finance?.funding_status) rows.push(["Funding status", profile.finance.funding_status.replaceAll("_", " ")]);
  if (profile.finance?.funding_sources) rows.push(["Funding sources", profile.finance.funding_sources]);
  if (profile.finance?.upcoming_milestones) rows.push(["Upcoming milestones", profile.finance.upcoming_milestones]);
  if (profile.team_operations?.team_capabilities) rows.push(["Team capabilities", profile.team_operations.team_capabilities]);
  if (profile.team_operations?.capability_gaps) rows.push(["Capability gaps", profile.team_operations.capability_gaps]);
  if (profile.team_operations?.critical_dependencies) rows.push(["Critical dependencies", profile.team_operations.critical_dependencies]);
  if (profile.team_operations?.suppliers_or_distribution) rows.push(["Suppliers or distribution", profile.team_operations.suppliers_or_distribution]);
  if (profile.team_operations?.technology_constraints) rows.push(["Technology constraints", profile.team_operations.technology_constraints]);
  if (profile.team_operations?.regulatory_context) rows.push(["Regulatory context", profile.team_operations.regulatory_context]);
  const detail = profile.business_model_details;
  if (detail && "sales_cycle_notes" in detail && detail.sales_cycle_notes) rows.push(["Sales cycle context", detail.sales_cycle_notes]);
  if (detail && "liquidity_notes" in detail && detail.liquidity_notes) rows.push(["Marketplace liquidity context", detail.liquidity_notes]);
  if (detail && "fulfilment_notes" in detail && detail.fulfilment_notes) rows.push(["Fulfilment context", detail.fulfilment_notes]);
  if (detail && "tooling_and_production" in detail && detail.tooling_and_production) rows.push(["Tooling and production", detail.tooling_and_production]);
  if (detail && "infrastructure_dependencies" in detail && detail.infrastructure_dependencies) rows.push(["Financial infrastructure dependencies", detail.infrastructure_dependencies]);
  if (detail && "regulatory_pathway" in detail && detail.regulatory_pathway) rows.push(["Regulatory pathway", detail.regulatory_pathway]);
  if (detail && "delivery_capacity_notes" in detail && detail.delivery_capacity_notes) rows.push(["Delivery capacity", detail.delivery_capacity_notes]);
  const metricGroups = [profile.customer_market?.metrics, profile.product_traction?.metrics, profile.economics?.metrics, profile.finance?.metrics, profile.team_operations?.metrics, profile.business_model_details && "metrics" in profile.business_model_details ? profile.business_model_details.metrics : undefined];
  const metricLabels: Record<string, string> = { team_size: "Team size", revenue_amount: "Monthly revenue", paying_customers: "Paying customers", active_users: "Active users", retention_rate: "Retention rate", churn_rate: "Churn rate", cash_balance: "Cash balance", monthly_operating_expense: "Monthly operating expense", runway: "Runway" };
  metricGroups.flatMap((group) => group ?? []).forEach((metric) => {
    const value = formatProfileMetric(metric);
    rows.push([metricLabels[metric.field_id] ?? metric.field_id.replaceAll("_", " "), `${value}${metric.source_reference ? ` · Source: ${metric.source_reference}` : ""}`]);
  });
  if (!rows.length) return null;
  return <div className="mt-5 rounded-2xl border border-ink/10 p-4">
    <h3 className="font-semibold">Structured profile <span className="text-xs font-normal text-muted">Schema v{profile.profile_schema_version}</span></h3>
    <p className="mt-1 text-xs text-muted">Founder-supplied snapshot, updated {formatProfileUpdatedAt(profile.last_updated_at)}. Provenance describes how each value was supplied; it does not independently verify it.</p>
    <dl className="mt-3 grid gap-x-6 divide-y divide-ink/10 text-sm md:grid-cols-[minmax(150px,.35fr)_1fr]">{rows.map(([label, value], i) => <div key={`${label}-${i}`} className="contents"><dt className="py-2 text-muted">{label}</dt><dd className="whitespace-pre-line break-words py-2">{value}</dd></div>)}</dl>
  </div>;
}

function Overview({ analysis }: { analysis: Analysis }) {
  const input = analysis.input ?? {};
  const tags = Array.isArray(input.tags) ? input.tags.filter((tag): tag is string => typeof tag === "string" && !!tag.trim()) : [];
  const countryCode = typeof input.country === "string" ? input.country : "";
  const stateCode = typeof input.state === "string" ? input.state : "";
  const country = countryCode ? COUNTRY_NAMES[countryCode] ?? countryCode : "Not provided";
  const place = [country, stateCode && stateCode !== "NONE" ? STATE_NAMES[stateCode] ?? stateCode : ""].filter(Boolean).join(" · ") || "Not provided";
  const context = analysis.context ?? {};
  const date = new Date(analysis.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

  return <section className="rounded-[28px] border border-ink/10 bg-dark-surface p-6 surface-lift md:p-10" aria-labelledby="startup-overview-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="eyebrow text-coral">Fragilee / startup overview</p>
        <p className="text-xs text-muted"><span className="sr-only">Analysis date: </span>{date}</p>
      </div>
      <h1 id="startup-overview-title" className="editorial-title mt-4 max-w-4xl break-words font-display">{analysis.title}<span className="text-coral">.</span></h1>
      <p className="mt-5 text-sm text-muted">Submitted location: <span className="text-text">{place}</span></p>
      <div className="mt-3 flex flex-wrap gap-2" aria-label="Submitted industries">
        {tags.length ? tags.map((tag) => <span key={tag} className="rounded-full border border-ink/15 px-3 py-1.5 text-xs text-text">{tag}</span>) : <span className="text-sm text-muted">Industry: Not provided</span>}
      </div>
      {context.concept && <p className="mt-6 max-w-3xl whitespace-pre-line break-words text-base leading-relaxed">{context.concept}</p>}
      <Link href="#evidence-examples" className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-full bg-sage px-6 text-sm font-semibold button-label-on-sage transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral">Review research and historical examples <span aria-hidden="true">↓</span></Link>
    </section>;
}

function FounderInformation({ analysis }: { analysis: Analysis }) {
  const context = analysis.context ?? {};
  const countryCode = typeof analysis.input?.country === "string" ? analysis.input.country : "";
  const stateCode = typeof analysis.input?.state === "string" ? analysis.input.state : "";
  const country = countryCode ? COUNTRY_NAMES[countryCode] ?? countryCode : "Not provided";
  const place = [country, stateCode && stateCode !== "NONE" ? STATE_NAMES[stateCode] ?? stateCode : ""].filter(Boolean).join(" · ") || "Not provided";
  const tags = Array.isArray(analysis.input?.tags) ? analysis.input.tags.filter((tag): tag is string => typeof tag === "string" && !!tag.trim()) : [];
  const displayProfile = isDisplayableProfile(context.profile) ? context.profile : null;
  const profileMetrics = displayProfile ? [displayProfile.customer_market?.metrics, displayProfile.product_traction?.metrics, displayProfile.economics?.metrics, displayProfile.finance?.metrics, displayProfile.team_operations?.metrics, displayProfile.business_model_details && "metrics" in displayProfile.business_model_details ? displayProfile.business_model_details.metrics : undefined].flatMap((group) => group ?? []) : [];
  const structuredTeamSize = profileMetrics.find((metric) => metric.field_id === "team_size");
  const hasContext = CONTEXT_FIELDS.some(([field]) => context[field] !== undefined && context[field] !== null && context[field] !== "");

  return <section className="mt-6 rounded-[24px] border border-ink/10 bg-dark-surface p-5 md:p-7" aria-labelledby="provided-info-title">
      <p className="eyebrow text-coral">Founder-submitted information</p>
      <h2 id="provided-info-title" className="mt-2 font-display text-2xl">What you shared</h2>
      <p className="mt-2 max-w-3xl text-sm text-muted">These are the values saved with this analysis. Free-text answers are founder-provided and have not been independently verified. “Not provided” means information is unavailable here; it is not a risk signal.</p>
      <dl className="mt-5 grid gap-x-8 divide-y divide-ink/10 border-y border-ink/10 text-sm md:grid-cols-[minmax(150px,.35fr)_1fr]">
        <div className="contents"><dt className="py-3 text-muted">Location used for model input</dt><dd className="break-words py-3">{place}</dd></div>
        <div className="contents"><dt className="py-3 text-muted">Industry tags used for model input</dt><dd className="break-words py-3">{tags.length ? tags.join(", ") : "Not provided"}</dd></div>
        {CONTEXT_FIELDS.filter(([field]) => field !== "team_size" || shouldDisplayLegacyTeamSize(context.team_size, structuredTeamSize)).map(([field, label]) => <div key={field} className="contents"><dt className="py-3 text-muted">{field === "team_size" && structuredTeamSize ? "Team size (legacy founder note)" : label}</dt><dd className="whitespace-pre-line break-words py-3">{founderValue(field, context[field])}</dd></div>)}
      </dl>
      {!hasContext && !displayProfile && <p className="mt-3 text-xs text-muted">This saved analysis has no additional founder notes or structured profile.</p>}
      {displayProfile && <ProfileSection profile={displayProfile} legacyRevenueModel={context.revenue_model}/>}
      {context.profile != null && !displayProfile && <p className="mt-3 rounded-xl border border-ink/10 p-3 text-sm text-muted" role="status">The saved structured profile could not be displayed safely. Other founder notes and report sections remain available.</p>}
    </section>;
}

export default function AnalysisView({ analysis, cases }: { analysis: Analysis; cases: CasesResponse | null }) {
  const reduce = useReducedMotion();
  const result = analysis.result;
  const researchNode = Array.isArray(analysis.input?.tags) && typeof analysis.input.tags[0] === "string"
    ? analysis.input.tags[0]
    : typeof analysis.input?.category === "string" ? analysis.input.category : "Industry";

  return <motion.main className="mx-auto w-full max-w-[1440px] px-4 pb-24 pt-6 md:px-8 md:pt-10 xl:px-12"
    initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: .35 }}>
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
      <Link href="/history" className="inline-flex min-h-11 items-center gap-2 rounded-full border border-ink/10 px-4 transition-colors hover:border-coral hover:text-text focus-visible:outline-2 focus-visible:outline-coral"><span aria-hidden="true">←</span> All analyses</Link>
      <span className="inline-flex items-center gap-2"><span className="size-1.5 rounded-full bg-lime" aria-hidden="true"/>Saved analysis</span>
    </div>

    <Overview analysis={analysis}/>

    <section className="mt-6 rounded-[24px] border border-ink/10 bg-dark-surface p-5 md:p-7" aria-labelledby="technical-model-title">
      <p className="eyebrow text-coral">Interactive startup analysis</p>
      <h2 id="technical-model-title" className="mt-2 font-display text-2xl">Risk tree</h2>
      <p className="mt-3 max-w-4xl text-sm leading-relaxed text-muted">The tree combines two separate paths: startup breakpoints from the structured profile, and historical TreeSHAP attribution from the classifier. Select a startup breakpoint to see what submitted information points to it, how it could break in practice, what remains unknown, and what to validate next. Historical model output is context, not a startup diagnosis.</p>
      <div className="mt-5"><PlexTree result={result} title={analysis.title} analysisId={analysis.id} diagnostics={analysis.diagnostics_state === "available" ? analysis.diagnostics : null}/></div>
      {analysis.diagnostics_state === "unavailable" && <p className="mt-4 rounded-xl border border-ink/10 p-4 text-sm text-muted" role="status">Startup diagnostics are unavailable for this saved analysis. The historical model trace and remaining report sections are still accessible.</p>}
    </section>

    <section id="evidence-examples" className="mt-8 scroll-mt-24" aria-labelledby="evidence-examples-title">
      <div className="mb-5"><p className="eyebrow text-lime">Independent information sources</p><h2 id="evidence-examples-title" className="mt-2 font-display text-3xl">Research and historical examples</h2><p className="mt-2 max-w-3xl text-sm text-muted">External research, curated company reports, and model output are separate. None of them independently verifies the information you entered or proves what will happen to this startup.</p></div>
      <CasesPanel data={cases} analysisId={analysis.id} researchNode={researchNode}/>
    </section>

    <details className="mt-10 rounded-2xl border border-ink/10 bg-dark-surface p-5 text-sm">
      <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 font-semibold focus-visible:outline-2 focus-visible:outline-coral"><span>Methodology limitations</span><span className="text-coral" aria-hidden="true">＋</span></summary>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-muted">{(Array.isArray(result?.limitations) ? result.limitations : []).map((limitation, index) => <li key={`${index}-${limitation}`}>{limitation}</li>)}</ul>
      {result?.disclaimer && <p className="mt-4 border-t border-ink/10 pt-4 text-muted">{result.disclaimer}</p>}
    </details>

    <details className="mt-10 rounded-[24px] border border-ink/10 bg-dark-surface p-5 md:p-7">
      <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-3 font-semibold focus-visible:outline-2 focus-visible:outline-coral"><span>Founder-submitted information, structured profile &amp; historical model context</span><span className="text-coral" aria-hidden="true">＋</span></summary>
      <FounderInformation analysis={analysis}/>

      <section className="mt-6 rounded-[24px] border border-coral/20 bg-dark-surface p-5 md:p-7" aria-labelledby="historical-model-context-title">
        <p className="eyebrow text-coral">Historical model context</p>
        <h2 id="historical-model-context-title" className="mt-2 font-display text-2xl">What this historical analysis can tell you</h2>
        <p className="mt-3 max-w-4xl text-sm leading-relaxed text-muted">The statistical model learned patterns from companies with recorded final outcomes. Those data do not establish a consistent prediction time horizon or a prospective probability for this startup. No individual failure probability, risk band, or overall risk score is presented here.</p>
        <p className="mt-3 max-w-4xl text-sm leading-relaxed text-muted">The model used the submitted location and industry fields (and, for older company-stage analyses, historical funding and company fields). It does not assess the free-text notes as verified facts. Model attribution is technical context about the classifier, not a diagnosis, causal explanation, or evidence that a weakness exists in this business.</p>
        <dl className="mt-4 grid gap-x-6 gap-y-3 rounded-2xl border border-ink/10 bg-ink/5 p-4 text-sm sm:grid-cols-2">
          <div><dt className="text-xs text-muted">Model artifact</dt><dd className="mt-1 break-all font-mono text-xs text-text" title={result?.model_version ?? undefined}>{result?.model_version ? result.model_version.slice(0, 16) : "Not recorded for this saved analysis"}</dd></div>
          <div><dt className="text-xs text-muted">Prediction horizon</dt><dd className="mt-1 text-text">Not established by the available outcome data</dd></div>
        </dl>
        <p className="mt-4 text-xs leading-relaxed text-muted">The interactive tree is shown above the report. Its historical attribution and startup diagnostics remain separate selectable branches.</p>
      </section>
    </details>

  </motion.main>;
}
