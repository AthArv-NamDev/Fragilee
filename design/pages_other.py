from common import *

M1 = SAMPLES["meta"]["stages"]["stage1"]["observed_failure_rate_by_band"]
M2 = SAMPLES["meta"]["stages"]["stage2"]["observed_failure_rate_by_band"]

# ------------------------------------------------------------------ dashboard
DASH_CSS = r"""
.head{display:flex;justify-content:space-between;align-items:flex-end;margin:30px 0 26px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.acard{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:22px;display:flex;flex-direction:column;gap:14px;transition:border-color .15s ease,transform .15s ease}
.acard:hover{border-color:rgba(124,111,207,.5);transform:translateY(-2px)}
.acard.sample{border-style:dashed;border-color:var(--line-2)}
.atop{display:flex;gap:16px;align-items:center}
.atop .t{font-family:var(--display);font-size:19px;line-height:1.15;letter-spacing:-.01em}
.ameta{display:flex;gap:8px;flex-wrap:wrap}
.say{font-size:14px;color:var(--muted)}.say b{color:var(--text);font-weight:600}
.ver{font-size:12.5px;color:var(--violet-text);border-top:1px solid var(--line);padding-top:12px;margin-top:auto}
.newcard{border:1.5px dashed var(--line-2);border-radius:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:var(--muted);min-height:190px;text-align:center;padding:20px}
.newcard .plus{width:46px;height:46px;border-radius:50%;border:1.5px solid var(--line-2);display:flex;align-items:center;justify-content:center;font-size:24px;color:var(--text)}
"""


def dashboard():
    items = [
        ("Coffee-delivery app", "Level 2", "Critical", M2, 2, "2 days ago", "↳ Version 2 of “Coffee-delivery idea”", False),
        ("Coffee-delivery idea", "Level 1", "Low", M1, 1, "5 days ago", "Has 1 newer version", False),
        ("Campus tutoring marketplace", "Level 1", "Medium", M1, 1, "1 week ago", "", False),
        ("Solar installation co-op", "Level 2", "Medium", M2, 2, "2 weeks ago", "", False),
        ("Pet-sitting platform", "Level 1", "High", M1, 1, "3 weeks ago", "", False),
        ("Sample: B2B analytics startup", "Level 2", "High", M2, 2, "Preloaded example", "Explore it before you run your own", True),
    ]
    cards = ""
    for t, lvl, band, rates, _, when, ver, sample in items:
        chips = f'<span class="chip violet">{lvl}</span><span class="chip">{when}</span>' + ('<span class="chip">Sample</span>' if sample else "")
        cards += (f'<a class="acard {"sample" if sample else ""}" href="#"><div class="atop">{ring(band, 74, 8, glyph_only=True)}<div><div class="t">{t}</div></div></div>'
                  f'<div class="ameta">{band_badge(band)}{chips}</div>'
                  f'<div class="say">About <b>{in_n(rates[band])}</b> similar startups closed</div>'
                  f'{f"<div class=ver>{ver}</div>" if ver else ""}</a>')
    cards += '<a class="newcard" href="#"><div class="plus">+</div><div><b style="color:var(--text)">New analysis</b><br>Takes about a minute.</div></a>'
    body = (app_topbar("Analyses") + '<main class="container" style="padding-bottom:80px"><div class="head"><div><h1 class="display h2">Your analyses</h1>'
            '<p class="muted" style="margin-top:8px">6 analyses, one of them a sample. Open one to explore its tree.</p></div>'
            '<button class="btn btn-primary">New analysis</button></div>'
            f'<div class="cards">{cards}</div></main>')
    return page("Fragilee · Analyses", body, DASH_CSS)


