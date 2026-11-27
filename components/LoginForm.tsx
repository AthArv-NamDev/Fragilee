"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { LANDING_AFTER_LOGIN, LANDING_AFTER_SIGNUP } from "@/lib/redirect";
import ThemeSelector from "@/components/ThemeSelector";
import Wordmark from "@/components/Wordmark";
import type { ThemeName } from "@/lib/theme";

export type Mode = "signin" | "signup";

function readableAuthError(error: unknown, mode: Mode) {
  const authError = error as { message?: string; status?: number; name?: string };
  if (
    (error instanceof TypeError && /fetch|network/i.test(error.message)) ||
    authError?.status === 0 ||
    authError?.name === "AuthRetryableFetchError"
  ) {
    return "We couldn't reach the authentication service. Check your connection and try again.";
  }
  const message = authError?.message ?? "";
  if (mode === "signin" && /invalid login credentials/i.test(message)) {
    return "That email and password do not match. Check them and try again.";
  }
  if (authError?.status && authError.status >= 500) {
    return "The authentication service is temporarily unavailable. Please try again shortly.";
  }
  if (/rate limit|too many requests/i.test(message)) {
    return "Too many attempts were made. Wait a few minutes, then try again.";
  }
  if (/email not confirmed/i.test(message)) {
    return "Your email is not confirmed yet. Check your inbox or resend the confirmation email below.";
  }
  if (mode === "signup" && /already registered|user exists/i.test(message)) {
    return "An account may already exist for this email. Try signing in instead.";
  }
  return message || "Something went wrong. Please try again.";
}

