import Link from "next/link";
import Nav from "@/components/Nav";
import Wave from "@/components/landing/Wave";
import Reveal from "@/components/landing/Reveal";
import Laurel from "@/components/landing/Laurel";
import TreePreview from "@/components/landing/TreePreview";
import LetterFlicker from "@/components/landing/LetterFlicker";
import Faq from "@/components/landing/Faq";
import { IconCracks, IconRanks, IconMoves, IconLevel } from "@/components/landing/Art";
import { STATS, FAQS } from "@/lib/landing-data";
import FragileeHeroScene from "@/components/landing/FragileeHeroScene";
import Marquee from "@/components/landing/Marquee";
import StartupPathways from "@/components/landing/StartupPathways";

const ink = "inline-flex min-h-11 items-center rounded-full bg-text button-label-on-text font-hero font-semibold px-7 py-3 hover:-translate-y-0.5 transition-transform focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-violet";
const outline = "inline-flex min-h-11 items-center rounded-full border border-ink/25 text-text font-semibold px-7 py-3 hover:bg-ink/5 transition-colors focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-violet";
const eyebrow = "font-hero font-extrabold uppercase tracking-wide text-sm";
const h2 = "font-hero font-black uppercase leading-[.95] tracking-tight";

export default function Home() {
  return (
    <main>
      <Nav />
      <section className="relative isolate overflow-hidden bg-dark-bg px-4 pb-12 pt-8 text-text md:px-8 md:pb-16 md:pt-12 xl:px-12">
        <div aria-hidden="true" className="pointer-events-none absolute -right-20 top-10 -z-0 size-[520px] rounded-full bg-coral/10 blur-[110px]"/>
        <div className="relative z-10 mx-auto grid min-h-[calc(100svh-5rem)] max-w-[1440px] items-center gap-3 lg:grid-cols-[minmax(0,1.12fr)_minmax(390px,.88fr)] xl:gap-12">
          <Reveal y={18} className="relative z-10 py-8 md:py-12">
            <h1 className="editorial-title max-w-[850px] font-display uppercase">
              Understand where it <span className="text-coral">breaks.</span>
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-relaxed text-muted md:text-lg">Explore what historical startup models use, inspect source-linked research and company stories, and decide what to validate next. Fragilee is a lens on the past, not a forecast for your idea.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/new" className="inline-flex min-h-12 items-center gap-3 rounded-full bg-sage px-6 text-sm font-semibold button-label-on-sage transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral">Explore your startup <span aria-hidden="true">↗</span></Link>
              <Link href="#how" className="inline-flex min-h-12 items-center gap-3 rounded-full border border-ink/25 px-6 text-sm font-semibold text-text transition-colors hover:border-coral hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral">How it works <span aria-hidden="true">↓</span></Link>
            </div>
            <p className="mt-5 text-xs text-muted">Free during beta · Level 1 model uses place and industry · Notes stay separate</p>
          </Reveal>
          <Reveal delay={.12} y={10} className="relative z-0 mx-auto w-full max-w-[620px] lg:max-w-none">
            <FragileeHeroScene/>
          </Reveal>
        </div>
        <div aria-label="Product capabilities" className="relative z-10 mx-auto mt-2 max-w-[1440px] overflow-hidden border-y border-ink/10 py-4">
          <Marquee seconds={38}>
            {["Historical model trace", "Research-linked insights", "Curated company cases", "Source-linked evidence", "Founder notes kept separate"].map((item, index) => <span key={item} className="flex items-center gap-3 whitespace-nowrap px-3 font-display text-sm uppercase tracking-wide text-muted md:text-base"><i aria-hidden="true" className={`size-2 rounded-full ${index % 2 ? "bg-coral" : "bg-lime"}`}/>{item}</span>)}
          </Marquee>
        </div>
      </section>
      {/* proof in numbers + a look at the tree */}
      <section id="data" className="relative z-10 scroll-mt-20 bg-dark-bg text-text [border-radius:50%_50%_0_0/90px_90px_0_0] pt-24 pb-20 px-6 md:px-14">
        <Reveal>
          <dl className="mx-auto max-w-4xl grid sm:grid-cols-3 gap-10">
            {STATS.map((s) => (
              <div key={s.value}><Laurel><dt className="font-hero text-4xl md:text-5xl">{s.value}</dt><dd className="text-xs md:text-sm text-muted max-w-[11rem] mx-auto">{s.label}</dd></Laurel></div>
            ))}
          </dl>
        </Reveal>
        <Reveal className="mx-auto mt-16 max-w-5xl">
          <div className="relative overflow-hidden rounded-[24px] border border-ink/10 bg-dark-surface text-text px-6 pt-8 pb-10 text-center">
            <TreePreview className="mx-auto w-full max-w-xl" />
            <h2 className={`${h2} text-[clamp(2.8rem,10vw,8.5rem)] -mt-2`}>See the tree.</h2>
            <p className="mx-auto mt-3 max-w-md text-muted text-sm md:text-base">Every result unfolds into branches: what the historical model used and how each input contributed to its score.</p>
          </div>
        </Reveal>
        <div className="mt-10 text-center"><p className="mb-3 text-sm text-muted">Curious what yours looks like?</p><Link href="/new" className={ink}>Grow my tree</Link></div>
      </section>

      {/* the story card + big call to action */}
      <section className="relative z-10 bg-dark-bg text-text px-6 md:px-14 pb-24">
        <Reveal className="mx-auto max-w-3xl">
          <div className="relative h-[420px] md:h-[460px] rounded-[24px] border border-ink/10 bg-violet/10 overflow-visible">
            <div className="absolute inset-x-0 bottom-0 flex justify-start pl-6 md:pl-14 overflow-hidden rounded-b-[24px] h-full items-end"><StartupPathways className="h-[62%] md:h-[78%] w-auto translate-y-6" /></div>
            <figure className="absolute -right-3 md:-right-16 top-8 w-[62%] md:w-[52%] rounded-[16px] border border-ink/10 bg-sand p-5 md:p-7">
              <figcaption className="font-hero text-ink text-xl md:text-2xl leading-tight">Every startup has a story.</figcaption>
              <p className="mt-2 text-xs md:text-sm text-ink/75">A structured read can help you decide which assumptions to validate next.</p>
            </figure>
          </div>
        </Reveal>
        <Reveal className="mx-auto mt-16 max-w-2xl text-center">
          <p className={eyebrow}>Discover what is missing in your startup</p>
          <h2 className={`${h2} mt-3 text-4xl md:text-6xl`}>Let&apos;s test it today.</h2>
          <p className="mt-4 text-muted">See which historical inputs are represented, what external research may be relevant, and what remains unknown.</p>
          <div className="mt-7 flex flex-wrap justify-center gap-3"><Link href="/new" className={ink}>Test my idea</Link><a href="#how" className={outline}>How does it work?</a></div>
        </Reveal>
      </section>

      <Wave color="var(--color-dark-surface)" className="relative z-10 -mb-px bg-dark-bg" />
      {/* why it matters */}
      <section id="how" className="relative z-10 scroll-mt-20 bg-dark-surface text-text px-6 md:px-14 py-24">
        <div className="mx-auto max-w-6xl grid md:grid-cols-2 gap-10 md:gap-16 items-center">
          <Reveal><div className="relative overflow-hidden rounded-[2rem] border-2 border-paper/30 aspect-[4/4.2] max-w-md mx-auto"><StartupPathways className="h-full w-full" /></div></Reveal>
          <Reveal delay={0.1}>
            <p className={`${eyebrow} text-coral`}>Know early. <span className="text-text">Decide better.</span></p>
            <h2 className={`${h2} mt-4 text-[clamp(2.2rem,5vw,4.2rem)]`}><LetterFlicker text="BUILD BEYOND HOPE." startAfter={2200} every={3200} /></h2>
            <p className="mt-6 text-muted text-base md:text-lg max-w-md">A structured read can make assumptions easier to discuss with your team, customers and investors. <b className="text-text">Build a sharper next question.</b></p>
          </Reveal>
        </div>
        <div className="mx-auto mt-24 max-w-6xl grid md:grid-cols-3 gap-12 md:gap-6 items-start">
          {[
            { icon: <IconCracks />, a: "Inputs", b: "Shown", c: "text-coral", d: "See which place and industry fields the historical model used for this read.", off: "" },
            { icon: <IconRanks />, a: "Model", b: "Traced", c: "text-lime", d: "Inspect feature contributions as model behavior, not as proven causes.", off: "md:mt-16" },
            { icon: <IconMoves />, a: "Research", b: "Linked", c: "text-rose", d: "Review source-linked studies separately from historical model output.", off: "md:mt-32" },
          ].map((t, i) => (
            <Reveal key={t.a} delay={i * 0.12} className={t.off}>
              {t.icon}
              <h3 className="mt-5 font-hero text-3xl">{t.a} <span className={t.c}>{t.b}</span></h3>
              <p className="mt-2 text-sm text-muted max-w-[16rem]">{t.d}</p>
            </Reveal>
          ))}
        </div>
      </section>

      <Wave color="var(--color-sand)" className="relative z-10 -mb-px bg-dark-surface" />
      {/* levels */}
      <section id="levels" className="relative z-10 scroll-mt-20 bg-sand text-ink px-6 md:px-14 py-24">
        <Reveal className="mx-auto max-w-6xl">
          <h2 className={`${h2} text-4xl md:text-6xl`}>Your next move</h2>
          <p className="mt-3 max-w-md text-ink/70">Start where you are. <b className="text-ink">Go deeper when you can.</b></p>
        </Reveal>
        <div className="mx-auto mt-12 max-w-6xl grid md:grid-cols-3 gap-6 items-start">
          {[
            { n: "1", a: "Start", b: "Smart", c: "text-lime", tag: "Open now", d: "Name it, describe it, pick where it lives and what it does. Your first read lands in minutes.", off: "" },
              { n: "2", a: "More", b: "Company data", c: "text-coral", tag: "Coming soon", d: "A fuller historical input form is not yet available. Existing model outputs still have important timing and cohort limits.", off: "md:mt-10" },
              { n: "3", a: "Review", b: "Evidence", c: "text-rose", tag: "Available in results", d: "Open academic research and historical company sources separately from the model trace.", off: "md:mt-20" },
          ].map((l, i) => (
            <Reveal key={l.n} delay={i * 0.12} className={l.off}>
              <div className="rounded-[24px] border border-ink/10 bg-dark-surface text-text p-6 pb-8">
                <span className="inline-block rounded-full bg-ink/5 px-3 py-1 text-xs font-semibold text-muted">{l.tag}</span>
                <div className="my-6"><IconLevel n={l.n} /></div>
                <h3 className="font-hero font-black text-3xl">{l.a} <span className={l.c}>{l.b}</span></h3>
                <p className="mt-2 text-sm text-muted">{l.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <Wave color="var(--color-sand)" className="relative z-10 -mb-px bg-sand" />
      {/* what it looks at: bento */}
      <section id="research" className="relative z-10 scroll-mt-24 bg-dark-bg text-text px-6 md:px-14 py-24">
        <Reveal className="mx-auto max-w-3xl text-center">
          <p className={eyebrow}>How, you ask?</p>
          <h2 className={`${h2} mt-3 text-4xl md:text-6xl`}>We study the patterns. So you don&apos;t have to.</h2>
        </Reveal>
        <Reveal className="mx-auto mt-12 max-w-6xl">
          <div className="grid md:grid-cols-3 md:grid-rows-2 gap-3 rounded-[24px] border border-ink/10 bg-dark-surface p-3 text-text">
            <div className="md:row-span-2 md:col-span-1 rounded-2xl bg-ink/5 p-6 flex flex-col justify-between min-h-[320px]">
              <TreePreview className="w-full" /><div><h3 className="font-hero text-2xl">The model trace</h3><p className="text-sm text-muted mt-1">Level 1 uses place and industry. Level 2 adds historical funding and company fields. Notes remain separate.</p></div>
            </div>
            {[
              { t: "Place", d: "Where the startup is located. The Level 1 model uses country and, in the US, state." },
              { t: "Industry", d: "Select up to five labels from the historical model's supported list." },
              { t: "Company cases", d: "Curated source-linked examples. A shared tag alone does not prove a direct comparison." },
              { t: "Your notes", d: "Saved with your analysis. Notes do not change the model; extracted topic words may inform research queries." },
            ].map((b) => (
              <div key={b.t} className="rounded-2xl border border-ink/10 bg-ink/5 p-6 min-h-[150px] flex flex-col justify-end hover:-translate-y-1 transition-transform"><h3 className="font-hero text-2xl">{b.t}</h3><p className="text-sm text-muted mt-1">{b.d}</p></div>
            ))}
          </div>
        </Reveal>
      </section>

      <Wave color="var(--color-sand)" className="relative z-10 -mb-px bg-dark-bg" />

      {/* FAQ */}
      <section id="faq" className="relative z-10 scroll-mt-20 bg-sand text-ink px-6 md:px-14 py-24">
        <Reveal className="mx-auto max-w-6xl text-center"><p className={eyebrow}>Got questions?</p><h2 className={`${h2} mt-3 text-4xl md:text-6xl`}>Frequently asked questions</h2></Reveal>
        <div className="mx-auto mt-12 max-w-6xl"><Faq items={FAQS} /></div>
      </section>

      <footer className="bg-dark-surface text-muted px-6 md:px-14 py-8 text-xs md:text-sm flex flex-wrap items-center justify-between gap-4">
        <span>Fragilee · a final-year project. Patterns, not predictions. Not financial advice.</span>
        <span className="flex gap-6"><Link href="/login" className="hover:text-text">Sign in</Link><Link href="/login?mode=signup" className="hover:text-text">Sign up</Link><a href="#faq" className="hover:text-text">FAQ</a></span>
      </footer>
    </main>
  );
}