# ------------------------------------------------------------------ landing
LAND_CSS = r"""
.hero{display:flex;gap:56px;align-items:center;padding:48px 0 96px}
.hero .l{flex:1.1}.hero .r{flex:.9}
.hero .h1{margin:16px 0 22px}.hero p.lead{font-size:18px;color:var(--muted);max-width:520px}
.ctas{display:flex;gap:12px;margin-top:30px;align-items:center}.micro{font-size:13px;color:var(--faint);margin-top:16px}
.demo{background:var(--surface);border:1px solid var(--line-2);border-radius:26px;padding:26px;box-shadow:0 30px 70px rgba(0,0,0,.35)}
.demo .row{display:flex;gap:20px;align-items:center}
.demo .say{font-family:var(--display);font-size:23px;line-height:1.12;letter-spacing:-.02em}
.cream{background:var(--cream);color:var(--ink);padding:96px 0}
.cream .eyebrow{color:#6b6760}.cream .h2{margin:12px 0 44px;max-width:640px}
.steps{display:flex;gap:20px}.step{flex:1;background:#fff;border:1px solid rgba(30,27,22,.1);border-radius:20px;padding:28px}
.step .n{width:38px;height:38px;border-radius:50%;background:var(--violet);color:#fff;display:flex;align-items:center;justify-content:center;font-family:var(--display);margin-bottom:18px}
.step h3{font-family:var(--display);font-size:22px;letter-spacing:-.01em;margin-bottom:8px}.step p{color:#5a564f;font-size:15px}
.step .tag{display:inline-block;margin-top:16px;font-size:12px;padding:4px 10px;border-radius:99px;background:#efecff;color:#5a4fb5;font-weight:600}
.honest{padding:96px 0}.honest .h2{margin:12px 0 40px;max-width:700px}
.two{display:flex;gap:20px}.two .card{flex:1;padding:30px}.two h4{font-family:var(--display);font-size:20px;margin-bottom:14px}
.two li{list-style:none;padding:9px 0 9px 28px;position:relative;color:var(--muted);border-bottom:1px solid var(--line)}.two li:last-child{border-bottom:0}
.two .yes li::before{content:"✓";position:absolute;left:0;color:var(--sage);font-weight:700}.two .no li::before{content:"✕";position:absolute;left:0;color:var(--critical-text);font-weight:700}
.stats{display:flex;gap:20px;margin-top:20px}.stat{flex:1;border:1px solid var(--line);border-radius:18px;padding:24px}
.stat b{display:block;font-family:var(--display);font-size:40px;letter-spacing:-.02em}.stat span{color:var(--muted);font-size:14px}
.note{color:var(--faint);font-size:13.5px;margin-top:18px;max-width:760px}
.endcta{text-align:center;padding:30px 0 90px}.endcta .h2{margin-bottom:24px}
footer.f{border-top:1px solid var(--line);padding:26px 0;color:var(--faint);font-size:13px;display:flex;justify-content:space-between}
"""


def mini_tree():
    cols = [("Funding", "#E0784F", 20), ("Traction", "#6FBFA0", 14), ("Market", "#D9A441", 11), ("Location", "#6FBFA0", 9)]
    out = ['<svg viewBox="0 0 420 200" width="100%" role="img" aria-label="Example risk tree">']
    xs = [60, 160, 260, 360]
    for (g, col, r), x in zip(cols, xs):
        out.append(f'<path d="M210 54 C210 100 {x} 90 {x} 130" fill="none" stroke="{col}" stroke-width="{2 + r / 5:.1f}" opacity=".55" stroke-linecap="round"/>')
    out.append('<circle cx="210" cy="40" r="30" fill="#1B1D27" stroke="#E0784F" stroke-width="4"/>')
    for (g, col, r), x in zip(cols, xs):
        out.append(f'<circle cx="{x}" cy="140" r="{r + 8}" fill="{col}" fill-opacity=".22" stroke="{col}" stroke-width="2.5"/>'
                   f'<text x="{x}" y="{140 + r + 28}" text-anchor="middle" font-size="12" font-weight="600" fill="#DCE1E8">{g}</text>')
    out.append("</svg>")
    return "".join(out)


