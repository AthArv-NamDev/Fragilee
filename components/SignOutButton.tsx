"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function SignOutButton() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function signOut() {
    if (busy) return;
    setBusy(true);
    setError(null);
    const { error: signOutError } = await createClient().auth.signOut();
    if (signOutError) {
      setError("Could not sign out. Try again.");
      setBusy(false);
      return;
    }
    router.replace("/login");
    router.refresh();
  }
  return (
    <div className="flex flex-col items-end">
      <button type="button" onClick={signOut} disabled={busy} aria-busy={busy} className="min-h-11 rounded-full border border-ink/20 px-4 text-sm font-semibold text-text transition-colors hover:border-violet focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet disabled:cursor-wait disabled:opacity-70">
        {busy ? "Signing out…" : "Sign out"}
      </button>
      {error && <span role="alert" className="mt-1 text-[11px] text-critical-text">{error}</span>}
    </div>
  );
}
