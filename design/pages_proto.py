"""Builds the two v2 review pages: the interactive plex-tree prototype and the design-system page.
Run: python3 pages_proto.py   (writes out/v2-plex-tree.html and out/v2-design-system.html)"""
import json, os
from common import *

OUT = os.path.join(HERE, "out")
rd = lambda n: open(os.path.join(HERE, n), encoding="utf-8").read()

# ---------- 1. plex tree prototype ----------
KEEP = ("stage", "band", "probability", "similar_startups_failure_rate", "base_failure_rate", "confidence", "tree")
DATA = {k: {key: SAMPLES[s][key] for key in KEEP} for k, s in (("idea", "stage1"), ("mixed", "stage2"), ("critical", "stage2_high"))}
js = rd("plex.js").replace("/*DATA*/", json.dumps(DATA, separators=(",", ":")))
body = f'''<div class="container">
<header class="topbar">{WORDMARK}<span class="chip violet">Prototype: real API responses, no backend</span></header>
<div class="hero"><h1 class="display h2">The plex tree</h1>
<p class="muted">Click any node and it glides to the centre; its parent sits above, its siblings to the sides, its children below. Bigger node, stronger push. Thicker link, stronger push.</p></div>
<div class="tabs" role="group" aria-label="Sample result">
<button data-key="idea">Idea stage (Low)</button><button data-key="mixed">Funding stage (mixed, High)</button><button data-key="critical">Funding stage (Critical)</button></div>
<div class="proto"><div><div class="card stage"><svg id="tree" viewBox="0 0 1000 570" role="group" aria-label="Risk tree. The outline list on the right has the same content in order."></svg></div>
<p class="hint muted">Enter or Space moves a focused node to the centre. Up arrow goes to the parent, Home goes to the top. <span id="lvl"></span>.</p>
<div class="legend hint"><span><i class="dot" style="background:var(--low)"></i>Low</span><span><i class="dot" style="background:var(--medium)"></i>Medium</span><span><i class="dot" style="background:var(--high)"></i>High</span><span><i class="dot" style="background:var(--critical)"></i>Critical</span><span>Size and thickness show strength</span></div></div>
<div class="panel"><div class="card" id="detail" aria-live="polite"></div><div class="card"><div class="eyebrow" style="margin-bottom:8px">Outline</div><nav aria-label="Risk tree outline"><ul class="ol" id="outline"></ul></nav></div></div></div>
<div class="foot muted">Limits, plainly: the data is a 2013-era snapshot of startups that ended as closed or acquired, so this shows patterns, not what will happen to yours. Idea-stage results are modest.</div></div>'''
open(os.path.join(OUT, "v2-plex-tree.html"), "w", encoding="utf-8").write(page("Fragilee: plex tree prototype", body, rd("plex.css"), "", js))
print("wrote plex tree")

# ---------- 2. design-system v2 page ----------
def lum(h):
    c = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
