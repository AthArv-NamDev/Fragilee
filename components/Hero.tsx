import Link from "next/link";
import ClockDial from "./landing/ClockDial";

const button = "inline-flex min-h-11 min-w-40 items-center justify-center rounded-full px-7 py-3 font-semibold transition-transform hover:-translate-y-px focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-violet";

// Keep the landing page focused on the product's one core action.
export default function Hero() {
  return (
    <section className="flex min-h-[calc(100svh-5rem)] flex-col items-center justify-center bg-dark-bg px-6 py-16 text-center">
      <p className="font-hero text-sm font-extrabold uppercase tracking-[0.18em] text-coral">Fragilee · startup stress test</p>
      <h1 className="mt-5 font-hero text-[clamp(3rem,9vw,6rem)] font-black uppercase leading-[.92] tracking-tight text-ink">Let&apos;s roll.</h1>
      <ClockDial className="mx-auto mt-8 size-48 md:size-64 drop-shadow-xl" />
      <p className="mx-auto mt-8 max-w-xl text-lg text-ink/70 md:text-xl">
        Still think your idea is bulletproof? <strong className="text-ink">Test it against the cracks.</strong>
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-3">
        <Link href="/new" className={`${button} bg-text button-label-on-text`}>Test my idea <span aria-hidden="true" className="ml-2">→</span></Link>
        <Link href="/login?mode=signup" className={`${button} border border-ink/25 text-text hover:bg-ink/5`}>Sign up</Link>
      </div>
      <p className="mt-5 text-xs text-ink/55">Free during beta · Private to you · Historical patterns, not predictions.</p>
    </section>
  );
}
