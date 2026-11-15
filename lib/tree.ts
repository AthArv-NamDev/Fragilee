import type { Band, PredictionResult } from "./types";
import { factorText } from "./format";

/* ---------- the model: your startup -> branches -> factors (+ locked ghosts at Level 1) ---------- */
export type TNode = {
  id: string;
  kind: "root" | "branch" | "factor" | "locked";
  label: string;
  band: Band | null;
  parent: string | null;
  children: string[];
  strength: number;               // 0 to 1: how hard it pushes, relative to its siblings
  contribution?: number;          // signed TreeSHAP log-odds contribution for this run
  effect?: "raises" | "lowers" | "neutral";
  value?: string | number;
  feature?: string;
};
export type TModel = Record<string, TNode>;

export const short = (s: string) => s.replace(/\s*\([^)]*\)/g, "");

/** Builds the tree from the API result, so what you see is always the data. */
export function buildModel(result: PredictionResult, rootLabel: string): TModel {
  const M: TModel = { root: { id: "root", kind: "root", label: rootLabel, band: null, parent: null, children: [], strength: 1 } };
  const branches = result.tree.children;
  const total = branches.reduce((s, b) => s + Math.abs(b.net_shap), 0) || 1;
  for (const b of branches) {
    const id = "b:" + b.group;
    M[id] = { id, kind: "branch", label: b.label, band: null, parent: "root", children: [], strength: Math.abs(b.net_shap) / total, effect: b.effect, contribution: b.net_shap };
    M.root.children.push(id);
    const sum = b.factors.reduce((s, f) => s + f.impact, 0) || 1;
    for (const f of b.factors) {
      const fid = `f:${b.group}:${f.feature}`;
      const raises = f.effect.startsWith("raises"), text = factorText(f);
      M[fid] = { id: fid, kind: "factor", label: text.label, value: text.value ?? undefined, feature: f.feature, band: null, parent: id, children: [], strength: f.impact / sum, effect: raises ? "raises" : "lowers", contribution: f.contribution };
      M[id].children.push(fid);
    }
  }
  if (result.stage === "stage1") {
    for (const g of ["Funding", "Traction"]) {
      M["x:" + g] = { id: "x:" + g, kind: "locked", label: g, band: null, parent: "root", children: [], strength: 0.12 };
      M.root.children.push("x:" + g);
    }
  }
  return M;
}

