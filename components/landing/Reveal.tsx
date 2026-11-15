"use client";

import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

// Fades and lifts its children in once, when they scroll into view. No motion at all if the visitor asked for none.
export default function Reveal({ children, delay = 0, y = 32, className }: { children: ReactNode; delay?: number; y?: number; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.7, delay, ease: [0.2, 0.7, 0.2, 1] }}
    >
      {children}
    </motion.div>
  );
}