def landing():
    r = SAMPLES["stage2"]
    body = (f'<div class="container"><header class="topbar">{WORDMARK}<nav class="nav"><a href="#">How it works</a><a href="#">The honest bit</a></nav>'
            '<a class="btn btn-ghost" href="#">Sign in</a></header>'
            '<section class="hero"><div class="l"><div class="eyebrow">Early-stage risk, minus the guesswork</div>'
            '<h1 class="display h1">Know where your startup is most likely to crack.</h1>'
            '<p class="lead">Answer a few questions. Fragilee compares your startup with thousands of real ones that either closed or were acquired, then shows which factors point toward trouble.</p>'
            '<div class="ctas"><a class="btn btn-primary" href="#">Start an analysis</a><a class="btn btn-ghost" href="#">See an example</a></div>'
            '<div class="micro">Free during beta. No pitch deck required.</div></div>'
            f'<div class="r"><div class="demo"><div class="row">{ring(r["band"], 118, 10)}<div><div class="eyebrow" style="margin-bottom:8px">An example read</div>'
            f'<div class="say">About {in_n(r["similar_startups_failure_rate"])} startups like this one closed</div></div></div>'
            f'<div style="margin-top:14px">{mini_tree()}</div></div></div></section></div>'
            '<section class="cream"><div class="container"><div class="eyebrow">How it works</div><h2 class="display h2">Two levels. No homework.</h2><div class="steps">'
            '<div class="step"><div class="n">1</div><h3>Tell us the idea</h3><p>Country, state and a few industry tags. Thirty seconds, and you get a first read straight away.</p><span class="tag">Level 1</span></div>'
            '<div class="step"><div class="n">2</div><h3>Level up, if you can</h3><p>Add funding and traction details and the read gets a lot sharper. Skip it if the startup is still just an idea.</p><span class="tag">Level 2 · optional</span></div>'
            '<div class="step"><div class="n">3</div><h3>Explore the tree</h3><p>Click any branch to see what is pushing the risk up or down, ranked, with your own numbers next to it.</p><span class="tag">Your result</span></div>'
            '</div></div></section>'
            '<section class="honest"><div class="container"><div class="eyebrow">The honest bit</div><h2 class="display h2">A pattern-finder, not a fortune teller.</h2>'
            '<div class="two"><div class="card yes"><h4>What it is</h4><ul><li>Real outcomes of startups that closed or were acquired.</li><li>A way to see which factors point toward trouble.</li><li>A prompt to ask better questions before you decide.</li></ul></div>'
            '<div class="card no"><h4>What it is not</h4><ul><li>A prediction of your future.</li><li>Financial or legal advice.</li><li>Proof that you will fail, or succeed.</li></ul></div></div>'
            '<div class="stats"><div class="stat"><b class="num">10,941</b><span>startups behind the idea-stage read</span></div>'
            '<div class="stat"><b class="num">922</b><span>US startups behind the funding-stage read</span></div>'
            '<div class="stat"><b class="num">2013</b><span>era of the data snapshot</span></div></div>'
            '<p class="note">Startups that are still operating are not in the data, so Fragilee separates closed from acquired, not failed from surviving. Idea-stage reads are deliberately modest.</p></div></section>'
            '<section class="container endcta"><h2 class="display h2">Ready to find the cracks?</h2><a class="btn btn-primary" href="#">Start an analysis</a></section>'
            '<div class="container"><footer class="f"><span>Fragilee · a final-year project</span><span>Patterns, not predictions. Not financial advice.</span></footer></div>')
    return page("Fragilee · Know where your startup is most likely to crack", body, LAND_CSS)


