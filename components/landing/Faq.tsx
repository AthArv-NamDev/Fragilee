"use client";

import { useId, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

export default function Faq({ items }: { items: { q: string; a: string }[] }) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  const base = useId();
  const reduce = useReducedMotion();
  const toggle = (i: number) => setOpen((s) => { const n = new Set(s); if (n.has(i)) n.delete(i); else n.add(i); return n; });
  return (
    <ul className="grid md:grid-cols-2 gap-4 items-start">
      {items.map((it, i) => {
        const isOpen = open.has(i);
        return (
          <li key={it.q} className="rounded-[16px] border border-ink/10 bg-dark-surface text-text">
            <h3>
              <button type="button" aria-expanded={isOpen} aria-controls={`${base}-${i}`} onClick={() => toggle(i)}
                  className="flex min-h-14 w-full items-center justify-between gap-4 p-5 text-left font-hero text-base md:text-lg focus-visible:outline-2 focus-visible:outline-violet rounded-xl">
                {it.q}
                <span aria-hidden="true" className={`text-2xl leading-none transition-transform duration-300 ${isOpen ? "rotate-45" : ""}`}>+</span>
              </button>
            </h3>
            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div id={`${base}-${i}`} role="region" aria-label={it.q} initial={reduce ? false : { height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }} transition={{ duration: 0.3 }} className="overflow-hidden">
                  <p className="px-5 pb-5 text-sm md:text-base text-muted">{it.a}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </li>
        );
      })}
    </ul>
  );
}
