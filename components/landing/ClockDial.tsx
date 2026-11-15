// A decorative dial: a ring of words slowly turning, a ticking seconds hand, around a central hub. It does not show the time.
export default function ClockDial({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 200 200" role="img" aria-label="A dial with the words find the cracks before they find you turning around it" className={className}>
      <defs><path id="ring" d="M100 100 m-74 0 a74 74 0 1 1 148 0 a74 74 0 1 1 -148 0" /></defs>
      <circle cx="100" cy="100" r="96" fill="var(--color-dark-surface)" stroke="var(--color-violet)" strokeWidth="3" />
      <g className="spin-slow"><text fontSize="12.5" fontWeight="700" fill="var(--color-text)"><textPath href="#ring" textLength="458" lengthAdjust="spacing">FIND THE CRACKS · BEFORE THEY FIND YOU ·</textPath></text></g>
      <line className="hand" style={{ ["--dur" as string]: "3600s" }} x1="100" y1="100" x2="100" y2="48" stroke="var(--color-high)" strokeWidth="5" strokeLinecap="round" />
      <line className="hand" style={{ ["--dur" as string]: "60s" }} x1="100" y1="112" x2="100" y2="30" stroke="var(--color-sage)" strokeWidth="2" strokeLinecap="round" />
      <circle cx="100" cy="100" r="9" fill="var(--color-text)" stroke="var(--color-high)" strokeWidth="4" />
    </svg>
  );
}
