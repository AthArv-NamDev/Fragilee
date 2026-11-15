import Link from "next/link";
import { redirect } from "next/navigation";
import AnalysisList from "@/components/AnalysisList";
import { serverApi } from "@/lib/api-server";
import type { AnalysisSummary } from "@/lib/types";

const PAGE_SIZE = 50;

export default async function DashboardPage() {
  const result = await serverApi<AnalysisSummary[]>(`/v1/analyses?limit=${PAGE_SIZE}`);
  if (!result.ok && result.status === 401) redirect("/login?next=%2Fdashboard");

  return <main className="mx-auto w-full max-w-[1440px] px-4 pb-24 pt-7 md:px-8 md:pt-10 xl:px-12">
    <section className="relative mb-8 overflow-hidden rounded-[28px] border border-ink/10 bg-dark-surface p-6 md:p-10">
      <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-24 size-72 rounded-full bg-coral/10 blur-3xl"/>
      <div className="relative flex flex-wrap items-end justify-between gap-6">
        <div><p className="eyebrow text-coral">Fragilee / dashboard</p><h1 className="editorial-title mt-3 max-w-4xl font-display">Welcome <span className="text-coral">back.</span></h1><p className="mt-4 max-w-2xl text-sm text-muted">Your saved startup reads, model traces and source trails live here.</p></div>
        <Link href="/new" className="inline-flex min-h-12 items-center gap-2 rounded-full bg-sage px-6 text-sm font-semibold text-[var(--sage-ink)] transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral">Test a new idea <span aria-hidden="true">↗</span></Link>
      </div>
    </section>

    {!result.ok ? <section role="alert" className="rounded-2xl border border-ink/10 bg-dark-surface p-6 md:p-8">
      <p className="eyebrow text-coral">Saved reads unavailable</p><h2 className="mt-2 font-display text-2xl">We couldn&apos;t reach your analyses.</h2>
      <p className="mt-2 max-w-2xl text-sm text-muted">{result.status === 0 ? "The analysis API is not reachable. Start the backend and refresh this page." : `The API answered ${result.status}. Your records have not been changed.`}</p>
      <Link href="/dashboard" className="mt-5 inline-flex min-h-11 items-center rounded-full border border-ink/20 px-5 text-sm font-semibold hover:border-coral">Try again</Link>
    </section> : <>
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3"><div><p className="eyebrow text-lime">Your work</p><h2 className="mt-2 font-display text-2xl md:text-3xl">Saved startup reads</h2></div><Link href="/history" className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-muted underline decoration-coral/60 underline-offset-4 hover:text-text">Full history <span aria-hidden="true">→</span></Link></div>
      {result.data.length === 0 ? <section className="analysis-grid-bg rounded-[24px] border border-dashed border-ink/20 bg-dark-surface p-8 text-center md:p-12">
        <span aria-hidden="true" className="mx-auto grid size-16 place-items-center rounded-full border border-coral/40 bg-coral-soft font-display text-2xl text-coral">F.</span>
        <h2 className="mt-5 font-display text-3xl">Your startup journey starts here.</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-muted">Create your first analysis to explore historical patterns and identify assumptions worth validating.</p>
        <Link href="/new" className="mt-6 inline-flex min-h-12 items-center gap-2 rounded-full bg-sage px-6 text-sm font-semibold text-[var(--sage-ink)]">Test your idea <span aria-hidden="true">↗</span></Link>
      </section> : <AnalysisList items={result.data}/>}
      {result.data.length >= PAGE_SIZE && <p className="mt-4 text-xs text-muted">Showing your latest {PAGE_SIZE} saved analyses. Open full history for search and filters.</p>}
    </>}
  </main>;
}
