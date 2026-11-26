import Link from "next/link";
import Reveal from "@/components/landing/Reveal";

const sections = [
  {
    title: "Historical model trace",
    body: "The stored model was trained on companies with recorded outcomes. Level 1 uses place and selected industry tags. Level 2 uses historical funding, relationship, category and state fields. Its feature contributions show what moved that model's internal score for this record; they do not establish a present-day vulnerability or explain why a company closed.",
  },
  {
    title: "What is unknown",
    body: "Founder notes do not change the historical model output. Missing operating details stay unknown; Fragilee does not infer revenue, demand, retention, margins, team capability or supplier exposure from an industry label.",
  },
  {
    title: "Research evidence",
    body: "Research is fetched separately from OpenAlex when you open a factor. The current retrieval uses query terms, titles, abstracts and source metadata; it has no embedding search or human-reviewed relevance benchmark. Direct evidence means one abstract sentence contains both the field and focus terms. Contextual evidence matches them elsewhere in the paper. Neither proves the finding applies to your company.",
  },
  {
    title: "Historical company cases",
    body: "Cases are a separate curated library with links to reporting. A shared industry or idea term is only a retrieval clue, not proof that two companies are directly comparable. A closure and a reported challenge do not, by themselves, establish a causal failure mechanism.",
  },
];

export default function GuidePage() {
  return (
    <main className="mx-auto w-full max-w-[1200px] px-4 pb-24 pt-7 md:px-8 md:pt-12">
      <div className="relative overflow-hidden rounded-[26px] border border-ink/10 bg-dark-surface p-6 md:p-10">
        <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-24 size-64 rounded-full bg-lime/10 blur-3xl"/>
        <div className="relative max-w-3xl"><p className="eyebrow text-coral">Method / evidence / limits</p>
        <h1 className="editorial-title mt-4 font-display">Read the <span className="text-coral">signals.</span></h1>
        <p className="mt-5 max-w-[62ch] text-sm leading-relaxed text-muted md:text-base">Fragilee is decision support. It should help you ask better questions, not claim to know your startup’s future. These layers remain separate by design.</p></div>
      </div>

      <div className="mt-7 grid gap-4 md:grid-cols-2">
        {sections.map((section, index) => (
          <Reveal key={section.title} delay={index * .07}>
          <section className="analysis-card h-full rounded-[22px] border border-ink/10 bg-dark-surface p-5 md:p-7">
            <div className="flex items-center justify-between gap-3"><p className="eyebrow text-muted">Layer {String(index + 1).padStart(2, "0")}</p><span aria-hidden="true" className="font-display text-3xl text-coral/60">{["◇", "?", "↗", "⌁"][index]}</span></div>
            <h2 className="mt-5 font-display text-2xl">{section.title}</h2>
            <p className="mt-3 text-sm leading-relaxed text-muted">{section.body}</p>
          </section>
          </Reveal>
        ))}
      </div>
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-ink/10 bg-ink/5 p-5">
        <p className="max-w-xl text-sm text-muted">A useful assessment is honest about what it knows and what still needs checking.</p>
        <Link href="/new" className="inline-flex min-h-12 items-center gap-2 rounded-full bg-sage px-6 text-sm font-semibold button-label-on-sage focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet">Test an idea <span aria-hidden="true">↗</span></Link>
      </div>
    </main>
  );
}
