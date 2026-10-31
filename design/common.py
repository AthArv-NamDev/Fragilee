"""Shared design system for the Fragilee v2 mockups: tokens, components and small HTML helpers."""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = json.load(open(os.path.join(HERE, "samples.json")))
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">')

BAND_COLOR = {"Low": "#6FBFA0", "Medium": "#D9A441", "High": "#E0784F", "Critical": "#B14C63"}
BAND_TEXT = {"Low": "#6FBFA0", "Medium": "#D9A441", "High": "#E0784F", "Critical": "#E89AAA"}
BAND_GLYPH = {"Low": "●", "Medium": "▲", "High": "◆", "Critical": "✦"}
BAND_FILL = {"Low": 0.25, "Medium": 0.5, "High": 0.75, "Critical": 1.0}

CSS = r"""
:root{
  --bg:#14151C; --surface:#1B1D27; --surface-2:#22242F; --line:rgba(220,225,232,.09); --line-2:rgba(220,225,232,.18);
  --text:#DCE1E8; --muted:#8A8D99; --faint:#5E616D;
  --violet:#7C6FCF; --violet-soft:rgba(124,111,207,.16); --violet-text:#B7AEEA;
  --sage:#8FBF6B; --sage-ink:#17240E;
  --low:#6FBFA0; --medium:#D9A441; --high:#E0784F; --critical:#B14C63; --critical-text:#E89AAA;
  --cream:#EDEAE2; --ink:#1E1B16;
  --r:16px; --r-lg:24px;
  --display:'Archivo Black','Arial Black',sans-serif; --body:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html{color-scheme:dark}
body{background:var(--bg);color:var(--text);font-family:var(--body);font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button{font-family:var(--body)}
.display{font-family:var(--display);font-weight:400;letter-spacing:-.02em;line-height:1.04}
.h1{font-size:62px}.h2{font-size:40px}.h3{font-size:26px}.h4{font-size:19px;letter-spacing:-.01em}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:600}
.muted{color:var(--muted)}.num{font-variant-numeric:tabular-nums}
.container{max-width:1120px;margin:0 auto;padding:0 32px}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:20px 0}
.wordmark{display:flex;align-items:center;gap:10px;font-family:var(--display);font-size:20px;letter-spacing:-.01em}
.nav{display:flex;gap:30px;font-size:14px;color:var(--muted)}.nav a{white-space:nowrap}.nav .on{color:var(--text)}
.avatar{width:34px;height:34px;border-radius:50%;background:var(--violet);color:#17141F;font-weight:700;font-size:13px;display:flex;align-items:center;justify-content:center}
.btn,.tagchip{flex:none}.btn{display:inline-flex;align-items:center;gap:8px;padding:12px 22px;border-radius:999px;font-weight:600;font-size:14px;border:1.5px solid transparent;cursor:pointer;transition:transform .15s ease,background .15s ease,border-color .15s ease}
.btn:hover{transform:translateY(-1px)}
.btn-primary{background:var(--sage);color:var(--sage-ink)}
.btn-ghost{border-color:var(--line-2);color:var(--text);background:transparent}
.btn-ghost:hover{border-color:var(--violet)}
.btn-quiet{color:var(--muted);background:none;padding:12px 10px}
.btn-danger{border-color:rgba(177,76,99,.5);color:var(--critical-text);background:transparent}
.btn[disabled]{opacity:.35;cursor:not-allowed;transform:none}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;font-size:12px;font-weight:500;background:var(--surface-2);color:var(--muted);border:1px solid var(--line);white-space:nowrap}
.chip.violet{background:var(--violet-soft);color:var(--violet-text);border-color:rgba(124,111,207,.32)}
.band{display:inline-flex;align-items:center;gap:7px;padding:5px 12px;border-radius:999px;font-size:12px;font-weight:600}
.band.low{background:rgba(111,191,160,.14);color:var(--low)}.band.medium{background:rgba(217,164,65,.14);color:var(--medium)}
.band.high{background:rgba(224,120,79,.14);color:var(--high)}.band.critical{background:rgba(177,76,99,.16);color:var(--critical-text)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:24px}
.callout{background:var(--violet-soft);border:1px solid rgba(124,111,207,.28);border-radius:14px;padding:16px 18px;font-size:14px;color:#C9C3F0}
hr.sep{border:0;border-top:1px solid var(--line);margin:0}
.kv{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid var(--line);font-size:14px}.kv:last-child{border-bottom:0}
.kv span:first-child{color:var(--muted)}
.opt{display:block;text-align:left;width:100%;background:var(--surface);border:1.5px solid var(--line-2);border-radius:18px;padding:22px;color:var(--text);cursor:pointer;transition:transform .15s ease,border-color .15s ease,background .15s ease}
.opt:hover{border-color:var(--violet);transform:translateY(-2px)}
.opt .t{font-family:var(--display);font-size:21px;letter-spacing:-.01em;line-height:1.15}
.opt .s{font-size:13px;color:var(--muted);margin-top:6px}
.opt.sel{background:var(--violet-soft);border-color:var(--violet)}
.tagchip{display:inline-flex;align-items:center;gap:8px;padding:11px 18px;border-radius:999px;border:1.5px solid var(--line-2);background:var(--surface);color:var(--text);font-size:15px;font-weight:500;cursor:pointer;transition:border-color .15s ease,background .15s ease}
.tagchip:hover{border-color:var(--violet)}.tagchip.sel{background:var(--violet-soft);border-color:var(--violet);color:#fff}
.progress{display:flex;gap:6px}.progress i{flex:1;height:5px;border-radius:5px;background:var(--surface-2)}.progress i.done{background:var(--violet)}.progress i.now{background:var(--sage)}
.input{width:100%;background:var(--surface);border:1.5px solid var(--line-2);border-radius:14px;padding:16px 18px;color:var(--text);font-size:18px;outline:none;font-family:var(--body)}
.input:focus{border-color:var(--sage)}
.stepper{display:inline-flex;align-items:center;gap:18px}
.stepper button{width:54px;height:54px;border-radius:50%;border:1.5px solid var(--line-2);background:var(--surface);color:var(--text);font-size:24px;cursor:pointer}
.stepper button:hover{border-color:var(--violet)}
.stepper .v{font-family:var(--display);font-size:54px;min-width:90px;text-align:center;letter-spacing:-.02em}
.switch{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 20px;border:1.5px solid var(--line-2);border-radius:16px;background:var(--surface);cursor:pointer;width:100%;color:var(--text);font-size:16px;font-weight:500;text-align:left}
.switch .k{width:44px;height:26px;border-radius:99px;background:var(--surface-2);position:relative;flex:none;border:1px solid var(--line-2)}
.switch .k::after{content:"";position:absolute;left:3px;top:3px;width:18px;height:18px;border-radius:50%;background:#aab;transition:transform .2s ease}
.switch.sel{border-color:var(--violet);background:var(--violet-soft)}.switch.sel .k{background:var(--sage)}.switch.sel .k::after{transform:translateX(18px);background:#fff}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--muted)}.legend span{display:inline-flex;align-items:center;gap:6px}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
@media screen and (max-width:860px){.h1{font-size:40px}.h2{font-size:30px}.container{padding:0 20px}.nav{display:none}}
"""

