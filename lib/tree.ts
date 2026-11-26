import type { Band, DiagnosticFinding, DiagnosticReport, PredictionResult } from "./types";
import { factorText } from "./format";
import { groupBreakpoints } from "./breakpoint-explorer.mjs";

/* ---------- the model: your startup -> branches -> factors (+ locked ghosts at Level 1) ---------- */
export type TNode = {
  id: string;
  kind: "root" | "stream" | "branch" | "factor" | "diagnostic-group" | "diagnostic" | "locked";
  label: string;
  band: Band | null;
  parent: string | null;
  children: string[];
  strength: number;               // 0 to 1: how hard it pushes, relative to its siblings
  contribution?: number;          // signed TreeSHAP log-odds contribution for this run
  effect?: "raises" | "lowers" | "neutral";
  value?: string | number;
  feature?: string;
  finding?: DiagnosticFinding;
};
export type TModel = Record<string, TNode>;

export const short = (s: string) => s.replace(/\s*\([^)]*\)/g, "");

/** Keep older saved reports readable without changing their stored result JSON. */
export function displayBranchLabel(label: string | undefined, group: string | undefined): string {
  if ([label, group].some((value) => typeof value === "string" && /market[\s_-]?industry/i.test(value))) return "Industry";
  return typeof label === "string" && label.trim() ? label : "Historical model factor";
}

/** Builds the tree from the API result, so what you see is always the data. */
export function buildModel(result: PredictionResult, rootLabel: string, diagnostics?: DiagnosticReport | null): TModel {
  const M: TModel = { root: { id: "root", kind: "root", label: rootLabel, band: null, parent: null, children: [], strength: 1 } };
  const modelChildren: string[] = [];
  const branches = Array.isArray((result as PredictionResult | null)?.tree?.children) ? result.tree.children : [];
  const total = branches.reduce((s, b) => s + (Number.isFinite(b.net_shap) ? Math.abs(b.net_shap) : 0), 0) || 1;
  for (const [index, b] of branches.entries()) {
    const group = typeof b.group === "string" ? b.group : `legacy-${index}`;
    const label = displayBranchLabel(b.label, group);
    const value = Number.isFinite(b.net_shap) ? b.net_shap : 0;
    const effect = b.effect === "raises" || b.effect === "lowers" ? b.effect : "neutral";
    const id = "b:" + group;
    M[id] = { id, kind: "branch", label, band: null, parent: "model-trace", children: [], strength: Math.abs(value) / total, effect, contribution: value };
    modelChildren.push(id);
    const factors = Array.isArray(b.factors) ? b.factors : [];
    const sum = factors.reduce((s, f) => s + (Number.isFinite(f.impact) ? Math.max(0, f.impact) : 0), 0) || 1;
    for (const [factorIndex, f] of factors.entries()) {
      const safeFeature = typeof f.feature === "string" ? f.feature : `legacy-factor-${factorIndex}`;
      const fid = `f:${group}:${safeFeature}`;
      const normalizedFactor = { ...f, feature: safeFeature, label: typeof f.label === "string" ? f.label : "Historical model input", value: f.value ?? "Not recorded" };
      const text = factorText(normalizedFactor);
      const effect = f.effect === "raises risk" ? "raises" : f.effect === "lowers risk" ? "lowers" : "neutral";
      const impact = Number.isFinite(f.impact) ? Math.max(0, f.impact) : 0;
      const contribution = Number.isFinite(f.contribution) ? f.contribution : undefined;
      M[fid] = { id: fid, kind: "factor", label: text.label, value: text.value ?? undefined, feature: safeFeature, band: null, parent: id, children: [], strength: impact / sum, effect, contribution };
      M[id].children.push(fid);
    }
  }
  if (result.stage === "stage1") {
    for (const g of ["Funding", "Traction"]) {
      M["x:" + g] = { id: "x:" + g, kind: "locked", label: g, band: null, parent: "model-trace", children: [], strength: 0.12 };
      modelChildren.push("x:" + g);
    }
  }
  M["model-trace"] = { id: "model-trace", kind: "stream", label: "Historical model attribution", band: null, parent: "root", children: modelChildren, strength: 0.5 };
  M.root.children.push("model-trace");

  const groups = groupBreakpoints(diagnostics?.findings ?? []);
  const groupIds: string[] = [];
  for (const group of groups) {
    const groupId = `diagnostic-group:${group.id}`;
    const findingIds: string[] = [];
    for (const finding of group.findings) {
      const id = `diagnostic:${finding.finding_id}`;
      findingIds.push(id);
      M[id] = { id, kind: "diagnostic", label: finding.title, band: null, parent: groupId, children: [], strength: 1, finding };
    }
    groupIds.push(groupId);
    M[groupId] = { id: groupId, kind: "diagnostic-group", label: group.label, band: null, parent: "breakpoints", children: findingIds, strength: 1 };
  }
  M.breakpoints = { id: "breakpoints", kind: "stream", label: "Startup breakpoints", band: null, parent: "root", children: groupIds, strength: 0.5 };
  M.root.children.push("breakpoints");
  return M;
}

