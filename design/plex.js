(() => {
'use strict';
const DATA = /*DATA*/;
const BC = {Low:'#6FBFA0', Medium:'#D9A441', High:'#E0784F', Critical:'#B14C63'};
const BT = {Low:'#6FBFA0', Medium:'#D9A441', High:'#E0784F', Critical:'#E89AAA'};
const GL = {Low:'●', Medium:'▲', High:'◆', Critical:'✦'};
const NEAREST = [[.1,'1 in 10'],[.2,'1 in 5'],[.25,'1 in 4'],[.33,'1 in 3'],[.4,'2 in 5'],[.5,'1 in 2'],[.6,'3 in 5'],[.67,'2 in 3'],[.75,'3 in 4'],[.8,'4 in 5'],[.9,'9 in 10']];
const inN = r => NEAREST.reduce((a, b) => Math.abs(b[0] - r) < Math.abs(a[0] - r) ? b : a)[1];
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const short = s => s.replace(/\s*\([^)]*\)/g, '');
const fmt = v => typeof v === 'number' ? String(v) : v;           // 2.0 arrives as 2 in JS, so no ".0"
const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs = {}) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
const reduce = window.matchMedia ? matchMedia('(prefers-reduced-motion: reduce)') : {matches: false};

/* ---------- model: root -> branches -> factors (+ locked ghosts at Level 1) ---------- */
function buildModel(res) {
  const M = {}, kids = res.tree.children;
  const tot = kids.reduce((s, b) => s + Math.abs(b.net_shap), 0) || 1;
  M.root = {id:'root', kind:'root', label:'Your startup', band:res.band, parent:null, children:[], strength:1};
  for (const b of kids) {
    const id = 'b:' + b.group;
    M[id] = {id, kind:'branch', label:b.label, band:b.band, effect:b.effect, parent:'root', children:[], strength:Math.abs(b.net_shap) / tot};
    M.root.children.push(id);
    const ft = b.factors.reduce((s, f) => s + f.impact, 0) || 1;
    for (const f of b.factors) {
      const fid = 'f:' + b.group + ':' + f.feature, raises = f.effect.startsWith('raises');
      M[fid] = {id:fid, kind:'factor', label:f.label, value:f.value, effect:raises ? 'raises' : 'lowers',
                band:raises ? (b.band === 'Low' ? 'Medium' : b.band) : 'Low', parent:id, children:[], strength:f.impact / ft};
      M[id].children.push(fid);
    }
  }
  if (res.stage === 'stage1') for (const g of ['Funding', 'Traction']) {
    const id = 'x:' + g;
    M[id] = {id, kind:'locked', label:g, band:null, parent:'root', children:[], strength:.12};
    M.root.children.push(id);
  }
  return M;
}

/* ---------- layout: active centre, parent above, siblings to the sides, children below ---------- */
const W = 1000, H = 570, CX = 500, CY = 262, SLOTS = [320, 680, 185, 815, 70, 930];
function radius(n, role) {
  if (role === 'active') return n.kind === 'root' ? 72 : 64;
  if (role === 'parent') return 28;
  if (n.kind === 'locked') return 30;
  const s = Math.sqrt(n.strength);
  return role === 'child' ? 22 + 32 * s : 18 + 24 * s;
}
function layout(M, aid) {
  const a = M[aid], out = new Map();
  out.set(aid, {x:CX, y:CY, r:radius(a, 'active'), role:'active'});
  if (a.parent) {
    const p = M[a.parent];
    out.set(p.id, {x:CX, y:64, r:radius(p, 'parent'), role:'parent'});
    let i = 0;
    for (const sid of p.children) {
      if (sid === aid) continue;
      const x = SLOTS[i++];
      if (x !== undefined) out.set(sid, {x, y:CY, r:radius(M[sid], 'sib'), role:'sib'});
    }
  }
  const c = a.children;
  c.forEach((cid, i) => out.set(cid, {x:c.length === 1 ? CX : 150 + i * 700 / (c.length - 1), y:452, r:radius(M[cid], 'child'), role:'child'}));
  return out;
}
function wrap(s, max, lines) {
  const out = [''];
  for (const w of s.split(' ')) { const l = out[out.length - 1], t = (l + ' ' + w).trim(); if (t.length <= max) out[out.length - 1] = t; else out.push(w); }
  if (out.length > lines) { out.length = lines; out[lines - 1] = out[lines - 1].slice(0, max - 1) + '…'; }
  return out;
}

