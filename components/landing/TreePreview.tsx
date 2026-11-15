"use client";

import { motion, useReducedMotion } from "motion/react";

// An illustrative map of the inputs available at each level, not a sample result.
const NODES = [
  { x: 150, y: 80, r: 26, t: "Place", s: "Level 1 model input" },
  { x: 92, y: 262, r: 26, t: "Industry", s: "Level 1 model input" },
  { x: 300, y: 318, r: 26, t: "Notes", s: "saved context only" },
  { x: 480, y: 262, r: 26, t: "Funding", s: "Level 2 model input", locked: true },
  { x: 462, y: 78, r: 26, t: "Company data", s: "Level 2 model input", locked: true },
];

export default function TreePreview({ className = "" }: { className?: string }) {
  const reduce = useReducedMotion();
  return (
    <svg viewBox="0 0 600 380" role="img" aria-label="Illustration of Fragilee inputs: place and industry at Level 1, additional company data at Level 2, with founder notes kept separate" className={className}>
      {NODES.map((n, i) => (
        <motion.path key={n.t} d={`M300 185 C ${(300 + n.x) / 2} 185, ${n.x} ${(185 + n.y) / 2}, ${n.x} ${n.y}`} fill="none" stroke={n.locked ? "var(--color-muted)" : "var(--color-violet)"}
          strokeWidth="3" strokeLinecap="round" strokeDasharray={n.locked ? "3 10" : undefined} opacity=".7"
          initial={reduce ? false : { pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.1, delay: 0.2 + i * 0.15 }} />
      ))}
      <circle cx="300" cy="185" r="56" fill="var(--color-sage)" stroke="var(--color-sage)" strokeWidth="4" />
      <text x="300" y="181" textAnchor="middle" fontSize="15" fontWeight="700" fill="var(--sage-ink)">YOUR</text>
      <text x="300" y="201" textAnchor="middle" fontSize="15" fontWeight="700" fill="var(--sage-ink)">IDEA</text>
      {NODES.map((n, i) => (
        <g key={n.t} className="float" style={{ ["--dur" as string]: `${5 + i}s` }}>
          <circle cx={n.x} cy={n.y} r={n.r} fill={n.locked ? "none" : "var(--color-violet)"} fillOpacity=".18" stroke={n.locked ? "var(--color-muted)" : "var(--color-violet)"} strokeWidth="3" strokeDasharray={n.locked ? "5 6" : undefined} />
          <text x={n.x} y={n.y + n.r + 22} textAnchor="middle" fontSize="16" fontWeight="700" fill="var(--color-text)">{n.t}</text>
          <text x={n.x} y={n.y + n.r + 40} textAnchor="middle" fontSize="12" fill="var(--color-muted)">{n.s}</text>
        </g>
      ))}
    </svg>
  );
}
