import Link from "next/link";
import { cookies } from "next/headers";
import { createClient } from "@/lib/supabase/server";
import ThemeSelector from "@/components/ThemeSelector";
import { validTheme } from "@/lib/theme";
import Wordmark from "@/components/Wordmark";

const links = [
  { href: "#data", label: "Explore" },
  { href: "#how", label: "How it works" },
  { href: "#research", label: "Research" },
];

export default async function Nav() {
  const [supabase, cookieStore] = await Promise.all([createClient(), cookies()]);
  const { data } = await supabase.auth.getClaims();
  const signedIn = Boolean(data?.claims);
  const theme = validTheme(cookieStore.get("fragilee-theme")?.value);
  return (
    <header className="sticky top-0 z-50 border-b border-ink/10 bg-dark-bg/90 text-text shadow-sm backdrop-blur-xl">
      <nav aria-label="Main" className="mx-auto flex min-h-[72px] max-w-[1440px] items-center justify-between gap-3 px-4 md:px-8 xl:px-12">
        <Wordmark />
        <div className="hidden items-center gap-1 md:flex">
          {links.map((link) => <Link key={link.href} href={link.href} className="inline-flex min-h-11 items-center rounded-full px-4 text-sm font-medium text-muted transition-colors hover:bg-ink/5 hover:text-text focus-visible:outline-2 focus-visible:outline-coral">{link.label}</Link>)}
        </div>
        <div className="flex items-center gap-2">
          <ThemeSelector initialTheme={theme}/>
          <details className="group relative md:hidden">
            <summary className="flex min-h-11 cursor-pointer list-none items-center rounded-full border border-ink/20 px-3 text-sm font-semibold marker:hidden focus-visible:outline-2 focus-visible:outline-coral">Menu</summary>
            <div className="absolute right-0 top-[calc(100%+10px)] z-50 grid min-w-48 gap-1 rounded-2xl border border-ink/10 bg-dark-surface p-2 shadow-2xl">
              {links.map((link) => <Link key={link.href} href={link.href} className="flex min-h-11 items-center rounded-xl px-3 text-sm text-muted hover:bg-ink/5 hover:text-text">{link.label}</Link>)}
              <Link href={signedIn ? "/dashboard" : "/login"} className="flex min-h-11 items-center rounded-xl px-3 text-sm text-muted hover:bg-ink/5 hover:text-text">{signedIn ? "Dashboard" : "Sign in"}</Link>
            </div>
          </details>
          {signedIn ? (
            <Link href="/dashboard" className="inline-flex min-h-11 items-center rounded-full bg-sage px-4 text-sm font-semibold button-label-on-sage transition-transform hover:-translate-y-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral md:px-5">Dashboard</Link>
          ) : (
            <>
              <Link href="/login" className="hidden min-h-11 items-center rounded-full border border-ink/20 px-4 text-sm font-semibold transition-colors hover:border-coral md:inline-flex">Sign in</Link>
              <Link href="/login?mode=signup" className="inline-flex min-h-11 items-center rounded-full bg-sage px-4 text-sm font-semibold button-label-on-sage transition-transform hover:-translate-y-px focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral md:px-5">Sign up</Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
