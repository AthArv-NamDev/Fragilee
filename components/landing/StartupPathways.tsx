/** A quiet map of possible startup paths, pressure points, and evidence. */
export default function StartupPathways({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 420 440" role="img" aria-label="A startup journey branching into possible paths, with a marked pressure point and evidence nodes" preserveAspectRatio="xMidYMid meet" className={className} fill="none">
      <rect width="420" height="440" rx="32" fill="var(--color-dark-surface)" />
      <path d="M0 345h420M0 358h420" stroke="var(--color-text)" strokeOpacity=".06" />
      <path d="M210 395V300c0-34-30-44-72-44h-28c-29 0-42-17-42-43v-54" stroke="var(--color-text)" strokeOpacity=".28" strokeWidth="3" />
      <path d="M210 300c0-34 30-44 72-44h27c29 0 42-17 42-43v-54" stroke="var(--color-text)" strokeOpacity=".28" strokeWidth="3" />
      <path d="M210 300v-46c0-28-20-43-49-43h-5" stroke="var(--color-high)" strokeWidth="4" strokeLinecap="round" />
      <path d="M210 300v-46c0-28 20-43 49-43h5" stroke="var(--color-sage)" strokeWidth="4" strokeLinecap="round" />
      <path d="M210 395V300" stroke="var(--color-text)" strokeOpacity=".42" strokeWidth="4" strokeLinecap="round" />
      <circle cx="210" cy="300" r="10" fill="var(--color-dark-bg)" stroke="var(--color-text)" strokeWidth="3" />
      <circle cx="154" cy="211" r="9" fill="var(--color-dark-bg)" stroke="var(--color-high)" strokeWidth="4" />
      <circle cx="266" cy="211" r="9" fill="var(--color-dark-bg)" stroke="var(--color-sage)" strokeWidth="4" />
      <path d="m145 201 18 20m0-20-18 20" stroke="var(--color-high)" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="82" cy="145" r="7" fill="var(--color-violet)" />
      <circle cx="338" cy="145" r="7" fill="var(--color-coral)" />
      <circle cx="210" cy="395" r="15" fill="var(--color-dark-bg)" stroke="var(--color-text)" strokeOpacity=".7" strokeWidth="3" />
      <circle cx="210" cy="395" r="5" fill="var(--color-text)" />
      <rect x="32" y="38" width="110" height="52" rx="12" fill="var(--color-dark-bg)" stroke="var(--color-text)" strokeOpacity=".12" />
      <path d="M48 55h42M48 67h74" stroke="var(--color-text)" strokeOpacity=".28" strokeWidth="4" strokeLinecap="round" />
      <rect x="278" y="38" width="110" height="52" rx="12" fill="var(--color-dark-bg)" stroke="var(--color-text)" strokeOpacity=".12" />
      <path d="M294 55h48M294 67h74" stroke="var(--color-text)" strokeOpacity=".28" strokeWidth="4" strokeLinecap="round" />
      <path d="M82 90v30m0 0h128m0 0h128m-128 0v110" stroke="var(--color-text)" strokeOpacity=".12" strokeWidth="2" strokeDasharray="4 7" />
      <circle cx="82" cy="120" r="4" fill="var(--color-violet)" />
      <circle cx="338" cy="120" r="4" fill="var(--color-coral)" />
    </svg>
  );
}
