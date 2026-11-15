"use client";

import { useRef, type ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";

export type TabDef = { id: string; label: string; panel: ReactNode };

/** Tabs that work with arrow keys. Every panel stays mounted, so the tree keeps its place while you read the stories. */
export default function ResultTabs({ tabs, active, onChange }: { tabs: TabDef[]; active: string; onChange: (id: string) => void }) {
  const setActive = onChange;
  const reduce = useReducedMotion();
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const move = (e: React.KeyboardEvent, i: number) => {
    const j = e.key === "ArrowRight" ? (i + 1) % tabs.length : e.key === "ArrowLeft" ? (i - 1 + tabs.length) % tabs.length : e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : -1;
    if (j < 0) return;
    e.preventDefault();
    setActive(tabs[j].id);
    refs.current[tabs[j].id]?.focus();
  };
  return (
    <div>
      <div role="tablist" aria-label="Result sections" className="mb-6 flex gap-2 overflow-x-auto border-b border-ink/10 pb-3">
        {tabs.map((t, i) => (
          <button key={t.id} ref={(el) => { refs.current[t.id] = el; }} role="tab" id={`tab-${t.id}`} aria-selected={active === t.id} aria-controls={`panel-${t.id}`} tabIndex={active === t.id ? 0 : -1}
            onClick={() => setActive(t.id)} onKeyDown={(e) => move(e, i)}
            className={`min-h-11 shrink-0 rounded-full border px-5 py-2 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-violet ${active === t.id ? "border-coral bg-coral text-coral-ink" : "border-ink/10 bg-dark-surface text-ink/80 hover:border-coral/50 hover:bg-ink/5"}`}>
            {t.label}
          </button>
        ))}
      </div>
      {tabs.map((t) => (
        <motion.div key={t.id} role="tabpanel" id={`panel-${t.id}`} aria-labelledby={`tab-${t.id}`} hidden={active !== t.id}
          initial={false} animate={active === t.id ? { opacity: 1, y: 0 } : { opacity: 0, y: 6 }} transition={{ duration: reduce ? 0 : .24, ease: "easeOut" }}>{t.panel}</motion.div>
      ))}
    </div>
  );
}