/* ---------- plain-language reading of the data (no raw numbers) ---------- */
const signed = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(3)}`;

export function summarise(M: TModel): { up: string | null; down: string | null } {
  const branches = Object.values(M).filter((n) => n.kind === "branch");
  const pick = (e: "raises" | "lowers") => branches.filter((b) => b.effect === e).sort((a, b) => b.strength - a.strength)[0];
  return { up: pick("raises") ? short(pick("raises").label) : null, down: pick("lowers") ? short(pick("lowers").label) : null };
}

/* ---------- layout: active node in the middle, parent above, siblings to the sides, children below ---------- */
export type Mode = "wide" | "compact";
export type Role = "active" | "parent" | "sib" | "child";
export type Slot = { x: number; y: number; r: number; role: Role };
export const DIMS = { wide: { W: 1200, H: 900, CX: 600, CY: 260 }, compact: { W: 480, H: 1360, CX: 240, CY: 250 } } as const;
const SIDE_SLOTS = [180, 360, 480, 720, 840, 1020];

export function radius(n: TNode, role: Role, mode: Mode): number {
  const s = Math.sqrt(n.strength);
  if (n.kind === "diagnostic-group" && role === "active") return mode === "wide" ? 58 : 48;
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
    const columns = kids.length > 4 ? 4 : Math.max(1, kids.length);
    kids.forEach((id, i) => {
      const row = Math.floor(i / columns), inRow = Math.min(columns, kids.length - row * columns);
      const left = CX - ((inRow - 1) * 290) / 2;
      out.set(id, { x: inRow === 1 ? CX : left + (i % columns) * 290, y: 500 + row * 190, r: radius(M[id], "child", mode), role: "child" });
    });
  } else {
    kids.forEach((id, i) => {
      const row = Math.floor(i / 2), inRow = Math.min(2, kids.length - row * 2);
      out.set(id, { x: CX + ((i % 2) - (inRow - 1) / 2) * 260, y: 490 + row * 220, r: radius(M[id], "child", mode), role: "child" });
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
  const n = M[id];
  if (!n) return { kicker: "Technical model details", title: "No selectable model detail", lines: ["This saved report does not contain this model node."] };
  const title = short(n.label);
  if (n.kind === "root") {
    return { kicker: "Analysis tree", title, lines: ["This tree keeps startup-specific diagnostics and historical model attribution in separate branches.", "Choose Startup breakpoints to inspect profile findings, their practical mechanisms, and next validation. Choose Historical model attribution for the classifier's stored TreeSHAP trace.", "Missing information is shown as a gap, not treated as risk. The tree is not an overall score or failure prediction."] };
  }
  if (n.kind === "stream") {
    if (n.id === "model-trace") {
      const s = summarise(M);
      const groups = n.children.map((child) => M[child]).filter((child) => child.kind === "branch").map((child) => child.label);
      const lines = ["Historical TreeSHAP attribution describes how the classifier used recorded inputs. It is not a startup-specific diagnosis, cause, or forecast."];
      if (groups.length) lines.push(`Model inputs represented here: ${[...new Set(groups)].join(", ")}.`);
      if (s.up) lines.push(`Inputs associated with a higher internal classifier output include ${s.up}.`);
      if (s.down) lines.push(`Inputs associated with a lower internal classifier output include ${s.down}.`);
      if (!groups.length) lines.push("This saved analysis has no compatible historical model trace.");
      if (n.children.some((child) => M[child].kind === "locked")) lines.push("Funding and Traction unlock with Level 2, coming soon.");
      return { kicker: "Historical model attribution", title, lines };
    }
    const count = n.children.reduce((sum, id) => sum + M[id].children.length, 0);
    return { kicker: "Founder-facing assessment", title, lines: [count ? `${count} profile checks are grouped below by business mechanism. Select a finding to inspect the submitted inputs, practical mechanism, uncertainty, and next validation.` : "No structured-profile diagnostic findings are available for this saved analysis.", "Finding order is not a ranking of likelihood, urgency, or severity. Information gaps are not risk findings."] };
  }
  if (n.kind === "diagnostic-group") return { kicker: "Breakpoint category", title, lines: ["Select an individual check in this category to inspect why it may matter for the submitted business and what to validate next."] };
  if (n.kind === "diagnostic") return { kicker: "Startup breakpoint", title, lines: [n.finding?.explanation ?? "Select a finding to inspect its assessment."] };
  if (n.kind === "branch") {
    const lines = [
      n.effect === "neutral" ? "The grouped attribution is neutral for this run." : `Technical TreeSHAP attribution: ${signed(n.contribution ?? 0)} log-odds.`,
      "Log-odds are the classifier's internal units, not percentage points, a failure probability, or a measurement of business health. This association is not causal evidence.",
    ];
    if (n.label === "Industry") lines.push("This branch summarizes recorded industry tags/categories. It does not score current demand, competition or customer validation.");
    if (n.children.length) lines.push("Choose a factor to inspect the recorded input and its technical attribution.");
    return { kicker: "Branch", title, lines };
  }
  if (n.kind === "factor") {
    const direction = n.effect === "raises" ? "raised" : "lowered";
    const lines = [n.contribution === undefined
      ? "This older saved report does not contain a per-input attribution."
      : n.effect === "neutral"
        ? `Technical TreeSHAP attribution: ${signed(n.contribution)} log-odds in the classifier's internal output for this run.`
        : `This recorded input was associated with a ${direction} shift of ${signed(n.contribution)} log-odds in the classifier's internal output for this run.`];
    if (n.value !== undefined) lines.push(`Recorded model input: ${n.value}.`);
    if (n.contribution !== undefined) lines.push("Log-odds are model units, not percentage points, a failure probability, or a business-risk measurement. The attribution is not causal evidence.");
    return { kicker: "Model factor", title, lines };
  }
  return { kicker: "Locked", title, lines: ["This branch needs funding and traction details. Level 2 will unlock it."] };
}

const NEAREST: [number, string][] = [[0.1, "1 in 10"], [0.2, "1 in 5"], [0.25, "1 in 4"], [0.33, "1 in 3"], [0.4, "2 in 5"], [0.5, "1 in 2"], [0.6, "3 in 5"], [0.67, "2 in 3"], [0.75, "3 in 4"], [0.8, "4 in 5"], [0.9, "9 in 10"]];
export const friendly = (r: number) => NEAREST.reduce((a, b) => (Math.abs(b[0] - r) < Math.abs(a[0] - r) ? b : a))[1];
