import Link from "next/link";
import AnalysisList from "@/components/AnalysisList";
import { serverApi } from "@/lib/api-server";
import type { AnalysisSummary } from "@/lib/types";

const PAGE = 50;

export default async function HistoryPage() {
  const res = await serverApi<AnalysisSummary[]>(`/v1/analyses?limit=${PAGE}`);
  return (
    <main className="mx-auto w-full max-w-[1440px] px-4 pb-24 pt-7 md:px-8 md:pt-10 xl:px-12">
      <div className="relative mb-8 overflow-hidden rounded-[26px] border border-ink/10 bg-dark-surface p-6 md:p-9">
        <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-24 size-64 rounded-full bg-coral/10 blur-3xl"/>
        <div className="relative flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="eyebrow text-coral">Your Fragilee workspace</p>
          <h1 className="editorial-title mt-3 max-w-3xl font-display">Saved <span className="text-coral">thinking.</span></h1>
          <p className="mt-4 max-w-[60ch] text-sm text-muted">Revisit a saved startup read, inspect its model trace, and follow the research and case sources.</p>
        </div>
        <Link href="/new" className="inline-flex min-h-12 items-center gap-2 rounded-full bg-sage px-6 text-sm font-semibold text-[var(--sage-ink)] transition-transform hover:-translate-y-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet">Start a new read <span aria-hidden="true">↗</span></Link>
        </div>
      </div>
      {res.ok ? (
        <>
          <AnalysisList items={res.data} />
          {res.data.length >= PAGE && <p className="text-sm text-muted mt-4">Showing your latest {PAGE}.</p>}
        </>
      ) : (
        <div className="rounded-2xl border border-ink/10 bg-dark-surface p-6" role="alert">
          <h2 className="font-display text-xl mb-2">We could not load your history</h2>
          <p className="text-muted text-sm">{res.status === 0 ? "The API is not reachable. Is it running on port 8000?" : `The API answered ${res.status}. Reload the page, or sign out and in again.`}</p>
        </div>
      )}
    </main>
  );
}
