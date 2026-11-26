import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import AnalysisView from "@/components/AnalysisView";
import { serverApi } from "@/lib/api-server";
import type { Analysis, CasesResponse } from "@/lib/types";

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const res = await serverApi<Analysis>(`/v1/analyses/${encodeURIComponent(id)}`);
  if (!res.ok) {
    if (res.status === 401) redirect("/login");
    if (res.status === 404 || res.status === 422) notFound(); // someone else's analysis also looks like "not found"
    return (
      <main className="mx-auto flex min-h-[65vh] w-full max-w-4xl items-center px-4 py-12 md:px-8">
        <section className="w-full rounded-[26px] border border-ink/10 bg-dark-surface p-7 md:p-10" role="alert">
          <p className="eyebrow text-coral">Analysis unavailable</p>
          <h1 className="mt-3 font-display text-3xl md:text-4xl">This read did not load.</h1>
          <p className="mt-3 max-w-xl text-sm text-muted">
            {res.status === 0 ? "The API could not be reached. Check that the backend is running, then try your history again." : `The API answered ${res.status}. Your saved history has not been changed.`}
          </p>
          <Link href="/history" className="mt-6 inline-flex min-h-11 items-center rounded-full bg-sage px-5 text-sm font-semibold button-label-on-sage">Back to saved analyses</Link>
        </section>
      </main>
    );
  }
  const cases = await serverApi<CasesResponse>(`/v1/analyses/${encodeURIComponent(id)}/cases`);   // a missing library must never break the tree
  return <AnalysisView analysis={res.data} cases={cases.ok ? cases.data : null} />;
}
