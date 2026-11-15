import Link from "next/link";

// The logo is always a link home. Plain wordmark, no tilted sticker (design v2).
export default function Wordmark() {
  return (
    <Link href="/" className="inline-flex items-center gap-2.5 rounded text-text hover:text-violet focus-visible:outline-2 focus-visible:outline-violet" aria-label="Fragilee, home">
      <svg width="26" height="26" viewBox="0 0 100 100" aria-hidden="true">
        <polygon points="50,12 80,30 80,70 50,88 20,70 20,30" fill="none" stroke="var(--line-2)" strokeWidth="5" />
        <path d="M50 12 L58 42 L42 50 L60 68 L50 88" fill="none" stroke="var(--violet)" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="58" cy="42" r="4.5" fill="var(--violet-text)" />
      </svg>
      <span className="font-display text-xl tracking-tight">Fragilee</span>
    </Link>
  );
}
