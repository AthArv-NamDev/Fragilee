"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";

// Wipes every analysis you have saved. Two steps, because it cannot be undone.
export default function DeleteAllButton() {
  const router = useRouter();
  const [step, setStep] = useState<"idle" | "ask" | "busy" | "done">("idle");
  const [count, setCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setStep("busy");
    setError(null);
    try {
      const r = await apiFetch<{ deleted: number }>("/v1/analyses", { method: "DELETE" });
      setCount(r.deleted);
      setStep("done");
      router.refresh();
    } catch {
      setError("Could not delete. Try again in a moment.");
      setStep("ask");
    }
  }
  return (
    <div>
      {step === "idle" && <button type="button" onClick={() => setStep("ask")} className="rounded-full border border-critical-text/60 text-critical-text px-5 py-2 text-sm">Delete all my analyses</button>}
      {(step === "ask" || step === "busy") && (
        <div role="group" aria-label="Confirm deleting all analyses" className="flex flex-wrap items-center gap-3 text-sm">
          <span className="text-muted">Delete everything for good?</span>
          <button type="button" onClick={run} disabled={step === "busy"} className="min-h-11 rounded-full bg-critical px-5 py-2 text-critical-ink disabled:opacity-50">{step === "busy" ? "Deleting…" : "Yes, delete all"}</button>
          <button type="button" onClick={() => setStep("idle")} disabled={step === "busy"} className="text-muted underline underline-offset-4">Cancel</button>
        </div>
      )}
      {step === "done" && <p role="status" className="text-sm text-lime">Deleted {count} {count === 1 ? "analysis" : "analyses"}.</p>}
      {error && <p role="alert" className="mt-2 text-sm text-critical-text">{error}</p>}
    </div>
  );
}