MARK = ('<svg width="26" height="26" viewBox="0 0 100 100" aria-hidden="true"><polygon points="50,12 80,30 80,70 50,88 20,70 20,30" '
        'fill="none" stroke="#3a3d4d" stroke-width="5"/><path d="M50 12 L58 42 L42 50 L60 68 L50 88" fill="none" stroke="#7C6FCF" '
        'stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="58" cy="42" r="4.5" fill="#B7AEEA"/></svg>')
WORDMARK = f'<a class="wordmark" href="#">{MARK}<span>Fragilee</span></a>'


def page(title, body, extra_css="", extra_head="", script=""):
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title>{FONTS}<style>{CSS}{extra_css}</style>{extra_head}</head><body>{body}'
            f'{("<script>" + script + "</script>") if script else ""}</body></html>')


def app_topbar(active="Analyses"):
    links = "".join(f'<a class="{"on" if n == active else ""}" href="#">{n}</a>' for n in ("Analyses", "New analysis", "How to read this"))
    return f'<div class="container"><header class="topbar">{WORDMARK}<nav class="nav">{links}</nav><div class="avatar">JS</div></header></div>'


def band_badge(band):
    return f'<span class="band {band.lower()}">{BAND_GLYPH[band]} {band}</span>'


def ring(band, size=150, stroke=11, word=True, glyph_only=False):
    """The band ring: the arc fills 1/4, 2/4, 3/4 or all of the circle for Low, Medium, High, Critical."""
    r = (size - stroke) / 2
    c = 2 * math.pi * r
    dash = c * BAND_FILL[band]
    cx = size / 2
    centre = (f'<text x="{cx}" y="{cx + size * 0.09}" text-anchor="middle" font-size="{size * 0.26}" fill="{BAND_TEXT[band]}">{BAND_GLYPH[band]}</text>'
              if glyph_only else
              f'<text x="{cx}" y="{cx + size * 0.075}" text-anchor="middle" font-family="Archivo Black, Arial Black, sans-serif" font-size="{size * 0.2}" fill="#DCE1E8">{band}</text>'
              f'<text x="{cx}" y="{cx + size * 0.21}" text-anchor="middle" font-size="{size * 0.072}" fill="#8A8D99" letter-spacing="1.2">RISK BAND</text>')
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="Risk band: {band}">'
            f'<circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="rgba(220,225,232,.1)" stroke-width="{stroke}"/>'
            f'<circle cx="{cx}" cy="{cx}" r="{r}" fill="none" stroke="{BAND_COLOR[band]}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-dasharray="{dash:.1f} {c:.1f}" transform="rotate(-90 {cx} {cx})"/>{centre}</svg>')


