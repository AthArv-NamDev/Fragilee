from common import *

META = SAMPLES["meta"]["stages"]
S1, S2 = SAMPLES["stage1"], SAMPLES["stage2_high"]
TAGS = [t for t in META["stage1"]["inputs"]["tags"]][:18]
STATES = [s for s in META["stage1"]["inputs"]["states"] if s not in ("OTHER", "NONE")][:12]

EXTRA = r"""
.flow{max-width:760px;margin:0 auto;padding:0 24px 80px}
.flow-top{display:flex;justify-content:space-between;align-items:center;padding:20px 0 26px}
.meta-row{display:flex;justify-content:space-between;align-items:center;margin:0 0 12px}
.q{margin-top:46px}
.q .display{font-size:42px}
.q .help{color:var(--muted);font-size:16px;margin:12px 0 30px;max-width:560px}
.opts{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.chips{display:flex;flex-wrap:wrap;gap:10px}
.foot{display:flex;justify-content:space-between;align-items:center;margin-top:34px}
.count{font-size:13px;color:var(--muted)}
.stack{display:flex;flex-direction:column;gap:12px}
.pad{margin-top:8px}
.bigrow{display:flex;justify-content:center;padding:18px 0}
.range{margin:14px 0 26px}.range label{display:flex;justify-content:space-between;font-size:15px;margin-bottom:10px}.range label b{font-family:var(--display);font-size:20px;letter-spacing:-.01em}
.range input{width:100%;accent-color:#7C6FCF}
.reveal{text-align:center;margin-top:40px}
.reveal .say{font-family:var(--display);font-size:38px;letter-spacing:-.02em;line-height:1.08;margin:22px 0 8px}
.reveal .sub{color:var(--muted);max-width:520px;margin:0 auto 24px}
.reveal .chips{justify-content:center;margin-bottom:28px}
.reveal .btns{display:flex;gap:12px;justify-content:center;flex-wrap:wrap}
.quiet{font-size:13px;color:var(--faint);margin-top:22px}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.q,.reveal{animation:rise .35s ease both}
@media (prefers-reduced-motion:reduce){.q,.reveal{animation:none}}
@media screen and (max-width:640px){.opts{grid-template-columns:1fr}.q .display{font-size:30px}}
"""

