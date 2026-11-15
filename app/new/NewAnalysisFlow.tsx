"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "motion/react";
import { apiFetch, ApiError } from "@/lib/api";
import { COUNTRY_NAMES, OTHER_COUNTRY, STATE_NAMES, US_STATES } from "@/lib/geo";
import type { Context } from "@/lib/types";

const MAX_TAGS = 5;
const MIN_CONCEPT = 10;
type StepId = "name" | "concept" | "vision" | "details" | "country" | "state" | "tags" | "review";
type Props = { countries: string[]; states: string[]; tags: string[] };

const STAGES: [NonNullable<Context["startup_stage"]>, string][] = [
  ["idea", "Just an idea"], ["prototype", "Prototype"], ["launched", "Launched"], ["earning", "Earning money"],
];

const card = "text-left rounded-2xl border p-5 transition-colors focus-visible:outline-2 focus-visible:outline-white";
const idle = "bg-dark-surface border-ink/10 hover:border-violet";
const chosen = "bg-violet/20 border-violet";
const input = "w-full bg-dark-surface border border-ink/10 rounded-lg px-4 py-3 text-text";
const primary = "min-h-11 rounded-full bg-sage px-8 font-semibold text-[var(--sage-ink)] transition-colors hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet disabled:opacity-50 disabled:cursor-not-allowed";

export default function NewAnalysisFlow({ countries, states, tags }: Props) {
  const router = useRouter();
  const reduce = useReducedMotion();
  const [index, setIndex] = useState(0);
  const [title, setTitle] = useState("");
  const [concept, setConcept] = useState("");
  const [vision, setVision] = useState("");
  const [customer, setCustomer] = useState("");
  const [revenue, setRevenue] = useState("");
  const [stage, setStage] = useState<Context["startup_stage"]>();
  const [team, setTeam] = useState("");
  const [worry, setWorry] = useState("");
  const [country, setCountry] = useState<string | null>(null);
  const [state, setState] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

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
    if (stage) c.startup_stage = stage;
    const n = Number(team);
    if (team.trim() && Number.isInteger(n) && n >= 1 && n <= 500) c.team_size = n;
    if (worry.trim()) c.biggest_worry = worry.trim();
    return c;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!country || picked.length === 0 || !title.trim() || concept.trim().length < MIN_CONCEPT || (country === "USA" && !state)) return;
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
          : err.status === 422 ? "One of your answers was not accepted. Go back and check them."
          : err.status === 503 ? "Saving is unavailable right now. Try again in a moment."
          : err.message,
        );
      } else {
        setError("Could not reach the API. Is it running on port 8000?");
      }
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
          <fieldset>
            <legend className="text-sm text-muted mb-2">Where is it today?</legend>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {STAGES.map(([id, label]) => (
                <button key={id} type="button" aria-pressed={stage === id} onClick={() => setStage(stage === id ? undefined : id)}
                  className={`${card} ${stage === id ? chosen : idle} text-sm`}>{label}</button>
              ))}
            </div>
          </fieldset>
          <div className="grid sm:grid-cols-2 gap-6">
            <div>
              <label htmlFor="team" className="block text-sm text-muted mb-2">How many people are on the team?</label>
              <input id="team" type="number" inputMode="numeric" min={1} max={500} value={team} onChange={(e) => setTeam(e.target.value)} placeholder="e.g. 3" className={input} />
            </div>
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
              ["Notes", [customer, revenue, stage, team && `${team} people`, worry].filter(Boolean).join(" · ") || "None", "details"],
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