NEAREST = [(.1, "1 in 10"), (.2, "1 in 5"), (.25, "1 in 4"), (.33, "1 in 3"), (.4, "2 in 5"), (.5, "1 in 2"),
           (.6, "3 in 5"), (.67, "2 in 3"), (.75, "3 in 4"), (.8, "4 in 5"), (.9, "9 in 10")]


def in_n(rate):
    """0.37 -> '2 in 5': the catchy way to say an observed rate."""
    return min(NEAREST, key=lambda p: abs(p[0] - rate))[1]


# ---- the plex tree, drawn statically (the interactive version is in the prototype) --------------
def branch_share(branches):
    total = sum(abs(b["net_shap"]) for b in branches) or 1
    return {b["group"]: abs(b["net_shap"]) / total for b in branches}


def curve(x1, y1, x2, y2):
    my = (y1 + y2) / 2
    return f"M{x1:.1f} {y1:.1f} C{x1:.1f} {my:.1f} {x2:.1f} {my:.1f} {x2:.1f} {y2:.1f}"


ORDER = ["Funding", "Traction", "Market", "Location"]


def tree_svg(result, width=1000, height=470, active=None):
    """Root-active layout: the startup on top, its four branches fanned out below.
    Branches the current level cannot see yet are drawn as locked ghosts."""
    band = result["band"]
    by = {b["group"]: b for b in result["tree"]["children"]}
    share = branch_share(result["tree"]["children"])
    root = (width / 2, 130)
    xs = [width * (i + 1) / (len(ORDER) + 1) for i in range(len(ORDER))]
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img" aria-label="Risk tree">']
    for g, x in zip(ORDER, xs):
        if g in by:
            w = 1.5 + 9 * share[g]
            out.append(f'<path d="{curve(root[0], root[1], x, 360)}" fill="none" stroke="{BAND_COLOR[by[g]["band"]]}" stroke-width="{w:.1f}" opacity=".55" stroke-linecap="round"/>')
        else:
            out.append(f'<path d="{curve(root[0], root[1], x, 360)}" fill="none" stroke="#5E616D" stroke-width="2" stroke-dasharray="6 7" opacity=".6"/>')
    out.append(f'<circle cx="{root[0]}" cy="{root[1]}" r="74" fill="#1B1D27" stroke="{BAND_COLOR[band]}" stroke-width="5"/>')
    out.append(f'<text x="{root[0]}" y="{root[1] - 2}" text-anchor="middle" font-family="Archivo Black, Arial Black, sans-serif" font-size="19" fill="#DCE1E8">Your startup</text>')
    out.append(f'<text x="{root[0]}" y="{root[1] + 20}" text-anchor="middle" font-size="15" font-weight="600" fill="{BAND_TEXT[band]}">{BAND_GLYPH[band]} {band}</text>')
    for g, x in zip(ORDER, xs):
        if g not in by:
            out.append(f'<circle cx="{x:.1f}" cy="360" r="34" fill="none" stroke="#5E616D" stroke-width="2.5" stroke-dasharray="5 6"/>')
            out.append(f'<text x="{x:.1f}" y="368" text-anchor="middle" font-size="20" fill="#8A8D99">&#128274;</text>')
            out.append(f'<text x="{x:.1f}" y="{360 + 34 + 28}" text-anchor="middle" font-family="Archivo Black, Arial Black, sans-serif" font-size="21" fill="#5E616D">{g}</text>')
            out.append(f'<text x="{x:.1f}" y="{360 + 34 + 50}" text-anchor="middle" font-size="15" fill="#5E616D">unlocks at Level 2</text>')
            continue
        b = by[g]
        r = 24 + 46 * math.sqrt(share[g])
        col = BAND_COLOR[b["band"]]
        out.append(f'<circle cx="{x:.1f}" cy="360" r="{r:.1f}" fill="{col}" fill-opacity=".22" stroke="{col}" stroke-width="3"/>')
        out.append(f'<text x="{x:.1f}" y="367" text-anchor="middle" font-size="{22 if r > 34 else 16}" font-weight="700" fill="#fff">{BAND_GLYPH[b["band"]]}</text>')
        out.append(f'<text x="{x:.1f}" y="{360 + r + 28:.1f}" text-anchor="middle" font-family="Archivo Black, Arial Black, sans-serif" font-size="21" fill="#DCE1E8">{b["label"]}</text>')
        arrow = {"raises": "&#9650; raises risk", "lowers": "&#9660; lowers risk", "neutral": "&#9679; neutral"}[b["effect"]]
        out.append(f'<text x="{x:.1f}" y="{360 + r + 50:.1f}" text-anchor="middle" font-size="15" fill="#8A8D99">{arrow}</text>')
    out.append("</svg>")
    return "".join(out)
