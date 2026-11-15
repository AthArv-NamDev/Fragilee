"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";

// Two steps on purpose: deleting cannot be undone.
export default function DeleteButton({ id, title }: { id: string; title: string }) {
  const router = useRouter();
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch<void>(`/v1/analyses/${id}`, { method: "DELETE" });
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError && err.status === 404 ? "It was already deleted." : "Could not delete it. Try again.");
      setBusy(false);
    }
  }

  if (!asking) {
    return (
      <button type="button" onClick={() => setAsking(true)} aria-label={`Delete ${title}`} className="min-h-11 px-2 text-sm text-muted hover:text-critical-text underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-violet">
        Delete
      </button>
    );
  }
  return (
    <span role="group" aria-label={`Confirm deleting ${title}`} className="flex items-center gap-3 text-sm">
      <span className="text-muted">Delete for good?</span>
      <button type="button" onClick={remove} disabled={busy} className="min-h-11 px-2 text-critical-text underline underline-offset-4 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-violet">
        {busy ? "Deleting…" : "Yes, delete"}
      </button>
      <button type="button" onClick={() => setAsking(false)} disabled={busy} className="min-h-11 px-2 text-muted underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-violet">Cancel</button>
      {error && <span role="alert" className="text-critical-text">{error}</span>}
    </span>
  );
}
