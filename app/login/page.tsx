"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

type Mode = "signin" | "signup";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    setNotice(null);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    if (mode === "signup" && password.length < 8) {
      setError("Use at least 8 characters for your password.");
      return;
    }
    setBusy(true);
    try {
      const supabase = createClient();
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        router.push("/dashboard");
        router.refresh();
      } else {
        const { data, error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        if (data.session) {
          router.push("/dashboard");
          router.refresh();
        } else {
          setNotice("Check your email and click the link to confirm your account, then sign in.");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const tab = (m: Mode) =>
    `flex-1 py-2.5 rounded-full text-sm font-medium ${mode === m ? "bg-sage text-charcoal" : "text-muted"}`;
  const field =
    "w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-text outline-none focus:border-sage";

  return (
    <main className="min-h-screen flex items-center justify-center bg-dark-surface px-6">
      <div className="w-full max-w-sm">
        <div className="flex bg-white/5 rounded-full p-1 mb-9">
          <button type="button" onClick={() => switchMode("signin")} aria-pressed={mode === "signin"} className={tab("signin")}>
            Sign in
          </button>
          <button type="button" onClick={() => switchMode("signup")} aria-pressed={mode === "signup"} className={tab("signup")}>
            Sign up
          </button>
        </div>

        <h1 className="font-display text-3xl text-text mb-1">
          {mode === "signin" ? "Welcome back" : "Create your account"}
        </h1>
        <p className="text-muted text-sm mb-8">
          {mode === "signin" ? "Log in to see your saved analyses." : "Save your analyses and sharpen them over time."}
        </p>

        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <label htmlFor="email" className="block text-muted text-sm mb-2">Email</label>
            <input id="email" type="email" required autoComplete="email" placeholder="you@example.com"
              value={email} onChange={(e) => setEmail(e.target.value)} className={field} />
          </div>
          <div>
            <label htmlFor="password" className="block text-muted text-sm mb-2">Password</label>
            <input id="password" type="password" required minLength={mode === "signup" ? 8 : undefined}
              autoComplete={mode === "signin" ? "current-password" : "new-password"} placeholder="••••••••"
              value={password} onChange={(e) => setPassword(e.target.value)} className={field} />
          </div>

          <div aria-live="polite" className="min-h-5 text-sm">
            {error && <p className="text-critical-text" role="alert">{error}</p>}
            {notice && <p className="text-low">{notice}</p>}
          </div>

          <button type="submit" disabled={busy}
            className="w-full bg-sage text-charcoal font-semibold py-3 rounded-full disabled:opacity-60">
            {busy ? "One moment…" : mode === "signin" ? "Sign in" : "Sign up"}
          </button>
        </form>
      </div>
    </main>
  );
}
