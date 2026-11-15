import Link from "next/link";
import Wordmark from "@/components/Wordmark";

export default function NotFound() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 text-center">
      <Wordmark />
      <h1 className="font-display text-4xl mt-8 mb-3">We could not find that page</h1>
      <p className="text-muted mb-8 max-w-md">It may have been deleted, or the link is wrong. Analyses are private, so someone else&apos;s link looks like this too.</p>
      <div className="flex gap-4">
        <Link href="/" className="inline-flex min-h-11 items-center rounded-full bg-sage px-6 font-semibold text-[var(--sage-ink)]">Go home</Link>
        <Link href="/dashboard" className="border border-text/40 px-6 py-3 rounded-full">Your analyses</Link>
      </div>
    </main>
  );
}