/* ---------- plain-language reading of the data (no raw numbers) ---------- */
const signed = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(3)}`;

export function summarise(M: TModel): { up: string | null; down: string | null } {
  const branches = M.root.children.map((id) => M[id]).filter((n) => n.kind === "branch");
  const pick = (e: "raises" | "lowers") => branches.filter((b) => b.effect === e).sort((a, b) => b.strength - a.strength)[0];
  return { up: pick("raises") ? short(pick("raises").label) : null, down: pick("lowers") ? short(pick("lowers").label) : null };
}

/* ---------- layout: active node in the middle, parent above, siblings to the sides, children below ---------- */
export type Mode = "wide" | "compact";
export type Role = "active" | "parent" | "sib" | "child";
export type Slot = { x: number; y: number; r: number; role: Role };
export const DIMS = { wide: { W: 1000, H: 640, CX: 500, CY: 262 }, compact: { W: 560, H: 840, CX: 280, CY: 250 } } as const;
const SIDE_SLOTS = [320, 680, 185, 815, 70, 930];

export function radius(n: TNode, role: Role, mode: Mode): number {
  const s = Math.sqrt(n.strength);
  if (role === "active") return n.kind === "root" ? (mode === "wide" ? 84 : 66) : mode === "wide" ? 74 : 58;
  if (role === "parent") return mode === "wide" ? 32 : 26;
  if (n.kind === "locked") return mode === "wide" ? 34 : 32;
  if (role === "child") return mode === "wide" ? 28 + 34 * s : 24 + 20 * s;
  return 22 + 26 * s;
}

export function layout(M: TModel, activeId: string, mode: Mode): Map<string, Slot> {
  const { CX, CY } = DIMS[mode], out = new Map<string, Slot>(), a = M[activeId];
  out.set(a.id, { x: CX, y: CY, r: radius(a, "active", mode), role: "active" });
  if (a.parent) {
    const p = M[a.parent];
    out.set(p.id, { x: CX, y: mode === "wide" ? 64 : 56, r: radius(p, "parent", mode), role: "parent" });
    if (mode === "wide") {
      let i = 0;
      for (const sid of p.children) {
        if (sid === a.id) continue;
        const x = SIDE_SLOTS[i++];
        if (x !== undefined) out.set(sid, { x, y: CY, r: radius(M[sid], "sib", mode), role: "sib" });   // on a phone siblings live in the outline
      }
    }
  }
  const kids = a.children;
  if (mode === "wide") {
    kids.forEach((id, i) => out.set(id, { x: kids.length === 1 ? CX : 150 + (i * 700) / (kids.length - 1), y: 478, r: radius(M[id], "child", mode), role: "child" }));
  } else {
    kids.slice(0, 6).forEach((id, i) => {
      const row = Math.floor(i / 3), inRow = Math.min(3, kids.length - row * 3);
      out.set(id, { x: CX + ((i % 3) - (inRow - 1) / 2) * 170, y: 510 + row * 190, r: radius(M[id], "child", mode), role: "child" });
    });
  }
  return out;
}

export function wrap(s: string, max: number, lines: number): string[] {
  const out = [""];
  for (const w of s.split(" ")) {
    const t = (out[out.length - 1] + " " + w).trim();
    if (t.length <= max) out[out.length - 1] = t; else out.push(w);
  }
  if (out.length > lines) { out.length = lines; out[lines - 1] = out[lines - 1].slice(0, max - 1) + "…"; }
  return out;
}

/* ---------- what the side panel says about a node ---------- */
export type Reading = { kicker: string; title: string; lines: string[] };
export function describe(M: TModel, id: string): Reading {
  const n = M[id], title = short(n.label);
  if (n.kind === "root") {
    const s = summarise(M);
    const groups = n.children.map((child) => M[child]).filter((child) => child.kind === "branch").map((child) => child.label);
    const lines = ["This saved model trace is not a validated forecast or a startup-specific vulnerability assessment."];
    if (groups.length) lines.push(`Model inputs represented here: ${[...new Set(groups)].join(", ")}.`);
    if (s.up) lines.push(`Largest positive model contribution: ${s.up}.`);
    if (s.down) lines.push(`Largest negative model contribution: ${s.down}.`);
    lines.push("A feature contribution describes how an input affected this historical model score. It is not a cause or proof of exposure.");
    if (n.children.some((c) => M[c].kind === "locked")) lines.push("Funding and Traction unlock with Level 2, coming soon.");
    return { kicker: "Model overview", title, lines };
  }
  if (n.kind === "branch") {
    const lines = [
      n.effect === "neutral" ? "The grouped model contribution is zero for this run." : `Model contribution: ${signed(n.contribution ?? 0)} log-odds for this run.`,
      "This is how the trained model combined these inputs. It is not a failure percentage or proof of cause.",
    ];
    if (n.label === "Industry") lines.push("This branch summarizes recorded industry tags/categories. It does not score current demand, competition or customer validation.");
    if (n.children.length) lines.push("Choose a factor to inspect its input and contribution, then review separate research evidence.");
    return { kicker: "Branch", title, lines };
  }
  if (n.kind === "factor") {
    const direction = n.effect === "raises" ? "raised" : "lowered";
    const lines = [n.contribution === undefined
      ? "This saved analysis predates per-factor contributions. Re-run it to see the model contribution."
      : `This model input ${direction} the raw score by ${signed(n.contribution)} log-odds for this run.`];
    if (n.value !== undefined) lines.push(`Input value used: ${n.value}.`);
    if (n.contribution !== undefined) lines.push("Log-odds are model units, not a percentage chance. This attribution is an association in historical data, not a cause.");
    return { kicker: "Model factor", title, lines };
  }
  return { kicker: "Locked", title, lines: ["This branch needs funding and traction details. Level 2 will unlock it."] };
}

const NEAREST: [number, string][] = [[0.1, "1 in 10"], [0.2, "1 in 5"], [0.25, "1 in 4"], [0.33, "1 in 3"], [0.4, "2 in 5"], [0.5, "1 in 2"], [0.6, "3 in 5"], [0.67, "2 in 3"], [0.75, "3 in 4"], [0.8, "4 in 5"], [0.9, "9 in 10"]];
export const friendly = (r: number) => NEAREST.reduce((a, b) => (Math.abs(b[0] - r) < Math.abs(a[0] - r) ? b : a))[1];