SCRIPT = r"""
const COUNTRIES=[["USA","United States","Where most of our data lives."],["GBR","United Kingdom","Tea, fintech and fog."],["CAN","Canada","Polite, and well funded."],["IND","India","A lot of founders, a lot of ambition."],["ISR","Israel","Small country, huge startup scene."],["OTHER","Somewhere else","We will group you with the rest."]];
const STATES=__STATES__;
const TAGS=__TAGS__;
const MONEY=[["Under $50k","Bootstrapped or just getting going",20000],["$50k to $250k","A pre-seed round, give or take",120000],["$250k to $1M","Seed money",600000],["$1M to $5M","Serious runway",2500000],["$5M or more","Proper venture territory",8000000]];
const REVEAL={1:{ring:__RING1__,say:"About __N1__ startups like yours closed",sub:"That is the observed rate for startups in the __B1__ band. It is an idea-stage read, so treat it as a first impression.",chips:["Level 1 · Your idea","Confidence: Limited"]},
              2:{ring:__RING2__,say:"About __N2__ startups like yours closed",sub:"That is the observed rate for startups in the __B2__ band. Funding and traction make this read much sharper.",chips:["Level 2 · Funding details","Confidence: Moderate","US benchmark"]}};
const S={country:null,state:null,tags:[],title:"",funding:null,rounds:1,vc:false,angel:false,series:[],investors:1,people:3,t1:1,t2:2};
const STEPS=[
 {id:"country",lvl:1,title:"Where does the startup live?",help:"Geography matters more than most founders like to admit."},
 {id:"state",lvl:1,title:"Which state?",help:"State only matters in the US, which is why you are seeing this.",when:()=>S.country==="USA"},
 {id:"tags",lvl:1,title:"What is it about?",help:"Pick up to five. Choose the ones you would put on the pitch deck."},
 {id:"title",lvl:1,title:"Name this analysis.",help:"Only you can see it. Untitled is allowed, but we will judge it quietly."},
 {id:"reveal1",reveal:1},
 {id:"funding",lvl:2,title:"How much has the startup raised?",help:"Total across every round. Ballpark is fine, we are not your accountant."},
 {id:"rounds",lvl:2,title:"How many funding rounds so far?",help:"A round is a funding event, not a coffee with an investor."},
 {id:"backers",lvl:2,title:"Who has backed you?",help:"Tick what applies. Series means the named rounds, A to D."},
 {id:"investors",lvl:2,title:"How many investors join a typical round?",help:"On average. One lone angel counts as one."},
 {id:"people",lvl:2,title:"How many people are linked to the company?",help:"Founders, team, advisors, board members with a public profile."},
 {id:"timing",lvl:2,title:"How fast did the money arrive?",help:"Years since founding. Speed says more than you would think."},
 {id:"reveal2",reveal:2}];
let i=0;
const $=s=>document.querySelector(s);
const visible=()=>STEPS.filter(s=>!s.when||s.when());
function go(d){const v=visible();let k=v.findIndex(s=>s.id===STEPS[i].id);k=Math.max(0,Math.min(v.length-1,k+d));i=STEPS.findIndex(s=>s.id===v[k].id);draw();window.scrollTo(0,0)}
function pick(k,v,adv){S[k]=v;if(adv)setTimeout(()=>go(1),220);else draw()}
function toggleTag(t){const a=S.tags;const k=a.indexOf(t);if(k>=0)a.splice(k,1);else if(a.length<5)a.push(t);draw()}
function toggleSeries(t){const a=S.series;const k=a.indexOf(t);if(k>=0)a.splice(k,1);else a.push(t);draw()}
function step(k,d,min,max){S[k]=Math.max(min,Math.min(max,S[k]+d));draw()}
function progress(s){const v=visible().filter(x=>x.lvl===s.lvl);const n=v.findIndex(x=>x.id===s.id);return `<div class="progress">${v.map((x,j)=>`<i class="${j<n?"done":j===n?"now":""}"></i>`).join("")}</div>`}
function reveal(n){const r=REVEAL[n];return `<div class="reveal"><div class="eyebrow">Level ${n} cleared</div><div style="display:flex;justify-content:center;margin-top:18px">${r.ring}</div>
 <div class="say">${r.say}</div><div class="sub">${r.sub}</div><div class="chips">${r.chips.map((c,j)=>`<span class="chip ${j===0?"violet":""}">${c}</span>`).join("")}</div>
 <div class="btns">${n===1?`<button class="btn btn-primary" onclick="go(1)">Level up: sharpen this read</button><button class="btn btn-ghost">Open full result</button>`:`<button class="btn btn-primary">Open full result</button><button class="btn btn-ghost" onclick="i=0;draw()">Start another</button>`}</div>
 ${n===1?'<div class="quiet">Level 2 takes about a minute and needs funding details. Skip it if the startup is still just an idea.</div>':""}</div>`}
function body(s){
 if(s.id==="country")return `<div class="opts">${COUNTRIES.map(c=>`<button class="opt ${S.country===c[0]?"sel":""}" onclick="pick('country','${c[0]}',true)"><div class="t">${c[1]}</div><div class="s">${c[2]}</div></button>`).join("")}</div>`;
 if(s.id==="state")return `<div class="chips">${STATES.map(x=>`<button class="tagchip ${S.state===x?"sel":""}" onclick="pick('state','${x}',true)">${x}</button>`).join("")}<button class="tagchip ${S.state==="OTHER"?"sel":""}" onclick="pick('state','OTHER',true)">Another state</button></div>`;
 if(s.id==="tags")return `<div class="chips">${TAGS.map(t=>`<button class="tagchip ${S.tags.includes(t)?"sel":""}" onclick="toggleTag('${t.replace(/'/g,"\\'")}')">${t}</button>`).join("")}</div>
  <div class="foot"><span class="count">${S.tags.length} of 5 picked</span><button class="btn btn-primary" ${S.tags.length?"":"disabled"} onclick="go(1)">Continue</button></div>`;
 if(s.id==="title")return `<input class="input" id="t" maxlength="80" placeholder="e.g. Coffee-delivery app" value="${S.title}" oninput="S.title=this.value;$('#go').disabled=!this.value.trim()"><div class="foot"><span class="count">Up to 80 characters</span><button id="go" class="btn btn-primary" ${S.title.trim()?"":"disabled"} onclick="go(1)">Reveal my read</button></div>`;
 if(s.id==="funding")return `<div class="stack">${MONEY.map(m=>`<button class="opt ${S.funding===m[2]?"sel":""}" onclick="pick('funding',${m[2]},true)"><div class="t">${m[0]}</div><div class="s">${m[1]}</div></button>`).join("")}</div>${S.country&&S.country!=="USA"?'<div class="quiet">Level 2 is benchmarked on US startups, so your result will carry a small “US benchmark” label.</div>':""}`;
 if(s.id==="rounds")return `<div class="bigrow"><div class="stepper"><button onclick="step('rounds',-1,1,10)">−</button><span class="v num">${S.rounds}</span><button onclick="step('rounds',1,1,10)">+</button></div></div><div class="foot"><span></span><button class="btn btn-primary" onclick="go(1)">Continue</button></div>`;
 if(s.id==="backers")return `<div class="stack"><button class="switch ${S.vc?"sel":""}" onclick="S.vc=!S.vc;draw()"><span>Venture capital</span><span class="k"></span></button><button class="switch ${S.angel?"sel":""}" onclick="S.angel=!S.angel;draw()"><span>Angel investors</span><span class="k"></span></button></div>
  <div class="eyebrow pad" style="margin-top:26px">Series reached</div><div class="chips" style="margin-top:12px">${["A","B","C","D"].map(x=>`<button class="tagchip ${S.series.includes(x)?"sel":""}" onclick="toggleSeries('${x}')">Series ${x}</button>`).join("")}</div><div class="foot"><span></span><button class="btn btn-primary" onclick="go(1)">Continue</button></div>`;
 if(s.id==="investors")return `<div class="bigrow"><div class="stepper"><button onclick="step('investors',-1,1,10)">−</button><span class="v num">${S.investors}</span><button onclick="step('investors',1,1,10)">+</button></div></div><div class="foot"><span></span><button class="btn btn-primary" onclick="go(1)">Continue</button></div>`;
 if(s.id==="people")return `<div class="bigrow"><div class="stepper"><button onclick="step('people',-1,0,60)">−</button><span class="v num">${S.people}</span><button onclick="step('people',1,0,60)">+</button></div></div><div class="foot"><span></span><button class="btn btn-primary" onclick="go(1)">Continue</button></div>`;
 if(s.id==="timing")return `<div class="range"><label><span>Founding to first funding</span><b class="num">${S.t1} yr</b></label><input type="range" min="0" max="10" step="0.5" value="${S.t1}" oninput="S.t1=+this.value;this.previousElementSibling.lastElementChild.textContent=this.value+' yr'"></div>
  <div class="range"><label><span>Founding to latest funding</span><b class="num">${S.t2} yr</b></label><input type="range" min="0" max="10" step="0.5" value="${S.t2}" oninput="S.t2=+this.value;this.previousElementSibling.lastElementChild.textContent=this.value+' yr'"></div><div class="foot"><span></span><button class="btn btn-primary" onclick="go(1)">Reveal the sharper read</button></div>`;
 return ""}
function draw(){const s=STEPS[i];const root=$("#flow");
 if(s.reveal){root.innerHTML=reveal(s.reveal);return}
 const v=visible().filter(x=>x.lvl===s.lvl);const n=v.findIndex(x=>x.id===s.id);
 root.innerHTML=`<div class="meta-row"><span class="chip violet">Level ${s.lvl} · ${s.lvl===1?"Your idea":"Sharpen your read"}</span><span class="count">Step ${n+1} of ${v.length}</span></div>${progress(s)}
 <div class="q"><div class="display">${s.title}</div><div class="help">${s.help}</div>${body(s)}</div>
 <div style="margin-top:22px">${(i>0&&STEPS[i-1]&&!STEPS[i-1].reveal)||s.id==="funding"?'<button class="btn btn-quiet" onclick="go(-1)">← Back</button>':""}</div>`;
 const t=$("#t");if(t)t.focus()}
draw();
"""


def build():
    script = (SCRIPT.replace("__STATES__", json.dumps(STATES)).replace("__TAGS__", json.dumps(TAGS))
              .replace("__RING1__", json.dumps(ring(S1["band"], 150, 11))).replace("__RING2__", json.dumps(ring(S2["band"], 150, 11)))
              .replace("__N1__", in_n(S1["similar_startups_failure_rate"])).replace("__N2__", in_n(S2["similar_startups_failure_rate"]))
              .replace("__B1__", S1["band"]).replace("__B2__", S2["band"]))
    body = (f'<div class="container"><header class="topbar">{WORDMARK}<a class="btn btn-quiet" href="#">Exit</a></header></div>'
            '<main class="flow"><div id="flow"></div></main>')
    return page("Fragilee · New analysis", body, EXTRA, script=script)


if __name__ == "__main__":
    open(os.path.join(HERE, "out", "v2-new-analysis.html"), "w").write(build())
    print("ok")
