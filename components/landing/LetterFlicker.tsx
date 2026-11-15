"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";

type Look = "outline" | "rose" | "sun" | "lime";
const LOOKS: Look[] = ["outline", "rose", "sun", "lime"];
const STYLE: Record<Look, React.CSSProperties> = {
  outline: { color: "transparent", WebkitTextStroke: "0.045em currentColor" },
  rose: { color: "var(--color-rose)" },
  sun: { color: "var(--color-sun)" },
  lime: { color: "var(--color-lime)" },
};

// Every couple of seconds one random letter changes its look for a moment (outline, or a bright colour).
// Screen readers get the plain text. With reduced motion nothing flickers.
export default function LetterFlicker({ text, startAfter = 1400, every = 2600 }: { text: string; startAfter?: number; every?: number }) {
  const reduce = useReducedMotion();
  const [on, setOn] = useState<{ i: number; look: Look } | null>(null);

  useEffect(() => {
    if (reduce) return;
    const letters = [...text].map((c, i) => (c === " " ? -1 : i)).filter((i) => i >= 0);
    let off: ReturnType<typeof setTimeout>;
    const flick = () => {
      setOn({ i: letters[Math.floor(Math.random() * letters.length)], look: LOOKS[Math.floor(Math.random() * LOOKS.length)] });
      off = setTimeout(() => setOn(null), 1100);
    };
    const first = setTimeout(flick, startAfter);
    const loop = setInterval(flick, every);
    return () => { clearTimeout(first); clearTimeout(off); clearInterval(loop); };
  }, [text, reduce, startAfter, every]);

  return (
    <>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {[...text].map((c, i) => (
          <span key={i} style={on?.i === i ? STYLE[on.look] : undefined} className="transition-colors duration-200">{c}</span>
        ))}
      </span>
    </>
  );
}