# ------------------------------------------------------------------ sign in
SIGN_CSS = r"""
.split{display:flex;min-height:760px}.art{flex:1.1;padding:36px 56px;display:flex;flex-direction:column;justify-content:space-between;background:linear-gradient(160deg,#181a24,#14151C)}
.slot{border:1.5px dashed var(--line-2);border-radius:20px;height:330px;display:flex;align-items:center;justify-content:center;color:var(--faint);font-size:13px}
.art .say{font-family:var(--display);font-size:40px;line-height:1.06;letter-spacing:-.02em;max-width:460px}.art p{color:var(--muted);margin-top:14px;max-width:400px}
.form{flex:1;background:var(--surface);display:flex;align-items:center;justify-content:center;padding:48px}
.fc{width:100%;max-width:380px}
.tabs{display:flex;background:rgba(220,225,232,.06);border-radius:99px;padding:4px;margin-bottom:34px}
.tabs span{flex:1;text-align:center;padding:10px 0;border-radius:99px;font-size:14px;font-weight:600;color:var(--muted)}.tabs .on{background:var(--sage);color:var(--sage-ink)}
.fld{margin-bottom:18px}.fld label{display:block;font-size:13px;color:var(--muted);margin-bottom:8px}
.fld .input{font-size:15px;padding:13px 15px}.err{font-size:12.5px;color:var(--critical-text);margin-top:7px}
.fc .btn{width:100%;justify-content:center;margin-top:8px}.fine{text-align:center;font-size:13px;color:var(--muted);margin-top:20px}.fine a{color:var(--violet-text)}
"""


def signin():
    body = (f'<div class="split"><div class="art">{WORDMARK}<div class="slot">Your visual goes here</div>'
            '<div><div class="say">Welcome back. Your cracks are right where you left them.</div><p>Sign in to pick up your analyses and versions.</p></div></div>'
            '<div class="form"><div class="fc"><div class="tabs"><span class="on">Sign in</span><span>Sign up</span></div>'
            '<h1 class="display h3" style="margin-bottom:6px">Good to see you</h1><p class="muted" style="margin-bottom:28px">Log in to see your saved analyses.</p>'
            '<div class="fld"><label>Email</label><input class="input" placeholder="you@example.com"></div>'
            '<div class="fld"><label>Password</label><input class="input" type="password" placeholder="••••••••" style="border-color:var(--critical)"><div class="err">⚠ That email and password do not match.</div></div>'
            '<button class="btn btn-primary">Sign in</button><div class="fine">New here? <a href="#">Create an account</a> · <a href="#">Forgot password</a></div></div></div></div>')
    return page("Fragilee · Sign in", body, SIGN_CSS)


# ------------------------------------------------------------------ settings
SET_CSS = r"""
.sec{margin-top:26px}.sec .eyebrow{margin-bottom:12px}.sec .card{padding:6px 24px}
.line{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:16px 0;border-bottom:1px solid var(--line)}.line:last-child{border-bottom:0}
.line .l b{display:block;font-weight:600}.line .l span{font-size:13px;color:var(--muted)}
"""


def settings():
    body = (app_topbar("") + '<main class="container" style="max-width:760px;padding-bottom:90px"><h1 class="display h2" style="margin-top:26px">Settings</h1>'
            '<div class="sec"><div class="eyebrow">Account</div><div class="card"><div class="line"><div class="l"><b>Email</b><span>jordan.s@example.com</span></div><button class="btn btn-ghost">Change</button></div>'
            '<div class="line"><div class="l"><b>Plan</b><span>Beta · unlimited analyses</span></div><span class="chip violet">Free</span></div>'
            '<div class="line"><div class="l"><b>Sign out</b><span>On this device</span></div><button class="btn btn-ghost">Sign out</button></div></div></div>'
            '<div class="sec"><div class="eyebrow">About the numbers</div><div class="card"><div class="line"><div class="l"><b>How to read your results</b><span>What the bands mean, and what the data can and cannot say.</span></div><button class="btn btn-ghost">Open</button></div></div></div>'
            '<div class="sec"><div class="eyebrow">Your data</div><div class="card"><div class="line"><div class="l"><b>Delete all my analyses</b><span>Removes every saved analysis and version. This cannot be undone.</span></div><button class="btn btn-danger">Delete</button></div>'
            '<div class="line"><div class="l"><b>Delete my account</b><span>Removes your account and everything in it.</span></div><button class="btn btn-danger">Delete</button></div></div></div></main>')
    return page("Fragilee · Settings", body, SET_CSS)


if __name__ == "__main__":
    out = os.path.join(HERE, "out")
    for name, fn in (("v2-dashboard", dashboard), ("v2-landing", landing), ("v2-signin", signin), ("v2-settings", settings)):
        open(f"{out}/{name}.html", "w").write(fn())
    print("ok")
