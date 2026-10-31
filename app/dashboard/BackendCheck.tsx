"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";

// Temporary: proves the API accepts your Supabase login. Replaced by the real dashboard list.
export default function BackendCheck() {
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function check() {
    setBusy(true);
    setMsg(null);
    try {
      const rows = await apiFetch<unknown[]>("/v1/analyses");
      setMsg({ ok: true, text: `The API accepted your login. Saved analyses found: ${rows.length}.` });
    } catch (err) {
      if (err instanceof ApiError) {
        setMsg({ ok: false, text: `The API answered ${err.status}: ${err.message}` });
      } else {
        setMsg({ ok: false, text: "Could not reach the API. Is it running on port 8000, and does its ALLOWED_ORIGINS include http://localhost:3000?" });
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-8">
      <button onClick={check} disabled={busy} className="bg-sage text-charcoal font-semibold px-6 py-3 rounded-full disabled:opacity-60">
        {busy ? "Checking…" : "Test the API connection"}
      </button>
      <p aria-live="polite" className={`mt-4 text-sm ${msg?.ok ? "text-low" : "text-critical-text"}`}>{msg?.text}</p>
    </div>
  );
}
