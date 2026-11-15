"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "motion/react";

// The footer name, huge. One letter at a time turns into an outline.
export default function BigWordmark({ text = "FRAGILEE" }: { text?: string }) {
  const reduce = useReducedMotion();
  const [i, setI] = useState(-1);
  useEffect(() => {
    if (reduce) return;
    const id = setInterval(() => setI(Math.floor(Math.random() * text.length)), 1800);
    return () => clearInterval(id);
  }, [reduce, text]);
  return (
    <div className="select-none flex justify-between font-hero leading-[.8] text-text text-[clamp(3.2rem,16.5vw,17rem)] tracking-tighter overflow-hidden" aria-hidden="true">
      {[...text].map((c, k) => (
        <span key={k} className="transition-all duration-300" style={k === i ? { color: "transparent", WebkitTextStroke: "0.02em var(--color-text)" } : undefined}>{c}</span>
      ))}
    </div>
  );
}
