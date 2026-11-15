"use client";

import { useState, type PointerEvent } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring } from "motion/react";

const NODES = [
  { id: "place", label: "Place", type: "MODEL INPUT · LEVEL 1", detail: "The first historical model reads country and state fields. It does not assess local customer demand." , x: 18, y: 24, kind: "model" },
  { id: "industry", label: "Industry", type: "MODEL INPUT · LEVEL 1", detail: "The first model uses selected industry tags. A tag is a model input, not a full market analysis.", x: 82, y: 24, kind: "model" },
  { id: "funding", label: "Funding", type: "MODEL INPUT · LEVEL 2", detail: "The second historical model uses funding amounts, round counts and investor flags.", x: 13, y: 66, kind: "model" },
  { id: "relationships", label: "Relationships", type: "MODEL INPUT · LEVEL 2", detail: "The second model includes people linked to a company. This field can include information from after the outcome.", x: 82, y: 66, kind: "model" },
  { id: "research", label: "Research", type: "EVIDENCE LAYER", detail: "OpenAlex results are retrieved separately when you explore a factor. Research does not change the model score.", x: 30, y: 91, kind: "evidence" },
  { id: "cases", label: "Company cases", type: "EVIDENCE LAYER", detail: "Curated company stories have their own source trail. A shared industry label does not make two companies equivalent.", x: 70, y: 91, kind: "evidence" },
] as const;

export default function FragileeHeroScene() {
  const reduce = useReducedMotion();
  const [selected, setSelected] = useState<(typeof NODES)[number]>(NODES[0]);
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const rx = useSpring(rawX, { stiffness: 110, damping: 19, mass: .6 });
  const ry = useSpring(rawY, { stiffness: 110, damping: 19, mass: .6 });

  function movePointer(event: PointerEvent<HTMLDivElement>) {
    if (reduce || event.pointerType !== "mouse") return;
    const rect = event.currentTarget.getBoundingClientRect();
    rawY.set(((event.clientX - rect.left) / rect.width - .5) * 7);
    rawX.set(((event.clientY - rect.top) / rect.height - .5) * -6);
  }

  function resetPointer() { rawX.set(0); rawY.set(0); }

  return <div>
    <div className="hero-ecosystem relative mx-auto aspect-[.92/1] w-full max-w-[590px]" onPointerMove={movePointer} onPointerLeave={resetPointer}>
      <motion.div className="absolute inset-[2%]" style={{ rotateX: rx, rotateY: ry, transformPerspective: 1100, transformStyle: "preserve-3d" }}>
        <div aria-hidden="true" className="absolute inset-[8%] rounded-full border border-coral/15"/>
        <div aria-hidden="true" className="absolute inset-[18%] rounded-full border border-lime/20 [transform:rotateX(58deg)]"/>
        <div aria-hidden="true" className="absolute inset-[23%] rounded-full border border-coral/10 [transform:rotateY(62deg)]"/>
        <svg viewBox="0 0 100 100" className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
          <defs><linearGradient id="heroBranch" x1="0" y1="0" x2="1" y2="1"><stop stopColor="var(--coral)"/><stop offset="1" stopColor="var(--acid)"/></linearGradient></defs>
          {NODES.map((node) => <path key={node.id} d={`M50 47 C50 ${(47 + node.y) / 2 - 4} ${node.x} ${(47 + node.y) / 2} ${node.x} ${node.y}`} fill="none" stroke={node.kind === "model" ? "url(#heroBranch)" : "var(--violet)"} strokeWidth=".42" strokeDasharray={node.kind === "evidence" ? "1.2 1.2" : undefined} opacity=".7"/>)}
        </svg>
        <motion.div className="hero-core absolute left-1/2 top-[47%] grid size-[28%] -translate-x-1/2 -translate-y-1/2 place-items-center rounded-[34%] border border-coral/40 bg-dark-surface shadow-[0_30px_80px_rgba(0,0,0,.35)]"
          animate={reduce ? undefined : { y: [0, -7, 0], rotateZ: [0, 1.5, 0] }} transition={reduce ? undefined : { duration: 7, repeat: Infinity, ease: "easeInOut" }} style={{ transformStyle: "preserve-3d" }}>
          <div aria-hidden="true" className="absolute inset-[14%] rounded-[30%] border border-lime/40 bg-coral/10 [transform:translateZ(22px)]"/>
          <div className="relative grid size-12 place-items-center rounded-2xl bg-coral font-display text-xl text-coral-ink shadow-xl [transform:translateZ(34px)] md:size-14">F.</div>
          <span className="absolute -bottom-8 whitespace-nowrap text-[10px] font-semibold uppercase tracking-[.18em] text-muted [transform:translateZ(24px)]">Fragilee · evidence map</span>
        </motion.div>
        {NODES.map((node) => <button key={node.id} type="button" aria-pressed={selected.id === node.id} onFocus={() => setSelected(node)} onMouseEnter={() => setSelected(node)} onClick={() => setSelected(node)}
          style={{ left: `${node.x}%`, top: `${node.y}%`, transform: "translate(-50%, -50%) translateZ(30px)" }}
          className={`hero-node absolute z-10 flex min-h-11 min-w-11 flex-col items-center justify-center gap-1 rounded-2xl border px-2 py-2 text-center shadow-xl backdrop-blur transition-[transform,border-color,background-color] duration-200 hover:-translate-y-1 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-coral ${selected.id === node.id ? "border-coral bg-coral text-coral-ink" : node.kind === "model" ? "border-ink/15 bg-dark-surface text-text" : "border-violet/40 bg-dark-surface text-violet-text"}`}>
          <span className="whitespace-nowrap text-[11px] font-bold md:text-xs">{node.label}</span>
          <span className={`hidden text-[8px] font-semibold tracking-[.1em] sm:block ${selected.id === node.id ? "text-dark-bg/80" : "text-muted"}`}>{node.kind === "model" ? "MODEL" : "EVIDENCE"}</span>
          <span className="sr-only">{node.type}. {node.detail}</span>
        </button>)}
      </motion.div>
    </div>
    <div className="mx-auto mt-3 min-h-[88px] max-w-[560px] rounded-2xl border border-ink/10 bg-dark-surface/85 p-4 text-left backdrop-blur" aria-live="polite">
      <p className={`eyebrow ${selected.kind === "model" ? "text-coral" : "text-violet-text"}`}>{selected.type}</p>
      <p className="mt-1 text-sm leading-relaxed text-muted">{selected.detail}</p>
    </div>
  </div>;
}
