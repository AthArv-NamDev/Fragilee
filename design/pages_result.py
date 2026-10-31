from common import *

META = SAMPLES["meta"]["stages"]
EXTRA = r"""
.crumbs{font-size:13px;color:var(--muted);margin:6px 0 18px}.crumbs b{color:var(--text);font-weight:500}
.titlerow{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;margin-bottom:26px}
.titlerow>div:first-child{flex:1;min-width:0}.titlerow .chips{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
.titlerow .actions{display:flex;gap:10px;flex:none}
.grid{display:flex;gap:20px;align-items:stretch}
.hero-card{width:350px;flex:none;display:flex;flex-direction:column;align-items:center;text-align:center;padding:30px 26px}
.hero-card .say{font-family:var(--display);font-size:27px;line-height:1.1;letter-spacing:-.02em;margin-top:18px}
.hero-card .sub{color:var(--muted);font-size:13.5px;margin-top:10px}
.hero-card .kvs{width:100%;margin-top:22px;text-align:left}
.tree-card{flex:1;padding:22px 24px 14px}
.tree-head{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:4px}.tree-head .h4{flex:1}.tree-head .legend{flex:none;white-space:nowrap}.legend span{white-space:nowrap}
.hint{font-size:12.5px;color:var(--faint);text-align:center;padding:2px 0 8px}
.row2{display:flex;gap:20px;margin-top:20px;align-items:flex-start}
.push{flex:1.15}.read{flex:1}
.brow{padding:16px 0;border-bottom:1px solid var(--line)}.brow:last-child{border-bottom:0}
.bhead{display:flex;align-items:center;gap:12px}
.bhead .name{font-family:var(--display);font-size:18px;letter-spacing:-.01em;flex:1}
.bar{height:7px;border-radius:7px;background:var(--surface-2);margin:10px 0 8px;overflow:hidden}.bar i{display:block;height:100%;border-radius:7px}
.fac{display:flex;justify-content:space-between;gap:14px;font-size:13.5px;color:var(--muted);padding:3px 0}.fac b{color:var(--text);font-weight:500}
.up{color:var(--high)}.down{color:var(--low)}
.read ul{list-style:none;margin-top:12px}.read li{padding:10px 0 10px 22px;position:relative;font-size:14px;color:var(--muted);border-bottom:1px solid var(--line)}
.read li:last-child{border-bottom:0}.read li::before{content:"";position:absolute;left:2px;top:17px;width:8px;height:8px;border-radius:50%;background:var(--violet)}
.rates{display:flex;gap:8px;margin:14px 0 4px}.rates div{flex:1;background:var(--surface-2);border-radius:12px;padding:10px 8px;text-align:center}
.rates b{display:block;font-family:var(--display);font-size:20px;letter-spacing:-.01em}.rates span{font-size:11px;color:var(--muted)}
.cta{margin-top:20px;width:100%;text-align:left}
.cta .btn{width:100%;justify-content:center}.cta .h4{margin-bottom:4px}.cta p{font-size:13.5px;color:#C9C3F0;margin-bottom:12px}
"""


def effect_html(f):
    cls, arrow = ("up", "▲") if f["effect"] == "raises risk" else ("down", "▼")
    return f'<div class="fac"><span><span class="{cls}">{arrow}</span> {f["label"]}</span><b class="num">{f["value"]}</b></div>'


