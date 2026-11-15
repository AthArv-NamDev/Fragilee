import { COUNTRY_NAMES, STATE_NAMES } from "./geo";
import type { Band, Factor } from "./types";

const NEAREST: [number, string][] = [
  [0.1, "1 in 10"], [0.2, "1 in 5"], [0.25, "1 in 4"], [0.33, "1 in 3"], [0.4, "2 in 5"], [0.5, "1 in 2"],
  [0.6, "3 in 5"], [0.67, "2 in 3"], [0.75, "3 in 4"], [0.8, "4 in 5"], [0.9, "9 in 10"],
];
/** 0.209 -> "1 in 5". Rounds to the nearest friendly fraction. */
export function inN(rate: number): string {
  return NEAREST.reduce((a, b) => (Math.abs(b[0] - rate) < Math.abs(a[0] - rate) ? b : a))[1];
}

export const BAND_STYLE: Record<Band, { color: string; text: string; glyph: string; fill: number }> = {
  Low: { color: "var(--color-low)", text: "text-low", glyph: "●", fill: 0.25 },
  Medium: { color: "var(--color-medium)", text: "text-medium", glyph: "▲", fill: 0.5 },
  High: { color: "var(--color-high)", text: "text-high", glyph: "◆", fill: 0.75 },
  Critical: { color: "var(--color-critical)", text: "text-critical-text", glyph: "✦", fill: 1 },
};

/** Turns API factors like "State: OTHER = Yes" into plain words. A tag or place is either on or off, so no value is shown. */
export function factorText(f: Factor): { label: string; value: string | null } {
  const [kind, val] = f.feature.split("=");
  if (val === undefined) return { label: f.label, value: String(f.value) };
  if (kind === "country") return { label: val === "OTHER" ? "Another country" : `Country: ${COUNTRY_NAMES[val] ?? val}`, value: null };
  if (kind === "state") {
    if (val === "NONE") return { label: "No state given", value: null };
    if (val === "OTHER") return { label: "Another US state", value: null };
    return { label: `State: ${STATE_NAMES[val] ?? val}`, value: null };
  }
  return { label: `Industry: ${val}`, value: null };
}
