import { connection } from "next/server";
import NewAnalysisFlow from "./NewAnalysisFlow";
import type { Meta } from "@/lib/types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function getMeta(): Promise<Meta | null> {
  try {
    const res = await fetch(`${API_URL}/v1/meta`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as Meta) : null;
  } catch {
    return null;
  }
}

export default async function NewAnalysisPage() {
  await connection(); // always fetch the options at request time, never at build time
  const meta = await getMeta();
  if (!meta) {
    return (
      <main className="min-h-screen px-6 py-10 max-w-xl mx-auto">
        <h1 className="font-display text-3xl mb-3">We could not load the options</h1>
        <p className="text-muted">The API is not reachable. Check that it is running on port 8000, then reload this page.</p>
      </main>
    );
  }
  const { countries, states, tags } = meta.stages.stage1.inputs;
  return <NewAnalysisFlow countries={countries} states={states} tags={tags} />;
}
