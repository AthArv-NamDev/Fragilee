"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "motion/react";
import { apiFetch, ApiError } from "@/lib/api";
import { COUNTRY_NAMES, OTHER_COUNTRY, STATE_NAMES, US_STATES } from "@/lib/geo";
import type { BusinessModelType, Context, ProfileMetric, ProfileStage, Provenance } from "@/lib/types";

const MAX_TAGS = 5;
const MIN_CONCEPT = 10;
type StepId = "name" | "concept" | "vision" | "details" | "country" | "state" | "tags" | "review";
type Props = { countries: string[]; states: string[]; tags: string[] };
type MetricDraft = { field_id: string; value: string; currency: string; provenance: Provenance; period: string };
const METRIC_CHOICES: [string, string, string, boolean, boolean][] = [
  ["customer_interviews", "Customer interviews", "interviews", false, false], ["paying_customers", "Paying customers", "customers", false, false], ["active_users", "Active users", "users", false, false],
  ["growth_rate", "Growth rate", "percent", false, true], ["retention_rate", "Retention rate", "percent", false, true], ["churn_rate", "Churn rate", "percent", false, true],
  ["signed_contracts", "Signed contracts", "contracts", false, false], ["preorders", "Pre-orders", "orders", false, false], ["pilots", "Pilots", "pilots", false, false],
  ["average_selling_price", "Average selling price", "currency/customer", true, false], ["variable_cost_per_unit", "Variable cost per unit", "currency/unit", true, false], ["gross_margin", "Gross margin", "percent", false, false], ["contribution_margin", "Contribution margin", "percent", false, false],
  ["customer_acquisition_cost", "Customer acquisition cost", "currency/customer", true, false], ["cac_payback_period", "CAC payback period", "months", false, false], ["cash_balance", "Cash balance", "currency", true, false], ["monthly_operating_expense", "Monthly operating expense", "currency/month", true, false], ["runway", "Runway", "months", false, false],
  ["average_contract_value", "Average contract value", "currency/year", true, false], ["sales_cycle", "Sales cycle", "days", false, false], ["transaction_volume", "Transaction volume", "currency", true, false], ["take_rate", "Take rate", "percent", false, false], ["active_buyers", "Active buyers", "buyers", false, false], ["active_sellers", "Active sellers", "sellers", false, false], ["repeat_transactions", "Repeat transactions", "percent", false, false],
  ["orders", "Orders", "orders", false, false], ["average_order_value", "Average order value", "currency/order", true, false], ["repeat_purchase_rate", "Repeat purchase rate", "percent", false, false], ["fulfilment_cost", "Fulfilment cost", "currency/order", true, false], ["bill_of_materials", "Bill of materials", "currency/unit", true, false], ["minimum_order_quantity", "Minimum order quantity", "units", false, false], ["utilization", "Utilization", "percent", false, false], ["revenue_per_delivery_unit", "Revenue per delivery unit", "currency/unit", true, false],
];

const card = "text-left rounded-2xl border p-5 transition-colors focus-visible:outline-2 focus-visible:outline-white";
const idle = "bg-dark-surface border-ink/10 hover:border-violet";
const chosen = "bg-violet/20 border-violet";
const input = "w-full bg-dark-surface border border-ink/10 rounded-lg px-4 py-3 text-text";
const primary = "min-h-11 rounded-full bg-sage px-8 font-semibold button-label-on-sage transition-colors hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet disabled:opacity-50 disabled:cursor-not-allowed";

