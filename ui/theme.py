"""Gen-Z motion layer for TravelMate / TripLedger AI.

Pure CSS (no JavaScript, no extra downloads) so it works inside Streamlit's sanitised markdown.
It is layered *on top of* the original design tokens (--ink, --green, --mint, --paper, --gold),
so the existing look is preserved and only enriched.

Techniques used (all progressive enhancement, graceful fallback everywhere):
  * aurora mesh-gradient background + film grain
  * scroll-driven reveals (animation-timeline) with load-time fallback
  * glass sidebar, pill radio nav, shine-sweep buttons with press feedback
  * marquee ticker, count-up stats, bento "how it works" grid
  * full prefers-reduced-motion support
"""
from __future__ import annotations
import html
import streamlit as st

THEME_CSS = """
<style>
@property --tm-n   { syntax:'\\3c integer\\3e '; initial-value:0; inherits:false; }

:root{
  --tm-aqua:#14b8a6; --tm-lime:#a3e635; --tm-violet:#8b5cf6; --tm-peach:#fb923c; --tm-pink:#f472b6;
  --tm-glass:rgba(255,255,255,.62); --tm-line:rgba(31,87,72,.14);
  --tm-ease:cubic-bezier(.22,1,.36,1);
}

/* ── aurora + grain ───────────────────────────────────────────── */
.stApp::before{
  content:""; position:fixed; inset:-20vmax; z-index:0; pointer-events:none; opacity:.55; filter:blur(60px);
  background:
    radial-gradient(38vmax 38vmax at 12% 18%, rgba(20,184,166,.28), transparent 60%),
    radial-gradient(34vmax 34vmax at 88% 12%, rgba(139,92,246,.18), transparent 60%),
    radial-gradient(40vmax 40vmax at 78% 88%, rgba(251,146,60,.18), transparent 60%),
    radial-gradient(30vmax 30vmax at 18% 86%, rgba(163,230,53,.18), transparent 60%);
  animation:tmAurora 26s ease-in-out infinite alternate;
}
.stApp::after{
  content:""; position:fixed; inset:0; z-index:0; pointer-events:none; opacity:.05; mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%2523n)'/%3E%3C/svg%3E");
}
.block-container, section[data-testid="stSidebar"]{ position:relative; z-index:1; }
@keyframes tmAurora{
  0%{ transform:translate3d(0,0,0) rotate(0deg) scale(1) }
  50%{ transform:translate3d(3vmax,-2vmax,0) rotate(8deg) scale(1.08) }
  100%{ transform:translate3d(-3vmax,2vmax,0) rotate(-6deg) scale(1.02) }
}

/* ── entrance + scroll reveals (fill-mode "backwards" keeps hover transforms working) ── */
.feature,.destination-card,.category-tab,.info-card,.flight-card,.hotel-card,.weather-card,
.itinerary-day,.tm-bento > div,.tm-stat,.trip-header,.tm-search-panel{
  animation:tmRise .7s var(--tm-ease) backwards;
}
@supports (animation-timeline: view()){
  .feature,.destination-card,.category-tab,.info-card,.flight-card,.hotel-card,.weather-card,
  .itinerary-day,.tm-bento > div,.tm-stat{
    animation:tmRise linear backwards; animation-timeline:view(); animation-range:entry 0% entry 45%;
  }
}
@keyframes tmRise{ from{ opacity:0; transform:translateY(26px) scale(.97); filter:blur(4px) } to{ opacity:1; transform:none; filter:none } }

/* ── hero polish ──────────────────────────────────────────────── */
.hero h1 em{
  background:linear-gradient(90deg,#fde68a,#a7f3d0,#c4b5fd,#fde68a); background-size:300% 100%;
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; color:transparent;
  animation:tmShimmer 6s linear infinite;
}
.hero::after{
  content:""; position:absolute; inset:0; pointer-events:none;
  background:linear-gradient(115deg,transparent 35%,rgba(255,255,255,.14) 50%,transparent 65%);
  background-size:250% 100%; animation:tmSweep 7s ease-in-out infinite;
}
.hero{ transition:transform .6s var(--tm-ease), box-shadow .6s var(--tm-ease); }
.hero:hover{ transform:translateY(-3px); box-shadow:0 30px 70px rgba(26,53,43,.20); }
@keyframes tmShimmer{ to{ background-position:300% 0 } }
@keyframes tmSweep{ 0%{ background-position:150% 0 } 60%,100%{ background-position:-100% 0 } }

/* ── cards: lift + animated conic border ──────────────────────── */
.destination-card,.category-tab,.feature,.info-card,.hotel-card,.flight-card{
  transition:transform .45s var(--tm-ease), box-shadow .45s var(--tm-ease);
}
.destination-card:hover,.category-tab:hover,.feature:hover,.info-card:hover{
  transform:translateY(-8px) rotate(-.4deg); box-shadow:0 26px 50px rgba(20,60,50,.18);
}
.destination-card{ background-size:112%; background-position:center; transition:transform .45s var(--tm-ease), box-shadow .45s var(--tm-ease), background-size 1.2s var(--tm-ease); }
.destination-card:hover{ background-size:124% }

/* ── buttons: gradient, shine sweep, press feedback ───────────── */
div.stButton > button, [data-testid="stDownloadButton"] button, [data-testid="stFormSubmitButton"] button,
[data-testid^="stBaseLinkButton"], .stLinkButton a{
  position:relative; overflow:hidden; border-radius:999px !important;
  transition:transform .25s var(--tm-ease), box-shadow .25s var(--tm-ease), filter .25s !important;
}
div.stButton > button::after, [data-testid="stFormSubmitButton"] button::after, [data-testid="stDownloadButton"] button::after{
  content:""; position:absolute; top:0; left:-120%; width:80%; height:100%; transform:skewX(-20deg);
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.45),transparent); transition:left .7s var(--tm-ease); pointer-events:none;
}
div.stButton > button:hover::after, [data-testid="stFormSubmitButton"] button:hover::after, [data-testid="stDownloadButton"] button:hover::after{ left:140% }
div.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover, [data-testid="stDownloadButton"] button:hover{
  transform:translateY(-2px); box-shadow:0 12px 26px rgba(31,87,72,.22);
}
div.stButton > button:active, [data-testid="stFormSubmitButton"] button:active{ transform:translateY(0) scale(.96); }
button:focus-visible, a:focus-visible, input:focus-visible{ outline:3px solid rgba(20,184,166,.55) !important; outline-offset:2px; }

/* ── inputs ───────────────────────────────────────────────────── */
.stTextInput input, .stNumberInput input, .stDateInput input, div[data-baseweb="select"] > div{
  transition:box-shadow .3s var(--tm-ease), border-color .3s, transform .3s var(--tm-ease) !important;
}
.stTextInput input:focus, .stNumberInput input:focus{ transform:translateY(-1px); box-shadow:0 0 0 4px rgba(20,184,166,.16) !important; }

/* ── glass sidebar + pill navigation ──────────────────────────── */
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,rgba(255,255,255,.72),rgba(233,242,233,.72)) !important;
  backdrop-filter:blur(18px) saturate(1.4); -webkit-backdrop-filter:blur(18px) saturate(1.4);
  border-right:1px solid var(--tm-line);
}
section[data-testid="stSidebar"] h2{
  background:linear-gradient(90deg,var(--green),var(--tm-aqua),var(--tm-violet)); background-size:200% 100%;
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; animation:tmShimmer 8s linear infinite;
}
section[data-testid="stSidebar"] [role="radiogroup"] > label{
  padding:9px 14px; border-radius:14px; margin-bottom:4px; border:1px solid transparent;
  transition:background .3s var(--tm-ease), transform .3s var(--tm-ease), border-color .3s;
}
section[data-testid="stSidebar"] [role="radiogroup"] > label:hover{ background:rgba(20,184,166,.10); transform:translateX(4px); }
section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked){
  background:linear-gradient(90deg,rgba(20,184,166,.18),rgba(139,92,246,.12)); border-color:rgba(20,184,166,.35); font-weight:700;
}

/* ── status / feedback ────────────────────────────────────────── */
div[data-testid="stAlert"]{ border-radius:16px; animation:tmRise .5s var(--tm-ease) backwards; backdrop-filter:blur(6px); }
div[data-testid="stSpinner"]{ animation:tmPulse 1.6s ease-in-out infinite; }
@keyframes tmPulse{ 50%{ opacity:.55 } }
[data-testid="stDataFrame"]{ border-radius:16px; overflow:hidden; box-shadow:0 8px 24px rgba(20,60,50,.08); }
[data-testid="stTabs"] button[aria-selected="true"]{ color:var(--green); }

/* ── marquee ticker ───────────────────────────────────────────── */
.tm-marquee{ overflow:hidden; margin:18px 0 6px; border-radius:999px; border:1px solid var(--tm-line);
  background:var(--tm-glass); backdrop-filter:blur(10px); padding:10px 0;
  mask-image:linear-gradient(90deg,transparent,#000 8%,#000 92%,transparent); -webkit-mask-image:linear-gradient(90deg,transparent,#000 8%,#000 92%,transparent); }
.tm-marquee-track{ display:flex; gap:12px; width:max-content; animation:tmMarquee 38s linear infinite; }
.tm-marquee:hover .tm-marquee-track{ animation-play-state:paused; }
.tm-chip{ display:inline-flex; align-items:center; gap:7px; padding:6px 15px; border-radius:999px; font-size:13px; font-weight:600;
  color:var(--green); background:#fff; border:1px solid var(--tm-line); white-space:nowrap; transition:transform .3s var(--tm-ease), background .3s; }
.tm-chip:hover{ transform:scale(1.08) rotate(-2deg); background:var(--mint); }
@keyframes tmMarquee{ to{ transform:translateX(-50%) } }

/* ── stats (count-up where supported) ─────────────────────────── */
.tm-stats{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin:18px 0; }
.tm-stat{ padding:20px 18px; border-radius:20px; background:var(--tm-glass); border:1px solid var(--tm-line); backdrop-filter:blur(10px); text-align:center; }
.tm-stat b{ display:block; font-family:'Playfair Display',serif; font-size:clamp(28px,4vw,42px); line-height:1.1;
  background:linear-gradient(135deg,var(--green),var(--tm-aqua),var(--tm-violet)); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
.tm-stat > span{ color:var(--muted); font-size:12px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase; }
/* number is drawn by ::after so the real value is never duplicated; enhanced browsers animate a counter */
.tm-count::after{ content:attr(data-n); }
@supports (animation-timeline: view()) and (counter-set: a 1){
  .tm-count{ animation:tmCount 1.8s var(--tm-ease) both; counter-reset:tmn var(--tm-n); }
  .tm-count::after{ content:counter(tmn); }
}
@keyframes tmCount{ from{ --tm-n:0 } to{ --tm-n:var(--to) } }

/* ── bento "how it works" ─────────────────────────────────────── */
.tm-bento{ display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:14px; margin:14px 0 26px; }
.tm-bento > div{ position:relative; overflow:hidden; padding:22px; border-radius:22px; background:var(--tm-glass); border:1px solid var(--tm-line);
  backdrop-filter:blur(10px); transition:transform .45s var(--tm-ease), box-shadow .45s var(--tm-ease); }
.tm-bento > div:hover{ transform:translateY(-6px); box-shadow:0 22px 44px rgba(20,60,50,.15); }
.tm-bento > div:nth-child(1){ grid-column:span 3; background:linear-gradient(135deg,rgba(20,184,166,.16),rgba(255,255,255,.7)); }
.tm-bento > div:nth-child(2){ grid-column:span 3; background:linear-gradient(135deg,rgba(139,92,246,.14),rgba(255,255,255,.7)); }
.tm-bento > div:nth-child(3){ grid-column:span 2; }
.tm-bento > div:nth-child(4){ grid-column:span 2; }
.tm-bento > div:nth-child(5){ grid-column:span 2; background:linear-gradient(135deg,rgba(251,146,60,.16),rgba(255,255,255,.7)); }
.tm-bento .ic{ font-size:30px; display:inline-block; animation:tmBob 3.4s ease-in-out infinite; }
.tm-bento > div:nth-child(2) .ic{ animation-delay:.4s } .tm-bento > div:nth-child(3) .ic{ animation-delay:.8s }
.tm-bento > div:nth-child(4) .ic{ animation-delay:1.2s } .tm-bento > div:nth-child(5) .ic{ animation-delay:1.6s }
.tm-bento h4{ margin:10px 0 4px; font-size:17px; color:var(--ink); }
.tm-bento p{ margin:0; color:var(--muted); font-size:13px; line-height:1.55; }
@keyframes tmBob{ 0%,100%{ transform:translateY(0) rotate(-4deg) } 50%{ transform:translateY(-7px) rotate(5deg) } }

/* ── live sticker badge ───────────────────────────────────────── */
.tm-sticker{ display:inline-flex; align-items:center; gap:8px; padding:6px 14px; border-radius:999px; font-size:12px; font-weight:800; letter-spacing:.6px;
  color:#0b6b57; background:rgba(163,230,53,.28); border:1px solid rgba(101,163,13,.35); }
.tm-sticker i{ width:8px; height:8px; border-radius:50%; background:#16a34a; animation:tmPing 1.8s infinite; }
@keyframes tmPing{ 0%{ box-shadow:0 0 0 0 rgba(22,163,74,.55) } 80%,100%{ box-shadow:0 0 0 9px rgba(22,163,74,0) } }

/* ── responsive ───────────────────────────────────────────────── */
@media (max-width:820px){
  .tm-stats{ grid-template-columns:repeat(2,minmax(0,1fr)); }
  .tm-bento{ grid-template-columns:repeat(2,minmax(0,1fr)); }
  .tm-bento > div:nth-child(n){ grid-column:span 2; }
  .destination-card:hover,.category-tab:hover,.feature:hover,.info-card:hover{ transform:translateY(-3px); }
}

/* ── accessibility: honour reduced motion ─────────────────────── */
@media (prefers-reduced-motion:reduce){
  .stApp::before,.hero::after,.hero h1 em,.tm-marquee-track,.tm-bento .ic,.tm-sticker i,
  section[data-testid="stSidebar"] h2{ animation:none !important; }
  .feature,.destination-card,.category-tab,.info-card,.flight-card,.hotel-card,.weather-card,.itinerary-day,
  .tm-bento > div,.tm-stat,.trip-header,.tm-search-panel,.tm-count{ animation:none !important; opacity:1 !important; filter:none !important; transform:none !important; }
  .tm-count{ counter-reset:none !important } .tm-count::after{ content:attr(data-n) !important; }
}
</style>
"""