def result_page(key, title, level):
    r = SAMPLES[key]
    stage = r["stage"]
    band = r["band"]
    rate = r["similar_startups_failure_rate"]
    share = branch_share(r["tree"]["children"])
    rates = META[stage]["observed_failure_rate_by_band"]
    chips = [f'<span class="chip violet">Level {level} · {"Your idea" if level == 1 else "Funding details"}</span>',
             f'<span class="chip">Confidence: {r["confidence"].capitalize()}</span>']
    if level == 2:
        chips.append('<span class="chip" title="Trained on US startups">US benchmark</span>')
    branches = ""
    for b in sorted(r["tree"]["children"], key=lambda b: -b["net_shap"]):
        col = BAND_COLOR[b["band"]]
        eff = {"raises": '<span class="up">▲ raises risk</span>', "lowers": '<span class="down">▼ lowers risk</span>', "neutral": "● neutral"}[b["effect"]]
        facs = "".join(effect_html(f) for f in b["factors"]) or '<div class="fac"><span>Nothing here moves the needle for this startup.</span></div>'
        branches += (f'<div class="brow"><div class="bhead"><span class="name">{b["label"]}</span><span class="muted" style="font-size:12.5px">{eff}</span>'
                     f'{band_badge(b["band"])}</div><div class="bar"><i style="width:{max(share[b["group"]] * 100, 3):.0f}%;background:{col}"></i></div>{facs}</div>')
    if stage == "stage1":
        plain = ["Built on 10,941 startups that either closed or were acquired. It only knows country and industry, so the read is deliberately modest.",
                 "Tested on startups it had never seen, it ranked the riskier of two startups correctly about 2 times in 3.",
                 "The data is a 2013-era snapshot of startups that raised funding. Startups still operating are not in it."]
    else:
        plain = ["Built on 922 US startups that either closed or were acquired.",
                 "Tested on startups it had never seen, it ranked the riskier of two startups correctly about 4 times in 5.",
                 "Business relationships is the strongest signal, and part of it may reflect success after the fact.",
                 "The data is a 2013-era snapshot and only includes startups with a final outcome."]
    limits = "".join(f"<li>{x}</li>" for x in plain)
    rate_boxes = "".join(f'<div><b style="color:{BAND_TEXT[k]}">{v * 100:.0f}%</b><span>{BAND_GLYPH[k]} {k}</span></div>' for k, v in rates.items())
    cta = ""
    if level == 1:
        cta = ('<div class="callout cta"><div class="h4 display">Level up</div><p>Idea-stage reads are deliberately modest. Add funding and traction details and the picture gets a lot sharper.</p>'
               '<button class="btn btn-primary">Sharpen this read</button></div>')
    body = (app_topbar("Analyses") + '<main class="container" style="padding-bottom:70px">'
            '<div class="crumbs">Analyses &nbsp;/&nbsp; <b>' + title + '</b></div>'
            f'<div class="titlerow"><div><h1 class="display h3" style="font-size:34px">{title}</h1><div class="chips">{"".join(chips)}</div></div>'
            '<div class="actions"><button class="btn btn-ghost">Save as new version</button><button class="btn btn-ghost">Delete</button></div></div>'
            '<section class="grid">'
            f'<div class="card hero-card">{ring(band, 176, 13)}'
            f'<div class="say">About {in_n(rate)} startups like yours closed</div>'
            f'<div class="sub">That is the observed rate for startups in the {band} band: {rate * 100:.0f}% of them closed.</div>'
            f'<div class="kvs"><div class="kv"><span>Confidence</span><span>{r["confidence"].capitalize()}</span></div>'
            f'<div class="kv"><span>Compared with</span><span>{"10,941" if stage == "stage1" else "922"} startups</span></div>'
            f'<div class="kv"><span>Data from</span><span>2013-era snapshot</span></div></div>{cta}</div>'
            '<div class="card tree-card"><div class="tree-head"><div class="h4 display">Where the pressure comes from</div>'
            '<div class="legend"><span>Size = strength of push</span><span>Colour = severity</span></div></div>'
            f'{tree_svg(r)}<div class="hint">Click a branch to dive in. Click the startup to come back up.</div></div></section>'
            '<section class="row2">'
            f'<div class="card push"><div class="h4 display">What is pushing the risk</div><p class="muted" style="font-size:13.5px;margin-top:4px">Ranked, strongest first.</p><div style="margin-top:8px">{branches}</div></div>'
            f'<div class="card read"><div class="h4 display">How to read this</div><p class="muted" style="font-size:13.5px;margin-top:4px">A pattern-finder, not a fortune teller.</p>'
            f'<div class="rates">{rate_boxes}</div><div class="muted" style="font-size:12px;margin-bottom:6px">Share of startups that closed in each band, in our data.</div><ul>{limits}<li>{r["disclaimer"]}</li></ul></div>'
            '</section></main>')
    return page(f"Fragilee · {title}", body, EXTRA)


if __name__ == "__main__":
    import os
    out = os.path.join(HERE, "out"); os.makedirs(out, exist_ok=True)
    open(f"{out}/v2-result.html", "w").write(result_page("stage2_high", "Coffee-delivery app", 2))
    open(f"{out}/v2-result-level1.html", "w").write(result_page("stage1", "Coffee-delivery idea", 1))
    print("ok")