/* ---------- drawing ---------- */
const svg = document.getElementById('tree'), edgeLayer = el('g'), nodeLayer = el('g');
svg.append(edgeLayer, nodeLayer);
let M, active = 'root', raf = 0, current = 'idea';
const cur = new Map(), nodes = new Map(), edges = new Map();

function subText(n) {
  if (n.kind === 'root') return 'Risk band: ' + n.band;
  if (n.kind === 'branch') return n.effect === 'raises' ? '▲ raises risk' : n.effect === 'lowers' ? '▼ lowers risk' : '● neutral';
  if (n.kind === 'factor') return (n.effect === 'raises' ? '↑ ' : '↓ ') + fmt(n.value);
  return 'unlocks at Level 2';
}
function ensureNode(id) {
  if (nodes.has(id)) return nodes.get(id);
  const n = M[id], g = el('g', {class:'node', tabindex:'0', role:'button'});
  g.dataset.id = id;
  const title = el('title'); title.textContent = n.label;
  g.append(title, el('circle'), el('text', {class:'gl'}), el('text', {class:'lb'}), el('text', {class:'sb'}));
  g.addEventListener('click', () => select(id));
  g.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(id); } });
  nodeLayer.append(g); nodes.set(id, g);
  return g;
}
function setRole(id, role) {
  const g = ensureNode(id), n = M[id];
  if (g.dataset.role === role) return;
  g.dataset.role = role;
  const col = n.kind === 'locked' ? '#5E616D' : BC[n.band], c = g.querySelector('circle');
  c.setAttribute('stroke', col);
  c.setAttribute('fill', n.kind === 'locked' ? 'none' : col);
  c.setAttribute('fill-opacity', role === 'active' ? '.3' : '.2');
  c.setAttribute('stroke-width', role === 'active' ? '5' : '3');
  if (n.kind === 'locked') c.setAttribute('stroke-dasharray', '5 6');
  const gl = g.querySelector('.gl');
  gl.textContent = n.kind === 'locked' ? '🔒' : n.kind === 'factor' ? (n.effect === 'raises' ? '↑' : '↓') : GL[n.band];
  const lb = g.querySelector('.lb'), sb = g.querySelector('.sb');
  lb.replaceChildren(); sb.textContent = role === 'parent' ? '' : subText(n);
  const lines = role === 'parent' ? [short(n.label)] : wrap(short(n.label), role === 'active' ? 30 : role === 'child' ? 20 : 15, 2);
  lines.forEach((t, i) => { const s = el('tspan'); s.textContent = t; s.dataset.i = i; lb.append(s); });
  g.setAttribute('aria-label', `${n.label}${n.band ? ', ' + n.band : ''}. ${n.kind === 'locked' ? 'Locked until Level 2.' : role === 'active' ? 'Selected.' : 'Press Enter to move here.'}`);
  if (role === 'active') g.setAttribute('aria-current', 'true'); else g.removeAttribute('aria-current');
}
function place(id, s) {
  const g = nodes.get(id), role = g.dataset.role, r = s.r, lb = g.querySelector('.lb'), sb = g.querySelector('.sb');
  g.setAttribute('transform', `translate(${s.x.toFixed(1)} ${s.y.toFixed(1)})`);
  g.style.opacity = s.op.toFixed(3);
  g.querySelector('circle').setAttribute('r', Math.max(r, 0).toFixed(1));
  const gl = g.querySelector('.gl'); gl.setAttribute('font-size', (r * .72).toFixed(1)); gl.setAttribute('y', (r * .26).toFixed(1));
  const lh = role === 'active' ? 24 : 17;
  if (role === 'parent') { lb.setAttribute('x', r + 12); lb.setAttribute('y', 6); lb.setAttribute('text-anchor', 'start'); }
  else { lb.setAttribute('x', 0); lb.setAttribute('y', (r + 24).toFixed(1)); lb.setAttribute('text-anchor', 'middle'); }
  lb.querySelectorAll('tspan').forEach((t, i) => { t.setAttribute('x', lb.getAttribute('x')); t.setAttribute('dy', i ? lh : 0); });
  sb.setAttribute('x', 0); sb.setAttribute('text-anchor', 'middle');
  sb.setAttribute('y', (r + 24 + lh * lb.querySelectorAll('tspan').length + 2).toFixed(1));
}
function edge(id, a, b) {
  const n = M[id];
  let p = edges.get(id);
  if (!p) { p = el('path', {fill:'none', 'stroke-linecap':'round'}); edgeLayer.append(p); edges.set(id, p); }
  const my = (a.y + b.y) / 2;
  p.setAttribute('d', `M${a.x.toFixed(1)} ${a.y.toFixed(1)} C${a.x.toFixed(1)} ${my.toFixed(1)} ${b.x.toFixed(1)} ${my.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`);
  if (n.kind === 'locked') { p.setAttribute('stroke', '#5E616D'); p.setAttribute('stroke-width', '2'); p.setAttribute('stroke-dasharray', '6 7'); }
  else { p.setAttribute('stroke', BC[n.band]); p.setAttribute('stroke-width', (1.5 + 9 * n.strength).toFixed(1)); }
  p.setAttribute('opacity', (Math.min(a.op, b.op) * (n.kind === 'locked' ? .6 : .55)).toFixed(3));
}
function draw() {
  for (const [id, s] of cur) place(id, s);
  const live = new Set();
  for (const [id, s] of cur) { const par = M[id].parent; if (par && cur.has(par)) { edge(id, cur.get(par), s); live.add(id); } }
  for (const [id, p] of edges) if (!live.has(id)) { p.remove(); edges.delete(id); }
}

