"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import Wordmark from "@/components/Wordmark";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void createClient().auth.getUser().then(({ data, error: authError }) => {
      if (!active) return;
      setReady(Boolean(data.user) && !authError);
      if (!data.user || authError) setError("This password reset link is invalid or expired. Request a new one from sign in.");
    }).catch(() => {
      if (active) setError("We couldn't verify this reset link. Request a new one from sign in.");
    });
    return () => { active = false; };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (password.length < 8) {
      setError("Use at least 8 characters for your password.");
      return;
    }
    if (password !== confirm) {
      setError("Those passwords don't match. Check them and try again.");
      return;
    }
    setBusy(true);
    try {
      const { error: updateError } = await createClient().auth.updateUser({ password });
      if (updateError) throw updateError;
      setNotice("Your password has been updated. You can continue to your account.");
      setPassword("");
      setConfirm("");
    } catch (err) {
      const message = err instanceof Error ? err.message : "We couldn't update your password. Request a new reset link and try again.";
      setError(/rate limit|too many requests/i.test(message) ? "Too many attempts were made. Wait a few minutes, then try again." : message);
    } finally {
      setBusy(false);
    }
  }

  const field = "min-h-14 w-full rounded-[14px] border-[1.5px] border-ink/20 bg-dark-surface px-[18px] text-base text-text outline-none transition-colors placeholder:text-muted focus:border-sage focus-visible:outline-2 focus-visible:outline-sage";

  return <main className="flex min-h-screen flex-col bg-dark-bg px-5 py-5 sm:px-8">
    <header><Link href="/" aria-label="Fragilee home"><Wordmark /></Link></header>
    <section className="flex flex-1 items-center justify-center py-10">
      <div className="w-full max-w-[420px]">
        <p className="eyebrow mb-3 text-violet-text">Account recovery</p>
        <h1 className="font-display text-3xl text-text">Set a new password</h1>
        <p className="mb-7 mt-2 text-sm text-muted">Choose a new password to secure your Fragilee account.</p>
        {ready ? <form onSubmit={submit} className="space-y-5">
          <div><label htmlFor="new-password" className="mb-2 block text-sm text-muted">New password</label><input id="new-password" type="password" autoComplete="new-password" minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} className={field} /></div>
          <div><label htmlFor="confirm-password" className="mb-2 block text-sm text-muted">Confirm new password</label><input id="confirm-password" type="password" autoComplete="new-password" minLength={8} required value={confirm} onChange={(event) => setConfirm(event.target.value)} className={field} /></div>
          <div aria-live="polite" className="text-sm">{error && <p role="alert" className="text-critical-text">{error}</p>}{notice && <p role="status" className="text-low">{notice}</p>}</div>
          <button type="submit" disabled={busy} className="min-h-12 w-full rounded-full bg-sage px-6 font-semibold button-label-on-sage focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet disabled:opacity-60">{busy ? "Updating…" : "Update password"}</button>
          {notice && <button type="button" onClick={() => router.replace("/dashboard")} className="min-h-11 w-full text-sm font-medium text-violet-text underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-violet">Continue to Fragilee</button>}
        </form> : <div aria-live="polite" className="space-y-5"><p role={error ? "alert" : "status"} className={error ? "text-sm text-critical-text" : "text-sm text-muted"}>{error ?? "Verifying your reset link…"}</p><Link href="/login" className="inline-flex min-h-11 items-center text-sm font-medium text-violet-text underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-violet">Back to sign in</Link></div>}
      </div>
    </section>
  </main>;
}
