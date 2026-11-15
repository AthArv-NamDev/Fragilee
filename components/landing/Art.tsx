// Shared icons use the v2 palette so they follow Light/Dark.
const tile = "grid place-items-center size-28 md:size-32 rounded-2xl border border-ink/10";
export function IconCracks() {
  return <div className={`${tile} bg-high`}><svg aria-hidden="true" viewBox="0 0 64 64" className="size-16" fill="none" stroke="var(--color-dark-bg)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"><circle cx="27" cy="27" r="16" fill="var(--color-dark-bg)" /><path d="M39 39 L56 56" /><path d="M22 16 L28 26 L22 31 L30 40" strokeWidth="3.5" /></svg></div>;
}
export function IconRanks() {
  return <div className={`${tile} bg-dark-surface`}><svg aria-hidden="true" viewBox="0 0 64 64" className="size-16" fill="none" strokeLinecap="round"><path d="M10 14 H54" stroke="var(--color-critical-text)" strokeWidth="9" /><path d="M10 32 H40" stroke="var(--color-medium)" strokeWidth="9" /><path d="M10 50 H26" stroke="var(--color-sage)" strokeWidth="9" /></svg></div>;
}
export function IconMoves() {
  return <div className={`${tile} bg-violet/10`}><svg aria-hidden="true" viewBox="0 0 64 64" className="size-16" fill="none" stroke="var(--color-violet)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"><circle cx="32" cy="32" r="24" fill="var(--color-dark-bg)" /><path d="M42 22 L35 35 L22 42 L29 29 Z" fill="var(--color-high)" /></svg></div>;
}
export function IconLevel({ n }: { n: string }) {
  return <div className="grid size-28 place-items-center rounded-2xl border border-ink/10 bg-dark-surface text-violet"><span className="font-display text-5xl">{n}</span></div>;
}