export default function NewAnalysisFlow({ countries, states, tags }: Props) {
  const router = useRouter();
  const reduce = useReducedMotion();
  const [index, setIndex] = useState(0);
  const [title, setTitle] = useState("");
  const [concept, setConcept] = useState("");
  const [vision, setVision] = useState("");
  const [customer, setCustomer] = useState("");
  const [revenue, setRevenue] = useState("");
  const [team, setTeam] = useState("");
  const [worry, setWorry] = useState("");
  const [businessModel, setBusinessModel] = useState<BusinessModelType | "">("");
  const [profileStage, setProfileStage] = useState<ProfileStage | "">("");
  const [customerType, setCustomerType] = useState<"b2b" | "b2c" | "b2b2c" | "other" | "not_sure_yet" | "">("");
  const [customerSegment, setCustomerSegment] = useState("");
  const [profileProblem, setProfileProblem] = useState("");
  const [profileSolution, setProfileSolution] = useState("");
  const [profileExtras, setProfileExtras] = useState<Record<string, string>>({});
  const [fundingStatus, setFundingStatus] = useState("");
  const [metricDrafts, setMetricDrafts] = useState<MetricDraft[]>([]);
  const [productStatus, setProductStatus] = useState<"concept" | "prototype" | "mvp" | "beta" | "launched" | "not_sure_yet" | "">("");
  const [modelDetail, setModelDetail] = useState("");
  const [metricProvenance, setMetricProvenance] = useState<Provenance>("measured");
  const [monthlyRevenue, setMonthlyRevenue] = useState("");
  const [revenueCurrency, setRevenueCurrency] = useState("USD");
  const [revenueProvenance, setRevenueProvenance] = useState<Provenance>("measured");
  const [country, setCountry] = useState<string | null>(null);
  const [state, setState] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const submissionInProgress = useRef(false);

  const steps: StepId[] = useMemo(
    () => (country === "USA"
      ? ["name", "concept", "vision", "details", "country", "state", "tags", "review"]
      : ["name", "concept", "vision", "details", "country", "tags", "review"]),
    [country],
  );
  const step = steps[Math.min(index, steps.length - 1)];
  useEffect(() => headingRef.current?.focus(), [step]); // moves screen readers to the new question

  const shownTags = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? tags.filter((t) => t.toLowerCase().includes(q)) : tags;
  }, [tags, query]);
  const popularStates = states.filter((s) => s !== "NONE" && s !== "OTHER");
  const place = country === OTHER_COUNTRY ? "Somewhere else" : country ? (COUNTRY_NAMES[country] ?? country) : "";

  const next = () => setIndex((i) => i + 1);
  const goTo = (id: StepId) => { setError(null); setIndex(steps.indexOf(id)); };
  function chooseCountry(code: string) {
    setCountry(code);
    if (code !== "USA") setState(null);
    setIndex(steps.indexOf("country") + 1); // the next step is the state (US) or the tags (anywhere else)
  }
  function chooseState(code: string) {
    setState(code);
    setIndex(steps.indexOf("state") + 1);
  }
  function toggleTag(t: string) {
    setPicked((p) => (p.includes(t) ? p.filter((x) => x !== t) : p.length < MAX_TAGS ? [...p, t] : p));
  }

  function buildContext(): Context {
    const c: Context = {};
    if (concept.trim()) c.concept = concept.trim();
    if (vision.trim()) c.vision = vision.trim();
    if (customer.trim()) c.customer = customer.trim();
    if (revenue.trim()) c.revenue_model = revenue.trim();
    if (worry.trim()) c.biggest_worry = worry.trim();
    const profile: NonNullable<Context["profile"]> = { profile_schema_version: 1, last_updated_at: new Date().toISOString().slice(0, 10) };
    const identity: NonNullable<typeof profile.identity> = {};
    if (businessModel) identity.business_model = businessModel;
    if (profileStage) identity.stage = profileStage;
    if (profileProblem.trim()) identity.problem = profileProblem.trim();
    if (profileSolution.trim()) identity.proposed_solution = profileSolution.trim();
    if (country) identity.operating_geography = place;
    const extra = (key: string) => profileExtras[key]?.trim() || undefined;
    const customerProfile = { ...(customerType ? { customer_type: customerType } : {}), ...(customerSegment.trim() ? { customer_segment: customerSegment.trim() } : {}), ...(extra("customer_description") ? { customer_description: extra("customer_description") } : {}), ...(extra("discovery_evidence") ? { discovery_evidence: extra("discovery_evidence") } : {}), ...(extra("willingness_to_pay_evidence") ? { willingness_to_pay_evidence: extra("willingness_to_pay_evidence") } : {}), ...(extra("existing_alternatives") ? { existing_alternatives: extra("existing_alternatives") } : {}), ...(extra("market_size_assumption") ? { market_size_assumption: extra("market_size_assumption") } : {}) };
    if (Object.keys(customerProfile).length) profile.customer_market = customerProfile;
    const tractionProfile = { ...(productStatus ? { product_status: productStatus } : {}), ...(extra("customer_validation") ? { customer_validation: extra("customer_validation") } : {}), ...(extra("acquisition_channel") ? { acquisition_channel: extra("acquisition_channel") } : {}) };
    if (Object.keys(tractionProfile).length) profile.product_traction = tractionProfile;
    const financeProfile = { ...(fundingStatus ? { funding_status: fundingStatus as NonNullable<typeof profile.finance>["funding_status"] } : {}), ...(extra("funding_sources") ? { funding_sources: extra("funding_sources") } : {}), ...(extra("upcoming_milestones") ? { upcoming_milestones: extra("upcoming_milestones") } : {}) };
    if (Object.keys(financeProfile).length) profile.finance = financeProfile;
    const operationsProfile = { ...(extra("team_capabilities") ? { team_capabilities: extra("team_capabilities") } : {}), ...(extra("capability_gaps") ? { capability_gaps: extra("capability_gaps") } : {}), ...(extra("critical_dependencies") ? { critical_dependencies: extra("critical_dependencies") } : {}), ...(extra("suppliers_or_distribution") ? { suppliers_or_distribution: extra("suppliers_or_distribution") } : {}), ...(extra("technology_constraints") ? { technology_constraints: extra("technology_constraints") } : {}), ...(extra("regulatory_context") ? { regulatory_context: extra("regulatory_context") } : {}) };
    if (Object.keys(operationsProfile).length || profile.team_operations) profile.team_operations = { ...operationsProfile, ...(profile.team_operations ?? {}) };
    const detailKey: Partial<Record<BusinessModelType, string>> = { b2b_saas: "sales_cycle_notes", marketplace: "liquidity_notes", dtc_ecommerce: "fulfilment_notes", hardware: "tooling_and_production", fintech: "infrastructure_dependencies", biotech_medtech: "regulatory_pathway", services_consulting: "delivery_capacity_notes" };
    if (businessModel && modelDetail.trim() && detailKey[businessModel]) {
      profile.business_model_details = { kind: businessModel, [detailKey[businessModel]!]: modelDetail.trim() } as NonNullable<typeof profile.business_model_details>;
    }
    if (monthlyRevenue.trim() && revenueProvenance !== "unknown" && revenueProvenance !== "not_applicable") {
      const amount = Number(monthlyRevenue);
      if (Number.isFinite(amount) && amount >= 0 && /^[A-Z]{3}$/.test(revenueCurrency)) {
        profile.economics = { ...(extra("pricing_model") ? { pricing_model: extra("pricing_model") } : {}), metrics: [{ field_id: "revenue_amount", value: amount, unit: "currency", currency: revenueCurrency, period: "month", provenance: revenueProvenance, confirmed_by_user: true, applicability: "applicable" }] };
      }
    } else if (revenueProvenance === "unknown" || revenueProvenance === "not_applicable") {
      profile.economics = { ...(extra("pricing_model") ? { pricing_model: extra("pricing_model") } : {}), metrics: [{ field_id: "revenue_amount", provenance: revenueProvenance, confirmed_by_user: true, applicability: revenueProvenance }] };
    } else if (extra("pricing_model")) {
      profile.economics = { pricing_model: extra("pricing_model") };
    }
    if (businessModel || profileStage || profileProblem.trim() || profileSolution.trim() || country) profile.identity = identity;
    const teamValue = Number(team);
    if (metricProvenance !== "unknown" && metricProvenance !== "not_applicable" && team.trim() && Number.isInteger(teamValue) && teamValue >= 1 && teamValue <= 500) {
      const metric: ProfileMetric = { field_id: "team_size", value: teamValue, unit: "people", provenance: metricProvenance, confirmed_by_user: true, applicability: "applicable" };
      profile.team_operations = { ...(profile.team_operations ?? {}), metrics: [...(profile.team_operations?.metrics ?? []), metric] };
    }
    // Explicit unknown and not-applicable states are retained, never translated into zero.
    if (metricProvenance === "unknown" || metricProvenance === "not_applicable") {
      profile.team_operations = { ...(profile.team_operations ?? {}), metrics: [...(profile.team_operations?.metrics ?? []), { field_id: "team_size", provenance: metricProvenance, confirmed_by_user: true, applicability: metricProvenance }] };
    }
    for (const draft of metricDrafts) {
      const choice = METRIC_CHOICES.find(([id]) => id === draft.field_id);
      if (!choice) continue;
      const [field_id, , unit, needsCurrency, needsPeriod] = choice;
      const unknown = draft.provenance === "unknown" || draft.provenance === "not_applicable";
      const value = draft.value.trim() ? Number(draft.value) : undefined;
      if (!unknown && (value === undefined || !Number.isFinite(value))) continue;
      const metric: ProfileMetric = { field_id: field_id as ProfileMetric["field_id"], ...(unknown ? {} : { value, unit, ...(needsCurrency ? { currency: draft.currency } : {}), ...(needsPeriod ? { period: draft.period as ProfileMetric["period"] } : {}) }), provenance: draft.provenance, confirmed_by_user: true, applicability: draft.provenance === "unknown" ? "unknown" : draft.provenance === "not_applicable" ? "not_applicable" : "applicable" };
      const target = ["customer_interviews", "market_size"].includes(field_id) ? "customer_market" : ["cash_balance", "monthly_operating_expense", "runway"].includes(field_id) ? "finance" : ["average_selling_price", "variable_cost_per_unit", "gross_margin", "contribution_margin", "customer_acquisition_cost", "cac_payback_period", "average_contract_value"].includes(field_id) ? "economics" : "product_traction";
      if (target === "customer_market") profile.customer_market = { ...(profile.customer_market ?? {}), metrics: [...(profile.customer_market?.metrics ?? []), metric] };
      else if (target === "finance") profile.finance = { ...(profile.finance ?? {}), metrics: [...(profile.finance?.metrics ?? []), metric] };
      else if (target === "economics") profile.economics = { ...(profile.economics ?? {}), metrics: [...(profile.economics?.metrics ?? []), metric] };
      else profile.product_traction = { ...(profile.product_traction ?? {}), metrics: [...(profile.product_traction?.metrics ?? []), metric] };
    }
    if (Object.keys(profile).some((key) => key !== "profile_schema_version" && key !== "last_updated_at")) c.profile = profile;
    return c;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (submissionInProgress.current) return;
    if (!country || picked.length === 0 || !title.trim() || concept.trim().length < MIN_CONCEPT || (country === "USA" && !state)) return;
    const teamNumber = Number(team);
    if (team.trim() && metricProvenance !== "unknown" && metricProvenance !== "not_applicable" && (!Number.isInteger(teamNumber) || teamNumber < 1 || teamNumber > 500)) {
      setError("Team size must be a whole number from 1 to 500, or select Unknown.");
      return;
    }
    if (monthlyRevenue.trim() && revenueProvenance !== "unknown" && revenueProvenance !== "not_applicable" && (!Number.isFinite(Number(monthlyRevenue)) || Number(monthlyRevenue) < 0 || !/^[A-Z]{3}$/.test(revenueCurrency))) {
      setError("Enter a non-negative monthly revenue and a three-letter currency code, or select Unknown.");
      return;
    }
    if (metricDrafts.some((draft) => {
      const choice = METRIC_CHOICES.find(([id]) => id === draft.field_id);
      if (!choice) return false;
      const [, , , needsCurrency, needsPeriod] = choice;
      const unknown = draft.provenance === "unknown" || draft.provenance === "not_applicable";
      const numeric = Number(draft.value);
      const nonNegative = new Set(["growth_rate", "gross_margin", "contribution_margin"]);
      const percentage = choice[2] === "percent" && draft.field_id !== "growth_rate";
      return !unknown && (!draft.value.trim() || !Number.isFinite(numeric) || (!nonNegative.has(draft.field_id) && numeric < 0) || (percentage && numeric > 100) || (draft.currency && !/^[A-Z]{3}$/.test(draft.currency)) || (needsCurrency && !/^[A-Z]{3}$/.test(draft.currency)) || (needsPeriod && !draft.period));
    })) {
      setError("Complete each added metric with a valid value, currency, and period where requested, or mark it Unknown / Not applicable.");
      return;
    }
    submissionInProgress.current = true;
    setBusy(true);
    setError(null);
    try {
      const modelInput = { country, ...(country === "USA" ? { state } : {}), tags: picked };
      const created = await apiFetch<{ id: string }>("/v1/analyses", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), stage: "stage1", input: modelInput, context: buildContext() }),
      });
      router.push(`/analysis/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 429 ? "That was a lot of requests. Wait a minute and try again."
          : err.status === 401 ? "Your session expired. Sign in again."
          : err.status === 422 ? `Please review: ${err.message || "one or more profile fields were not accepted"}`
          : err.status === 503 ? "Saving is unavailable right now. Try again in a moment."
          : err.message,
        );
      } else {
        setError("Could not reach the API. Is it running on port 8000?");
      }
      submissionInProgress.current = false;
      setBusy(false);
    }
  }

  const heading: Record<StepId, [string, string]> = {
    name: ["What is your startup called?", "A working name is fine. Only you can see it."],
    concept: ["What does it do?", "Two or three sentences. Who is it for, and what problem does it fix?"],
    vision: ["Where could this go?", "In five years, what does success look like? You can skip this."],
    details: ["A few more things.", "Optional notes do not change the historical model output. If you open research later, up to 18 topic words may be sent to OpenAlex; your startup title and full notes are not."],
    country: ["Where does the startup live?", "Pick the closest match. If yours is not listed, choose somewhere else."],
    state: ["Which state?", "State only matters in the US, which is why you are seeing this."],
    tags: ["Which industries fit?", `Pick up to ${MAX_TAGS}. Closest fit is fine. These feed the risk model.`],
    review: ["Ready?", "Check your answers, then we will read the data."],
  };
  const conceptOk = concept.trim().length >= MIN_CONCEPT;

  return (
    <main className="mx-auto min-h-screen w-full max-w-5xl px-4 py-7 md:px-8 md:py-12">
      <div className="mb-9 flex items-center justify-between gap-4"><div><p className="eyebrow text-coral">Fragilee / test the idea</p><h1 className="mt-2 font-display text-2xl md:text-3xl">A clearer look starts with context.</h1></div><div aria-hidden="true" className="hidden size-16 rounded-[22px] border border-coral/30 bg-coral-soft md:grid md:place-items-center"><span className="font-display text-2xl text-coral">F.</span></div></div>
      <div className="mx-auto max-w-3xl rounded-[28px] border border-ink/10 bg-dark-surface p-5 surface-lift md:p-9">
      <div className="flex items-center justify-between text-sm text-muted mb-4">
        <span className="px-3 py-1.5 rounded-full text-xs bg-violet/20 text-text">Level 1 · Your idea</span>
        <span>Step {Math.min(index, steps.length - 1) + 1}{country ? ` of ${steps.length}` : ""}</span>
      </div>
      <div className="flex gap-1.5 mb-10" aria-hidden="true">
        {steps.map((s, i) => <i key={s} className={`h-1 flex-1 rounded ${i <= index ? "bg-violet" : "bg-ink/10"}`} />)}
      </div>

      <motion.div key={step} initial={reduce ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduce ? 0 : .28, ease: "easeOut" }}>
      <h2 ref={headingRef} tabIndex={-1} className="font-display text-3xl mb-2 outline-none">{heading[step][0]}</h2>
      <p className="text-muted mb-8">{heading[step][1]}</p>

      {step === "name" && (
        <form onSubmit={(e) => { e.preventDefault(); if (title.trim()) next(); }}>
          <label htmlFor="title" className="sr-only">Startup name</label>
          <input id="title" required maxLength={80} placeholder="e.g. Brewdash" value={title} onChange={(e) => setTitle(e.target.value)} className={input} />
          <button type="submit" disabled={!title.trim()} className={`mt-8 ${primary}`}>Next</button>
        </form>
      )}

      {step === "concept" && (
        <div>
          <label htmlFor="concept" className="sr-only">What it does</label>
          <textarea id="concept" rows={5} maxLength={800} value={concept} onChange={(e) => setConcept(e.target.value)}
            placeholder="e.g. Coffee delivery for small offices, bought on a monthly plan." className={input} />
          <p className="text-xs text-muted mt-2 flex justify-between">
            <span>{conceptOk ? "" : `A little more, please (at least ${MIN_CONCEPT} characters).`}</span><span>{concept.length} / 800</span>
          </p>
          <button type="button" disabled={!conceptOk} onClick={next} className={`mt-6 ${primary}`}>Next</button>
        </div>
      )}

      {step === "vision" && (
        <div>
          <label htmlFor="vision" className="sr-only">Vision</label>
          <textarea id="vision" rows={4} maxLength={800} value={vision} onChange={(e) => setVision(e.target.value)}
            placeholder="e.g. The default way every office in Europe buys coffee." className={input} />
          <p className="text-xs text-muted mt-2 text-right">{vision.length} / 800</p>
          <div className="mt-6 flex gap-4 items-center">
            <button type="button" onClick={next} className={primary}>{vision.trim() ? "Next" : "Skip"}</button>
          </div>
        </div>
      )}

      {step === "details" && (
        <div className="space-y-6">
          <div>
            <label htmlFor="customer" className="block text-sm text-muted mb-2">Who is the customer?</label>
            <input id="customer" maxLength={200} value={customer} onChange={(e) => setCustomer(e.target.value)} placeholder="e.g. Office managers" className={input} />
          </div>
          <div>
            <label htmlFor="revenue" className="block text-sm text-muted mb-2">How does it make money?</label>
            <input id="revenue" maxLength={200} value={revenue} onChange={(e) => setRevenue(e.target.value)} placeholder="e.g. Monthly subscription" className={input} />
          </div>
          <details className="rounded-xl border border-ink/10 p-4">
            <summary className="cursor-pointer font-semibold">Structured profile (optional)</summary>
            <p className="mt-2 text-sm text-muted">These founder-supplied details are saved with your report. They do not change the historical model result.</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="text-sm text-muted">Business model
                <select value={businessModel} onChange={(e) => setBusinessModel(e.target.value as BusinessModelType | "")} className={`${input} mt-2`}>
                  <option value="">Not provided</option><option value="b2b_saas">B2B SaaS</option><option value="b2c_saas">B2C SaaS</option><option value="marketplace">Marketplace</option><option value="dtc_ecommerce">DTC / E-commerce</option><option value="hardware">Hardware</option><option value="fintech">Fintech</option><option value="biotech_medtech">Biotech / Medtech</option><option value="services_consulting">Services / Consulting</option><option value="consumer_application">Consumer application</option><option value="platform_developer_tools">Platform / Developer tools</option><option value="other">Other</option><option value="not_yet_determined">Not yet determined</option>
                </select>
              </label>
              <label className="text-sm text-muted">Current stage
                <select value={profileStage} onChange={(e) => setProfileStage(e.target.value as ProfileStage | "")} className={`${input} mt-2`}>
                  <option value="">Not provided</option><option value="idea_concept">Idea / Concept</option><option value="validation_customer_discovery">Validation / Customer discovery</option><option value="mvp_product_development">MVP / Product development</option><option value="pre_revenue">Pre-revenue</option><option value="early_revenue">Early revenue</option><option value="early_growth">Early growth</option><option value="scaling">Scaling</option><option value="mature_established">Mature / Established</option><option value="not_sure_yet">Not sure yet</option>
                </select>
              </label>
              <label className="text-sm text-muted">Customer type
                <select value={customerType} onChange={(e) => setCustomerType(e.target.value as typeof customerType)} className={`${input} mt-2`}><option value="">Not provided</option><option value="b2b">B2B</option><option value="b2c">B2C</option><option value="b2b2c">B2B2C</option><option value="other">Other</option><option value="not_sure_yet">Not sure yet</option></select>
              </label>
              <label className="text-sm text-muted">Customer segment (optional)<input value={customerSegment} onChange={(e) => setCustomerSegment(e.target.value)} maxLength={200} className={`${input} mt-2`} placeholder="e.g. independent retailers" /></label>
              <label className="text-sm text-muted">Problem you are addressing (optional)<textarea value={profileProblem} onChange={(e) => setProfileProblem(e.target.value)} rows={2} maxLength={800} className={`${input} mt-2`} /></label>
              <label className="text-sm text-muted">How your product addresses it (optional)<textarea value={profileSolution} onChange={(e) => setProfileSolution(e.target.value)} rows={2} maxLength={800} className={`${input} mt-2`} /></label>
              <label className="text-sm text-muted">Product status
                <select value={productStatus} onChange={(e) => setProductStatus(e.target.value as typeof productStatus)} className={`${input} mt-2`}><option value="">Not provided</option><option value="concept">Concept</option><option value="prototype">Prototype</option><option value="mvp">MVP</option><option value="beta">Beta</option><option value="launched">Launched</option><option value="not_sure_yet">Not sure yet</option></select>
              </label>
              {businessModel && ({ b2b_saas: "Sales cycle context", marketplace: "Marketplace liquidity context", dtc_ecommerce: "Fulfilment context", hardware: "Tooling and production context", fintech: "Financial infrastructure dependencies", biotech_medtech: "Regulatory pathway context", services_consulting: "Delivery capacity context" } as Partial<Record<BusinessModelType, string>>)[businessModel] && <label className="text-sm text-muted">{({ b2b_saas: "Sales cycle context", marketplace: "Marketplace liquidity context", dtc_ecommerce: "Fulfilment context", hardware: "Tooling and production context", fintech: "Financial infrastructure dependencies", biotech_medtech: "Regulatory pathway context", services_consulting: "Delivery capacity context" } as Partial<Record<BusinessModelType, string>>)[businessModel]}<textarea value={modelDetail} onChange={(e) => setModelDetail(e.target.value)} rows={2} maxLength={800} className={`${input} mt-2`} placeholder="Optional context for this business model" /></label>}
              <details className="sm:col-span-2 rounded-xl border border-ink/10 p-4">
                <summary className="cursor-pointer font-semibold">More optional profile context</summary>
                <p className="mt-2 text-xs text-muted">Only answer what fits your business. Blank fields stay unprovided; they are not treated as weaknesses.</p>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  {[["customer_description", "Who typically uses or buys it?"], ["discovery_evidence", "What have you learned from customer discovery?"], ["willingness_to_pay_evidence", "Any evidence of willingness to pay?"], ["existing_alternatives", "What alternatives do customers use today?"], ["market_size_assumption", "Market-size estimate and its source, if known"], ["customer_validation", "How have you validated the product?"], ["acquisition_channel", "How do customers find you?"], ["pricing_model", "Pricing approach"], ["funding_sources", "Funding sources (optional)"], ["upcoming_milestones", "Upcoming financial or product milestones"], ["team_capabilities", "Relevant team capabilities"], ["capability_gaps", "Known capability gaps"], ["critical_dependencies", "Critical dependencies"], ["suppliers_or_distribution", "Supplier or distribution dependencies"], ["technology_constraints", "Technology or infrastructure constraints"], ["regulatory_context", "Regulatory context, if relevant"]].map(([key, label]) => <label key={key} className="text-sm text-muted">{label}<textarea value={profileExtras[key] ?? ""} onChange={(e) => setProfileExtras((current) => ({ ...current, [key]: e.target.value }))} rows={2} maxLength={800} className={`${input} mt-2`} /></label>)}
                  <label className="text-sm text-muted">Funding status<select value={fundingStatus} onChange={(e) => setFundingStatus(e.target.value)} className={`${input} mt-2`}><option value="">Not provided</option><option value="bootstrapped">Bootstrapped</option><option value="grants">Grants</option><option value="angel">Angel</option><option value="venture">Venture</option><option value="debt">Debt</option><option value="mixed">Mixed</option><option value="not_funded">Not funded</option><option value="not_sure_yet">Not sure yet</option></select></label>
                </div>
              </details>
              <details className="sm:col-span-2 rounded-xl border border-ink/10 p-4">
                <summary className="cursor-pointer font-semibold">Optional quantitative evidence</summary>
                <p className="mt-2 text-xs text-muted">Add only measurements you have. Values stay separate from the model result. Estimated, assumed, unknown, and not-applicable states are retained as selected.</p>
                <div className="mt-4 space-y-3">
                  {metricDrafts.map((draft, index) => {
                    const selected = METRIC_CHOICES.find(([id]) => id === draft.field_id);
                    const unavailable = new Set(metricDrafts.filter((_, i) => i !== index).map((item) => item.field_id));
                    return <div key={index} className="rounded-xl border border-ink/10 p-3">
                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="text-sm text-muted">Metric<select value={draft.field_id} onChange={(e) => setMetricDrafts((items) => items.map((item, i) => i === index ? { ...item, field_id: e.target.value } : item))} className={`${input} mt-2`}><option value="">Choose a metric</option>{METRIC_CHOICES.filter(([id]) => !unavailable.has(id) || id === draft.field_id).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
                        <label className="text-sm text-muted">Provenance<select value={draft.provenance} onChange={(e) => setMetricDrafts((items) => items.map((item, i) => i === index ? { ...item, provenance: e.target.value as Provenance } : item))} className={`${input} mt-2`}><option value="measured">Measured</option><option value="estimated">Estimated</option><option value="assumed">Assumed</option><option value="unknown">Unknown</option><option value="not_applicable">Not applicable</option></select></label>
                        <label className="text-sm text-muted">Value{selected ? ` (${selected[2]})` : ""}<input type="number" step="any" value={draft.value} disabled={draft.provenance === "unknown" || draft.provenance === "not_applicable" || !selected} onChange={(e) => setMetricDrafts((items) => items.map((item, i) => i === index ? { ...item, value: e.target.value } : item))} className={`${input} mt-2`} /></label>
                        {selected?.[3] && <label className="text-sm text-muted">Currency (3-letter code)<input maxLength={3} value={draft.currency} disabled={draft.provenance === "unknown" || draft.provenance === "not_applicable"} onChange={(e) => setMetricDrafts((items) => items.map((item, i) => i === index ? { ...item, currency: e.target.value.toUpperCase() } : item))} className={`${input} mt-2`} /></label>}
                        {selected?.[4] && <label className="text-sm text-muted">Measurement period<select value={draft.period} disabled={draft.provenance === "unknown" || draft.provenance === "not_applicable"} onChange={(e) => setMetricDrafts((items) => items.map((item, i) => i === index ? { ...item, period: e.target.value } : item))} className={`${input} mt-2`}><option value="">Choose a period</option><option value="month">Month</option><option value="quarter">Quarter</option><option value="year">Year</option></select></label>}
                      </div>
                      <button type="button" onClick={() => setMetricDrafts((items) => items.filter((_, i) => i !== index))} className="mt-2 min-h-11 text-sm text-muted underline">Remove metric</button>
                    </div>;
                  })}
                  <button type="button" onClick={() => setMetricDrafts((items) => [...items, { field_id: "", value: "", currency: "USD", provenance: "measured", period: "" }])} disabled={metricDrafts.length >= METRIC_CHOICES.length} className="min-h-11 rounded-full border border-ink/20 px-4 text-sm hover:border-violet disabled:opacity-50">+ Add a metric</button>
                </div>
              </details>
              <label className="text-sm text-muted">Team size provenance
                <select value={metricProvenance} onChange={(e) => setMetricProvenance(e.target.value as Provenance)} className={`${input} mt-2`}><option value="measured">Measured</option><option value="estimated">Estimated</option><option value="assumed">Assumed</option><option value="unknown">Unknown</option><option value="not_applicable">Not applicable</option></select>
              </label>
            </div>
            {metricProvenance !== "unknown" && metricProvenance !== "not_applicable" && <p className="mt-2 text-xs text-muted">Team size stays optional. Enter it above; its provenance is saved separately.</p>}
          </details>
          <div className="grid sm:grid-cols-2 gap-6">
            <div>
              <label htmlFor="team" className="block text-sm text-muted mb-2">How many people are on the team?</label>
              <input id="team" type="number" inputMode="numeric" min={1} max={500} disabled={metricProvenance === "unknown" || metricProvenance === "not_applicable"} value={team} onChange={(e) => setTeam(e.target.value)} placeholder="e.g. 3" className={input} />
            </div>
            <fieldset className="rounded-xl border border-ink/10 p-4">
              <legend className="px-1 text-sm font-semibold">Monthly revenue (optional)</legend>
              <p className="mb-3 text-xs text-muted">Leave blank if you do not want to share it. An unknown response is not treated as zero.</p>
              <div className="grid gap-3 sm:grid-cols-3">
                <label className="text-sm text-muted">Amount<input type="number" min="0" step="any" value={monthlyRevenue} disabled={revenueProvenance === "unknown" || revenueProvenance === "not_applicable"} onChange={(e) => setMonthlyRevenue(e.target.value)} className={`${input} mt-2`} /></label>
                <label className="text-sm text-muted">Currency<input value={revenueCurrency} maxLength={3} disabled={revenueProvenance === "unknown" || revenueProvenance === "not_applicable"} onChange={(e) => setRevenueCurrency(e.target.value.toUpperCase())} className={`${input} mt-2`} aria-label="Revenue currency, three letter code" /></label>
                <label className="text-sm text-muted">Provenance<select value={revenueProvenance} onChange={(e) => setRevenueProvenance(e.target.value as Provenance)} className={`${input} mt-2`}><option value="measured">Measured</option><option value="estimated">Estimated</option><option value="assumed">Assumed</option><option value="unknown">Unknown</option><option value="not_applicable">Not applicable</option></select></label>
              </div>
            </fieldset>
            <div>
              <label htmlFor="worry" className="block text-sm text-muted mb-2">What worries you most?</label>
              <input id="worry" maxLength={200} value={worry} onChange={(e) => setWorry(e.target.value)} placeholder="e.g. Running out of cash" className={input} />
            </div>
          </div>
          <button type="button" onClick={next} className={primary}>Next</button>
        </div>
      )}

      {step === "country" && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {countries.map((c) => (
            <button key={c} type="button" aria-pressed={country === c} onClick={() => chooseCountry(c)}
              className={`${card} ${country === c ? chosen : idle}`}>
              <span className="font-display text-lg">{COUNTRY_NAMES[c] ?? c}</span>
            </button>
          ))}
          <button type="button" aria-pressed={country === OTHER_COUNTRY} onClick={() => chooseCountry(OTHER_COUNTRY)}
            className={`${card} ${country === OTHER_COUNTRY ? chosen : idle}`}>
            <span className="font-display text-lg">Somewhere else</span>
          </button>
        </div>
      )}

      {step === "state" && (
        <div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {popularStates.map((s) => (
              <button key={s} type="button" aria-pressed={state === s} onClick={() => chooseState(s)}
                className={`${card} ${state === s ? chosen : idle}`}>
                <span className="font-display text-lg">{STATE_NAMES[s] ?? s}</span>
              </button>
            ))}
          </div>
          <label htmlFor="other-state" className="block text-muted text-sm mt-8 mb-2">Not in the list? Pick another state</label>
          <select id="other-state" value="" onChange={(e) => e.target.value && chooseState(e.target.value)} className={input}>
            <option value="">Choose a state…</option>
            {US_STATES.filter(([code]) => !popularStates.includes(code)).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
        </div>
      )}

      {step === "tags" && (
        <div>
          <label htmlFor="tag-search" className="sr-only">Search industries</label>
          <input id="tag-search" type="search" placeholder="Search industries" value={query} onChange={(e) => setQuery(e.target.value)} className={`${input} mb-4`} />
          <p className="text-sm text-muted mb-3" aria-live="polite">{picked.length} of {MAX_TAGS} chosen</p>
          {picked.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {picked.map((t) => (
                <button key={t} type="button" onClick={() => toggleTag(t)} aria-label={`Remove ${t}`}
                  className="px-3 py-1.5 rounded-full text-sm bg-violet/30 border border-violet">{t} ✕</button>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-2 max-h-72 overflow-y-auto pr-1">
            {shownTags.filter((t) => !picked.includes(t)).map((t) => (
              <button key={t} type="button" onClick={() => toggleTag(t)} disabled={picked.length >= MAX_TAGS}
                className="px-3 py-1.5 rounded-full text-sm bg-dark-surface border border-ink/10 hover:border-violet disabled:opacity-40 disabled:cursor-not-allowed">
                {t}
              </button>
            ))}
            {shownTags.length === 0 && <p className="text-muted text-sm">Nothing matches. Try a shorter word.</p>}
          </div>
          <button type="button" disabled={picked.length === 0} onClick={next} className={`mt-8 ${primary}`}>Next</button>
        </div>
      )}

      {step === "review" && (
        <form onSubmit={submit}>
          <dl className="rounded-2xl bg-dark-surface border border-ink/10 divide-y divide-ink/10 text-sm">
            {([
              ["Name", title, "name"], ["What it does", concept, "concept"], ["Vision", vision || "Skipped", "vision"],
              ["Notes", [customer, revenue, team && `${team} people`, worry].filter(Boolean).join(" · ") || "None", "details"],
              ["Structured profile", [businessModel && businessModel.replaceAll("_", " "), profileStage && profileStage.replaceAll("_", " "), customerType, customerSegment, profileProblem && `Problem: ${profileProblem}`, profileSolution && `Solution: ${profileSolution}`, productStatus, modelDetail, metricProvenance === "unknown" || metricProvenance === "not_applicable" ? `Team size ${metricProvenance}` : team && `${team} people (${metricProvenance})`, revenueProvenance === "unknown" || revenueProvenance === "not_applicable" ? `Revenue ${revenueProvenance}` : monthlyRevenue && `${monthlyRevenue} ${revenueCurrency} / month (${revenueProvenance})`, ...metricDrafts.filter((m) => m.field_id).map((m) => `${METRIC_CHOICES.find(([id]) => id === m.field_id)?.[1] ?? m.field_id}: ${m.provenance === "unknown" || m.provenance === "not_applicable" ? m.provenance : `${m.value || "(value needed)"}${m.currency ? ` ${m.currency}` : ""}${m.period ? ` / ${m.period}` : ""} (${m.provenance})`}`)].filter(Boolean).join(" · ") || "Not provided", "details"],
              ["Place", [place, state ? STATE_NAMES[state] : ""].filter(Boolean).join(", "), "country"],
              ["Industries", picked.join(", "), "tags"],
            ] as [string, string, StepId][]).map(([label, value, id]) => (
              <div key={label} className="flex gap-4 p-4">
                <dt className="w-28 shrink-0 text-muted">{label}</dt>
                <dd className="flex-1 break-words">{value}</dd>
                <button type="button" onClick={() => goTo(id)} aria-label={`Edit ${label}`} className="text-muted underline-offset-4 hover:underline">Edit</button>
              </div>
            ))}
          </dl>
          <p className="text-xs text-muted mt-4">
            This historical model trace uses place and industry tags only; it does not assess demand, customers or operations. Your title and notes are not scored. If you open research later, up to 18 topic words may be sent to OpenAlex; your title and full notes are not.
          </p>
          <div aria-live="polite" className="min-h-6 mt-3 text-sm">
            {error && <p role="alert" className="text-critical-text">{error}</p>}
          </div>
          <button type="submit" disabled={busy} className={`mt-4 ${primary}`}>{busy ? "Comparing historical data…" : "Save historical comparison"}</button>
        </form>
      )}
      </motion.div>

      {index > 0 && (
        <button type="button" onClick={() => { setError(null); setIndex(index - 1); }} className="mt-10 block text-sm text-muted underline-offset-4 hover:underline">
          ← Back
        </button>
      )}
      </div>
    </main>
  );
}