def cr(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + .05) / (lb + .05)
def blend(fg, a, bg):
    f = [int(fg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]; b = [int(bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02x%02x%02x" % tuple(round(a * x + (1 - a) * y) for x, y in zip(f, b))
BG, SF = "#14151C", "#1B1D27"
violet_soft = blend("#7C6FCF", .16, SF)
swatches = [  # name, hex, text-on, role
    ("Night", BG, "#DCE1E8", "Page"), ("Surface", SF, "#DCE1E8", "Cards"), ("Text", "#DCE1E8", BG, "Body text"),
    ("Muted", "#8A8D99", BG, "Secondary text"), ("Violet", "#7C6FCF", "#17141F", "Selection, focus"), ("Sage", "#8FBF6B", "#17240E", "Primary action"),
    ("Low", "#6FBFA0", BG, "Band"), ("Medium", "#D9A441", BG, "Band"), ("High", "#E0784F", BG, "Band"), ("Critical", "#B14C63", "#fff", "Band fill"),
    ("Critical text", "#E89AAA", BG, "Band as text")]
sw = "".join(f'<div class="sw"><div class="chipc" style="background:{h};color:{t}">Aa</div><div><b>{n}</b><br><span class="muted num">{h}</span><br><span class="muted">{r}</span></div></div>' for n, h, t, r in swatches)
pairs = [("Text on Night", "#DCE1E8", BG), ("Text on Surface", "#DCE1E8", SF), ("Muted on Night", "#8A8D99", BG), ("Muted on Surface", "#8A8D99", SF),
         ("Faint on Night", "#5E616D", BG), ("Low on Surface", "#6FBFA0", SF), ("Medium on Surface", "#D9A441", SF), ("High on Surface", "#E0784F", SF),
         ("Critical on Surface (raw)", "#B14C63", SF), ("Critical text on Surface", "#E89AAA", SF), ("Violet text on selected card", "#B7AEEA", violet_soft),
         ("Sage button label", "#17240E", "#8FBF6B")]
def verdict(x): return "AA text" if x >= 4.5 else ("large text and graphics only" if x >= 3 else "decoration only")
rows = "".join(f'<div class="kv"><span>{n}</span><span class="num">{cr(a, b):.1f} : 1 &nbsp; <b>{verdict(cr(a, b))}</b></span></div>' for n, a, b in pairs)
rings = "".join(f'<div style="text-align:center">{ring(b, 120, 9)}<div style="margin-top:8px">{band_badge(b)}</div></div>' for b in ("Low", "Medium", "High", "Critical"))
def node(cx, cy, r, band, glyph, label, sub=""):
    c = BAND_COLOR[band]
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c}" fill-opacity=".22" stroke="{c}" stroke-width="3"/>'
            f'<text x="{cx}" y="{cy + r * .26:.0f}" text-anchor="middle" font-size="{r * .72:.0f}" font-weight="700" fill="#fff">{glyph}</text>'
            f'<text x="{cx}" y="{cy + r + 22}" text-anchor="middle" font-family="Archivo Black, Arial Black, sans-serif" font-size="14" fill="#DCE1E8">{label}</text>'
            f'<text x="{cx}" y="{cy + r + 40}" text-anchor="middle" font-size="12" fill="#8A8D99">{sub}</text>')
anat = ('<svg viewBox="0 0 760 210" width="100%" role="img" aria-label="Node anatomy">'
        + node(80, 70, 28, "Low", "↓", "Weak push", "small, thin link")
        + node(240, 70, 42, "Medium", "▲", "Medium push", "")
        + node(430, 70, 56, "High", "◆", "Strong push", "big, thick link")
        + node(620, 70, 28, "Low", "🔒", "Locked", "unlocks at Level 2").replace(f'fill="{BAND_COLOR["Low"]}" fill-opacity=".22" stroke="{BAND_COLOR["Low"]}" stroke-width="3"', 'fill="none" stroke="#5E616D" stroke-width="2.5" stroke-dasharray="5 6"') + "</svg>")
css = '''.sec{padding:34px 0;border-top:1px solid var(--line)}.sec>h2{margin-bottom:6px}.sec>p{max-width:62ch;margin-bottom:18px}
.grid{display:grid;gap:14px}.g3{grid-template-columns:repeat(auto-fill,minmax(210px,1fr))}.g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.sw{display:flex;gap:12px;align-items:center;font-size:13px;line-height:1.4}.chipc{width:56px;height:56px;border-radius:14px;display:flex;align-items:center;justify-content:center;font-family:var(--display);font-size:20px;flex:none;border:1px solid var(--line-2)}
.demo{display:flex;gap:12px;flex-wrap:wrap;align-items:center}.dd li{margin:0 0 8px 18px;font-size:14px}.dd{max-width:62ch}
.no{color:var(--critical-text)}.yes{color:var(--low)}.scale>div{padding:10px 0;border-bottom:1px solid var(--line);display:flex;gap:20px;align-items:baseline}.scale span:first-child{width:90px;font-size:12px;color:var(--muted);flex:none}'''
ds = f'''<div class="container"><header class="topbar">{WORDMARK}<span class="chip violet">Design system v2</span></header>
<div class="hero" style="padding:8px 0 28px"><h1 class="display h2">Calm, data first, a little wit</h1>
<p class="muted" style="max-width:60ch;margin-top:10px">Signal palette and Archivo Black plus Inter stay for now. What changes from v1: no tilted sticker logo, quieter surfaces, and colour that always comes with a glyph and a word.</p></div>
<section class="sec"><h2 class="display h3">Colour</h2><p class="muted">Band colours are the only place colour carries meaning. Violet means you chose it, sage means go.</p><div class="grid g3">{sw}</div>
<h3 class="display h4" style="margin:28px 0 8px">Contrast, measured from these hex values</h3><div class="card">{rows}</div>
<p class="muted" style="margin-top:10px;font-size:13px">Computed with the WCAG 2 formula. Not tested with real users or assistive tech.</p></section>
<section class="sec"><h2 class="display h3">Type</h2><p class="muted">Archivo Black for display, Inter for everything else. Never all-caps for body labels.</p><div class="scale card">
<div><span>H1 62</span><span class="display h1" style="font-size:48px">Risk, read plainly</span></div><div><span>H2 40</span><span class="display h2">Your idea</span></div><div><span>H3 26</span><span class="display h3">Sharpen your read</span></div>
<div><span>Body 15</span><span>About 2 in 5 startups like yours closed. That is a pattern in old data, not a forecast.</span></div><div><span>Small 13</span><span class="muted" style="font-size:13px">Confidence and limits sit in small, never hidden.</span></div></div></section>
<section class="sec"><h2 class="display h3">Risk bands</h2><p class="muted">Ring fill is a quarter, half, three quarters or full. Each band has a glyph, a colour and a word, so colour is never the only cue.</p><div class="demo" style="gap:36px">{rings}</div></section>
<section class="sec"><h2 class="display h3">Controls</h2><div class="grid g2"><div class="card"><div class="demo"><button class="btn btn-primary">Check my idea</button><button class="btn btn-ghost">Sharpen your read</button><button class="btn btn-quiet">Skip</button><button class="btn btn-danger">Delete</button><button class="btn btn-primary" disabled>Disabled</button></div>
<div class="demo" style="margin-top:18px"><span class="chip">Confidence: moderate</span><span class="chip violet">US benchmark</span><span class="chip">Level 1</span></div>
<div class="demo" style="margin-top:18px"><span class="tagchip">Software</span><span class="tagchip sel">Mobile</span><span class="tagchip">Health Care</span></div></div>
<div class="card"><div class="demo" style="display:grid;gap:12px"><button class="opt sel"><div class="t">United States</div><div class="s">Then we ask which state</div></button><input class="input" value="Fragilee" aria-label="Startup name"><div class="progress"><i class="done"></i><i class="done"></i><i class="now"></i><i></i></div></div></div></div></section>
<section class="sec"><h2 class="display h3">Plex tree anatomy</h2><p class="muted">Size is how hard a node pushes the result. Link thickness repeats it. Colour is the band. Factors show an arrow for the direction of the push. Locked branches are dashed ghosts, never hidden.</p><div class="card">{anat}</div></section>
<section class="sec"><h2 class="display h3">Motion</h2><ul class="dd"><li>Motion answers a click: a node glides to the centre in about 0.65 s, and nothing animates by itself.</li><li>With reduced motion on, the tree jumps with no glide.</li><li>Every node is reachable by keyboard, and an outline list carries the same content for phones and screen readers.</li></ul></section>
<section class="sec"><h2 class="display h3">Voice</h2><div class="grid g2"><div class="card"><b class="yes">Say</b><ul class="dd" style="margin-top:10px"><li>About 2 in 5 startups like yours closed.</li><li>This is a pattern in old data, not a forecast.</li><li>Unlocks at Level 2.</li></ul></div><div class="card"><b class="no">Do not say</b><ul class="dd" style="margin-top:10px"><li>Your startup will fail.</li><li>AUC, SHAP or probability scores on the main screen.</li><li>Anything that implies advice, or certainty.</li></ul></div></div></section>
<div class="foot muted" style="border-top:1px solid var(--line);padding:22px 0 40px;font-size:13px">Generated by pages_proto.py. Fonts load from Google Fonts, so open this online or the fallbacks show.</div></div>'''
open(os.path.join(OUT, "v2-design-system.html"), "w", encoding="utf-8").write(page("Fragilee: design system v2", ds, css))
print("wrote design system")
for n, a, b in pairs: print(f"{n:34s}{cr(a,b):5.1f}")