/* ---------- motion: glide the chosen node to the centre ---------- */
function go(id, instant) {
  const prev = cur.get(active) || {x:CX, y:CY, r:60}, tgt = layout(M, id), start = new Map();
  active = id;
  for (const [nid, t] of tgt) {
    if (!cur.has(nid)) cur.set(nid, {x:prev.x, y:prev.y, r:4, op:0});
    start.set(nid, {...cur.get(nid)}); setRole(nid, t.role);
  }
  const leaving = [...cur.keys()].filter(k => !tgt.has(k));
  for (const k of leaving) start.set(k, {...cur.get(k)});
  const dur = instant || reduce.matches ? 0 : 650, t0 = performance.now();
  cancelAnimationFrame(raf);
  const step = now => {
    const u = dur ? Math.min(1, (now - t0) / dur) : 1, e = u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
    for (const [nid, t] of tgt) { const s = start.get(nid), c = cur.get(nid); c.x = s.x + (t.x - s.x) * e; c.y = s.y + (t.y - s.y) * e; c.r = s.r + (t.r - s.r) * e; c.op = s.op + (1 - s.op) * e; }
    for (const k of leaving) { const s = start.get(k), c = cur.get(k); c.x = s.x + (CX - s.x) * e; c.y = s.y + (CY - s.y) * e; c.r = s.r * (1 - .7 * e); c.op = s.op * (1 - e); }
    draw();
    if (u < 1) raf = requestAnimationFrame(step);
    else { for (const k of leaving) { cur.delete(k); nodes.get(k)?.remove(); nodes.delete(k); } draw(); }
  };
  if (dur) raf = requestAnimationFrame(step); else step(t0);
  renderDetail(id); markOutline(id);
}
function select(id) {
  if (M[id].kind === 'locked') { renderDetail(id); return; }
  if (id !== active) go(id);
}
svg.addEventListener('keydown', e => {
  if ((e.key === 'ArrowUp' || e.key === 'Backspace') && M[active].parent) { e.preventDefault(); select(M[active].parent); nodes.get(M[active].parent)?.focus(); }
  if (e.key === 'Home') { e.preventDefault(); select('root'); }
});

