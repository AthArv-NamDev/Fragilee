// Everything the landing page states as a fact lives here, and backend/tests/test_landing_facts.py checks it against the real data.
// The page deliberately says nothing about where the data comes from, how old it is or how big it is.

export const STATS = [
  { value: "144", label: "industries understood" },
  { value: "5", label: "industries per idea" },
  { value: "Private", label: "visible only to you" },
];

/** Industry tags, most common first. All of them are tags the model understands. */
export const TAGS = ["Software", "Biotechnology", "Mobile", "Curated Web", "E-Commerce", "Enterprise Software", "Advertising", "Social Media", "Health Care", "Games", "Internet", "Finance", "Analytics", "Technology", "Hardware + Software", "Security", "Clean Technology", "Services", "Semiconductors", "Web Hosting", "Health and Wellness", "SaaS", "Networking", "Video", "Social Network Media", "Apps", "Search", "Cloud Computing", "Education", "Manufacturing", "Messaging", "Music", "Travel", "Sales and Marketing", "News", "Medical", "Web Development", "Entertainment", "Telecommunications", "Media", "Fashion", "iPhone", "Information Technology", "Business Services", "Consulting", "Android", "Photography", "Design"];

/** Share of startups that closed, for industries with plenty of data behind them. low < high in every pair. */
export const PAIRS = [
 {
  "low": "Enterprise Software",
  "lowPct": 22,
  "high": "Social Media",
  "highPct": 57
 },
 {
  "low": "Biotechnology",
  "lowPct": 24,
  "high": "Music",
  "highPct": 58
 },
 {
  "low": "Security",
  "lowPct": 21,
  "high": "Internet",
  "highPct": 50
 }
];

export const EXTREMES = {"low": {"tag": "Security", "pct": 21}, "high": {"tag": "Services", "pct": 59}, "gap": 38};

export const FACTS = [
  ...PAIRS.map((p, i) => ({ big: `${p.lowPct}% vs ${p.highPct}%`, text: `closed: ${p.low.toLowerCase()} versus ${p.high.toLowerCase()}. ${["Same data, very different odds.", "Industry changes the picture.", "Where you play matters."][i]}` })),
  { big: `${EXTREMES.low.pct}%`, text: `closed in ${EXTREMES.low.tag.toLowerCase()}, the lowest of the industries with plenty of data.` },
  { big: `${EXTREMES.high.pct}%`, text: `closed in ${EXTREMES.high.tag.toLowerCase()}, the highest of those industries.` },
  { big: `${EXTREMES.gap} points`, text: "separate the lowest and the highest industry." },
];

export const FAQS = [
 {
  "q": "What exactly is Fragilee?",
  "a": "A decision-support tool for early-stage founders. It shows how a historical model used place and industry inputs, while research and company cases are presented separately. It does not forecast an individual startup's future."
 },
 {
  "q": "Can I trust the result?",
  "a": "Use it as an exploratory historical comparison, not an individual startup forecast. The training records have outcome and timing limitations, and shared tags do not guarantee that a company case is directly comparable. Read the methodology and open the linked sources."
 },
 {
  "q": "Will it tell me my startup will fail?",
  "a": "No. It summarizes patterns in historical company records and shows model feature contributions. Those patterns do not establish what will happen to your startup."
 },
 {
  "q": "Where do the failure stories come from?",
  "a": "From a curated library of real startups that closed. Each summary is written from reputable news and industry sources, and every story links to them so you can read the full account."
 },
 {
  "q": "What happens to what I write about my startup?",
  "a": "Your saved analysis and notes are scoped to your account. Notes do not change the historical model output. If you open research, the backend sends up to 18 extracted topic words from selected notes to OpenAlex; it excludes your startup title and full note text."
 },
 {
  "q": "How much does it cost?",
  "a": "Nothing during the beta. No card needed."
 },
 {
  "q": "What is Level 2?",
  "a": "Level 2 uses historical funding, company relationships, category and state fields. The fuller workflow is not yet available in the current idea form."
 },
 {
  "q": "Who built this?",
  "a": "A student, as a final-year project. It is real software with real tests, and it is still growing."
 }
];
