export default function AnalysisLoading() {
  return <main className="mx-auto w-full max-w-[1440px] px-4 pb-24 pt-6 md:px-8 md:pt-10 xl:px-12">
    <section className="rounded-[24px] border border-ink/10 bg-dark-surface p-6 md:p-8" aria-busy="true" aria-live="polite">
      <p className="eyebrow text-coral">Saved analysis</p>
      <h1 className="mt-2 font-display text-3xl">Loading your report</h1>
      <p className="mt-3 text-sm text-muted">Loading founder information, historical context, and startup diagnostics.</p>
      <div className="mt-6 space-y-3" aria-hidden="true">
        <div className="h-4 w-2/3 animate-pulse rounded bg-ink/10 motion-reduce:animate-none" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-ink/10 motion-reduce:animate-none" />
        <div className="h-24 animate-pulse rounded-2xl bg-ink/5 motion-reduce:animate-none" />
      </div>
    </section>
  </main>;
}
