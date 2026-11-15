import type { ReactNode } from "react";

// Endless strip. The children are rendered twice so the loop has no gap. Pauses on hover; stops for reduced motion.
export default function Marquee({ children, reverse = false, seconds = 45, className = "" }: { children: ReactNode; reverse?: boolean; seconds?: number; className?: string }) {
  return (
    <div className={`marquee ${className}`}>
      <div className={`marquee-track ${reverse ? "reverse" : ""}`} style={{ ["--dur" as string]: `${seconds}s` }}>
        <div className="flex shrink-0 items-center gap-3 pr-3">{children}</div>
        <div className="flex shrink-0 items-center gap-3 pr-3" aria-hidden="true">{children}</div>
      </div>
    </div>
  );
}