/* ---------- detail panel and outline ---------- */
function renderDetail(id) {
  const n = M[id], res = DATA[current], box = document.getElementById('detail'), pct = Math.round(n.strength * 100);
  const chip = n.band ? `<span class="band ${n.band.toLowerCase()}">${GL[n.band]} ${n.band}</span>` : '<span class="chip">Locked</span>';
  let h = `<div class="eyebrow">${esc({root:'Your startup', branch:'Branch', factor:'Factor', locked:'Locked branch'}[n.kind])}</div><h2 class="display h4">${esc(short(n.label))}</h2><div class="row">${chip}`;
  if (n.kind === 'root') {
    h += `<span class="chip">Confidence: ${esc(res.confidence)}</span></div><p>About <b>${inN(res.similar_startups_failure_rate)}</b> startups like yours closed.</p>`
      + `<p class="muted">Across everything in the data, about ${Math.round(res.base_failure_rate * 100)}% closed. This is a pattern in old data, not a forecast.</p>`;
  } else if (n.kind === 'branch') {
    h += '</div><p>' + (n.effect === 'neutral' ? 'Barely moves the result either way.' : `Pushes risk ${n.effect === 'raises' ? 'up' : 'down'}. About <b>${pct}%</b> of the total push in this tree.`) + '</p>';
    if (!n.children.length) h += '<p class="muted">Nothing inside this branch stands out.</p>';
  } else if (n.kind === 'factor') {
    h += `<span class="chip">${esc(fmt(n.value))}</span></div><p>${n.effect === 'raises' ? 'Raises' : 'Lowers'} risk. About <b>${pct}%</b> of this branch's push.</p>`;
    if (/relationships/i.test(n.label)) h += '<p class="muted">Part of this signal may be success showing up after the fact.</p>';
  } else {
    h += '</div><p>This branch needs funding and traction details. Add them at Level 2 to unlock it.</p><button class="btn btn-ghost" disabled>Sharpen your read (not wired in the prototype)</button>';
  }
  if (n.kind === 'branch' && n.children.length) h += '<p class="muted">Click a factor below to see what is behind it.</p>';
  box.innerHTML = h;
}
function buildOutline() {
  const mk = id => {
    const n = M[id], locked = n.kind === 'locked';
    const dot = n.band ? `<i class="dot" style="background:${BC[n.band]}"></i>` : '<i class="dot ghost"></i>';
    const eff = n.kind === 'locked' ? 'unlocks at Level 2' : n.kind === 'root' ? n.band : n.effect;
    let s = `<li><button class="ol-btn" data-id="${esc(id)}"${locked ? ' aria-disabled="true"' : ''}>${dot}<span>${esc(short(n.label))}</span><em>${esc(eff)}</em></button>`;
    if (n.children.length) s += '<ul>' + n.children.map(mk).join('') + '</ul>';
    return s + '</li>';
  };
  const o = document.getElementById('outline');
  o.innerHTML = mk('root');
  o.querySelectorAll('.ol-btn').forEach(b => b.addEventListener('click', () => select(b.dataset.id)));
}
function markOutline(id) {
  document.querySelectorAll('.ol-btn').forEach(b => b.dataset.id === id ? b.setAttribute('aria-current', 'true') : b.removeAttribute('aria-current'));
}

/* ---------- samples ---------- */
function load(key) {
  current = key; M = DATA[key].model = buildModel(DATA[key]);
  cancelAnimationFrame(raf);
  cur.clear(); edges.clear(); nodes.clear(); edgeLayer.replaceChildren(); nodeLayer.replaceChildren(); active = 'root';
  document.querySelectorAll('.tabs button').forEach(b => b.setAttribute('aria-pressed', b.dataset.key === key));
  document.getElementById('lvl').textContent = DATA[key].stage === 'stage1' ? 'Level 1: idea only' : 'Level 2: funding and traction';
  buildOutline(); go('root', true);
}
document.querySelectorAll('.tabs button').forEach(b => b.addEventListener('click', () => load(b.dataset.key)));
load('idea');
})();