export default function LoginForm({ next, initialMode, initialTheme, authError }: { next: string | null; initialMode: Mode; initialTheme: ThemeName; authError?: "confirmation" | "oauth" }) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(authError === "confirmation" ? "That confirmation link is invalid or expired. Sign in or request a new signup email." : authError === "oauth" ? "Google sign-in did not complete. You can try again or use email and password." : null);
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
        router.replace(next ?? LANDING_AFTER_LOGIN);
        router.refresh();
      } else {
        const callback = new URL("/auth/callback", window.location.origin);
        callback.searchParams.set("next", next ?? LANDING_AFTER_SIGNUP);
        const { data, error } = await supabase.auth.signUp({ email, password, options: { emailRedirectTo: callback.toString() } });
        if (error) throw error;
        if (data.session) {
          router.replace(next ?? LANDING_AFTER_SIGNUP);
          router.refresh();
        } else {
          setNotice("If this email can be registered, a confirmation link is on its way. Check your inbox; the link will open Test the Idea.");
        }
      }
    } catch (err) {
      setError(readableAuthError(err, mode));
    } finally {
      setBusy(false);
    }
  }

  function callbackUrl(destination: string) {
    const callback = new URL("/auth/callback", window.location.origin);
    callback.searchParams.set("next", destination);
    return callback.toString();
  }

  async function continueWithGoogle() {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      const { error } = await createClient().auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: callbackUrl(next ?? (mode === "signin" ? LANDING_AFTER_LOGIN : LANDING_AFTER_SIGNUP)) },
      });
      if (error) throw error;
    } catch (err) {
      setError(readableAuthError(err, mode));
      setBusy(false);
    }
  }

  async function resendConfirmation() {
    setError(null);
    setNotice(null);
    if (!email.trim()) {
      setError("Enter your email address first, then request a new confirmation link.");
      document.getElementById("email")?.focus();
      return;
    }
    setBusy(true);
    try {
      const { error } = await createClient().auth.resend({
        type: "signup",
        email: email.trim(),
        options: { emailRedirectTo: callbackUrl(next ?? LANDING_AFTER_SIGNUP) },
      });
      if (error) throw error;
      setNotice("If this email has a pending signup, a fresh confirmation link is on its way. Use the newest email; older links may have expired.");
    } catch (err) {
      setError(readableAuthError(err, "signup"));
    } finally {
      setBusy(false);
    }
  }

  async function sendPasswordReset() {
    setError(null);
    setNotice(null);
    if (!email.trim()) {
      setError("Enter your account email first, then request a password reset.");
      document.getElementById("email")?.focus();
      return;
    }
    setBusy(true);
    try {
      const { error } = await createClient().auth.resetPasswordForEmail(email.trim(), {
        redirectTo: callbackUrl("/reset-password"),
      });
      if (error) throw error;
      setNotice("If an account can be recovered with that email, a password reset link is on its way.");
    } catch (err) {
      setError(readableAuthError(err, "signin"));
    } finally {
      setBusy(false);
    }
  }

  const tab = (m: Mode) =>
    `min-h-11 flex-1 rounded-full px-4 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-violet ${mode === m ? "bg-violet text-coral-ink" : "text-muted hover:text-text"}`;
  const field = "min-h-14 w-full rounded-[14px] border-[1.5px] border-ink/20 bg-dark-surface px-[18px] text-base text-text outline-none transition-colors placeholder:text-muted focus:border-sage focus-visible:outline-2 focus-visible:outline-sage";

  return (
    <main className="grid min-h-screen bg-dark-bg lg:grid-cols-2">
      <section className="hidden flex-col justify-between border-r border-ink/10 bg-dark-surface p-10 lg:flex xl:p-14">
        <Wordmark />
        <div className="mx-auto flex w-full max-w-md flex-col gap-6">
          <div aria-hidden="true" className="relative grid aspect-[1.7/1] place-items-center overflow-hidden rounded-[24px] border border-ink/10 bg-violet/10">
            <div className="absolute size-48 rounded-full border border-violet/30" />
            <div className="absolute size-32 rounded-full border border-violet/40" />
            <div className="size-12 rounded-full border-2 border-sage bg-sage/15" />
          </div>
          <div>
            <h2 className="font-display text-3xl leading-tight">Welcome back. Your work is right where you left it.</h2>
            <p className="mt-3 text-sm text-muted">Sign in to pick up your saved analyses and versions.</p>
          </div>
        </div>
        <p className="text-xs text-muted">Fragilee · Patterns in historical data, not predictions.</p>
      </section>

      <section className="flex min-h-screen flex-col px-5 py-5 sm:px-8 lg:px-10">
        <header className="flex items-center justify-between gap-3 lg:justify-end">
          <span className="lg:hidden"><Wordmark /></span>
          <div className="flex items-center gap-3"><Link href="/" className="text-sm text-muted underline-offset-4 hover:text-text hover:underline">Back to home</Link><ThemeSelector initialTheme={initialTheme} /></div>
        </header>
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-[420px]">
            <div className="mb-7 flex rounded-full border border-ink/10 bg-ink/5 p-1">
              <button type="button" onClick={() => switchMode("signin")} aria-pressed={mode === "signin"} className={tab("signin")}>Sign in</button>
              <button type="button" onClick={() => switchMode("signup")} aria-pressed={mode === "signup"} className={tab("signup")}>Sign up</button>
            </div>

            <h1 className="font-display text-3xl text-text">
              {mode === "signin" ? "Good to see you" : "Create your account"}
            </h1>
            <p className="mb-7 mt-2 text-sm text-muted">
              {mode === "signin" ? "Log in to see your saved analyses." : "Save your analyses and return to them whenever you need."}
            </p>

            <form onSubmit={onSubmit} className="space-y-5">
              <div>
                <label htmlFor="email" className="mb-2 block text-sm text-muted">Email</label>
                <input id="email" type="email" required autoComplete="email" placeholder="you@example.com"
                  value={email} onChange={(e) => setEmail(e.target.value)} className={field} />
              </div>
              <div>
                <label htmlFor="password" className="mb-2 block text-sm text-muted">Password</label>
                <input id="password" type="password" required minLength={mode === "signup" ? 8 : undefined}
                  autoComplete={mode === "signin" ? "current-password" : "new-password"} placeholder="••••••••"
                  value={password} onChange={(e) => setPassword(e.target.value)} className={field} />
                {mode === "signin" && <button type="button" disabled={busy} onClick={sendPasswordReset} className="mt-2 min-h-11 text-sm font-medium text-violet-text underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-violet disabled:opacity-60">Forgot password?</button>}
              </div>

              <div aria-live="polite" className="min-h-5 text-sm">
                {error && <p className="text-critical-text" role="alert">{error}</p>}
                {notice && <p className="text-low" role="status">{notice}</p>}
              </div>

              <button type="submit" disabled={busy}
                className="min-h-12 w-full rounded-full bg-sage px-6 font-semibold button-label-on-sage transition-transform hover:-translate-y-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet disabled:opacity-60">
                {busy ? "One moment…" : mode === "signin" ? "Sign in" : "Sign up"}
              </button>
            </form>
            <button type="button" disabled={busy} onClick={resendConfirmation} className="mt-3 min-h-11 w-full text-sm font-medium text-violet-text underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-violet disabled:opacity-60">{mode === "signup" ? "Didn't get the email? Resend confirmation" : "Resend confirmation email"}</button>
            <div className="my-5 flex items-center gap-3 text-xs text-muted" aria-hidden="true"><span className="h-px flex-1 bg-ink/15" /><span>OR</span><span className="h-px flex-1 bg-ink/15" /></div>
            <button type="button" disabled={busy} onClick={continueWithGoogle} className="flex min-h-12 w-full items-center justify-center gap-3 rounded-full border border-ink/20 bg-dark-surface px-6 font-semibold text-text transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet disabled:opacity-60" aria-label="Continue with Google">
              <span aria-hidden="true" className="font-bold text-base">G</span>{busy ? "One moment…" : "Continue with Google"}
            </button>
            <p className="mt-6 text-center text-xs text-muted">Your saved analyses are private to your account.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