def inject() -> None:
    """Inject the motion layer once per script run (after the original CSS so it can enrich it)."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def marquee(names: list[str]) -> str:
    chips = "".join(f'<span class="tm-chip">📍 {html.escape(str(n))}</span>' for n in names)
    # Track is duplicated so the -50% translate loops seamlessly.
    return f'<div class="tm-marquee" aria-label="Featured destinations"><div class="tm-marquee-track">{chips}{chips}</div></div>'


def stats(items: list[tuple[int, str]]) -> str:
    cells = "".join(
        f'<div class="tm-stat"><b><span class="tm-count" style="--to:{int(v)}" data-n="{int(v)}"></span></b><span>{html.escape(label)}</span></div>'
        for v, label in items
    )
    return f'<div class="tm-stats">{cells}</div>'


def bento() -> str:
    cards = [
        ("🧭", "Search anything", "Curated guides or any place on Earth, with instant suggestions and a Google Maps hand-off."),
        ("🤖", "Four AI agents", "Flights, hotels, weather and itinerary agents are coordinated into one plan in seconds."),
        ("💸", "Budget aware", "Estimated costs vs. your budget, with a clear warning before you overspend."),
        ("🔐", "Secure ledger", "Sign in, save trips and verify PayPal Sandbox payments server-side."),
        ("📦", "Take it anywhere", "Export your itinerary as PDF, Word, JSON or plain text."),
    ]
    inner = "".join(f'<div><span class="ic">{i}</span><h4>{html.escape(t)}</h4><p>{html.escape(d)}</p></div>' for i, t, d in cards)
    return f'<div class="tm-bento">{inner}</div>'
