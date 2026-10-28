"""All custom CSS for the dashboard. Injected once with st.html."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=DM+Sans:opsz,wght@9..40,400..700&display=swap');

:root{
  --bg:#0A1020; --panel:#111A2E; --raised:#16213A; --line:#233152; --line-soft:#1B2745;
  --text:#E9EFFA; --muted:#8B9BB8; --faint:#5E6E8C;
  --sky:#4DA3FF; --best:#4ADE80;
  --display:'Bricolage Grotesque','DM Sans',system-ui,-apple-system,'Segoe UI',sans-serif;
  --body:'DM Sans',system-ui,-apple-system,'Segoe UI',sans-serif;
}

/* ───────── 1. Remove Streamlit chrome and the space it reserves ───────── */
header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"],
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
#MainMenu, footer { display:none !important; }

[data-testid="stAppViewContainer"] > .main,
section.main { padding-top:0 !important; }

[data-testid="stMainBlockContainer"], .block-container{
  padding:.85rem 1.5rem .5rem !important;
  max-width:100% !important;
}
[data-testid="stVerticalBlock"]{ gap:.65rem !important; }
[data-testid="stHorizontalBlock"]{ gap:.6rem !important; }
/* the container that holds this stylesheet must not reserve a gap */
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > style),
.element-container:has(> style){ display:none !important; }

/* ───────── 2. Base ───────── */
.stApp{
  background:
    radial-gradient(900px 420px at 6% -10%, rgba(77,163,255,.17), transparent 62%),
    radial-gradient(720px 380px at 98% -14%, rgba(255,200,61,.10), transparent 62%),
    var(--bg);
  color:var(--text);
}
.stApp, .stApp p, .stApp label, .stApp input, .stApp button, .stApp textarea,
.stApp [data-baseweb="select"], .stApp [data-baseweb="tab"]{
  font-family:var(--body);
}
.stApp *::selection{ background:rgba(77,163,255,.35); }
::-webkit-scrollbar{ width:10px; height:10px; }
::-webkit-scrollbar-thumb{ background:var(--line); border-radius:10px; }
::-webkit-scrollbar-track{ background:transparent; }

/* ───────── 3. Top bar ───────── */
.topbar{ display:flex; align-items:center; gap:.9rem; min-height:46px; }
.mark{ flex:none; filter:drop-shadow(0 6px 14px rgba(77,163,255,.35)); }
.brand{ font-family:var(--display); font-weight:700; font-size:1.45rem; letter-spacing:-.02em; line-height:1.05; }
.brand small{ display:block; font-family:var(--body); font-weight:400; font-size:.78rem;
  letter-spacing:0; color:var(--muted); margin-top:.2rem; }
.top-stats{ margin-left:auto; display:flex; gap:.5rem; flex-wrap:wrap; justify-content:flex-end; }
.chip{ display:inline-flex; align-items:center; gap:.4rem; padding:.28rem .7rem; border-radius:999px;
  background:var(--panel); border:1px solid var(--line); color:var(--muted); font-size:.8rem; white-space:nowrap; }
.chip b{ color:var(--text); font-weight:600; font-variant-numeric:tabular-nums; }

/* ───────── 4. The search bar ───────── */
[data-testid="stTextInputRootElement"]{
  border-radius:18px; background:var(--panel); border:1px solid var(--line);
  min-height:3.5rem; box-shadow:0 10px 34px rgba(0,0,0,.28);
  transition:border-color .15s, box-shadow .15s;
  background-image:url("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='22' height='22' viewBox='0 0 24 24' fill='none' stroke='%238B9BB8' stroke-width='2.2' stroke-linecap='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='M20 20l-3.6-3.6'/%3E%3C/svg%3E");
  background-repeat:no-repeat; background-position:1.1rem center;
}
[data-testid="stTextInputRootElement"]:focus-within{
  border-color:var(--sky);
  box-shadow:0 0 0 4px rgba(77,163,255,.20), 0 10px 34px rgba(0,0,0,.35);
}
[data-testid="stTextInput"] input{ background:transparent !important; }
[data-testid="stTextInput"] input{
  font-size:1.12rem; padding-left:3.2rem !important; color:var(--text);
}
[data-testid="stTextInput"] input::placeholder{ color:var(--faint); }

/* ───────── 5. Controls ───────── */
[data-baseweb="select"] > div, [data-testid="stNumberInput"] [data-baseweb="input"]{
  background:var(--panel); border-radius:12px; border-color:var(--line); min-height:2.6rem;
}
[data-testid="stButtonGroup"] button{ font-weight:500; font-size:.88rem; }
.stButton > button, .stDownloadButton > button, [data-testid="stPopover"] > div > button{
  border-radius:12px; border:1px solid var(--line); background:var(--panel);
  font-weight:600; min-height:2.6rem; transition:border-color .12s, transform .12s;
}
.stButton > button:hover, .stDownloadButton > button:hover{ border-color:var(--sky); color:var(--text); }
.stButton > button[kind="primary"]{
  background:linear-gradient(180deg,#5BB0FF,#3D8FEA); border-color:#3D8FEA; color:#06101F;
}
.stButton > button[kind="primary"]:hover{ filter:brightness(1.08); color:#06101F; }
.stButton > button:disabled{ opacity:.45; }

[data-testid="stDataFrame"]{
  border:1px solid var(--line); border-radius:16px; overflow:hidden;
  box-shadow:0 12px 40px rgba(0,0,0,.25);
}
[data-testid="stExpander"] details{ border:1px solid var(--line); border-radius:14px; background:var(--panel); }
[data-testid="stCaptionContainer"]{ color:var(--muted); }
[data-testid="stAlert"]{ border-radius:14px; }

/* ───────── 6. Source badge (colour = source, everywhere) ───────── */
.badge{ --c:#4DA3FF; display:inline-flex; align-items:center; gap:.4rem; padding:.14rem .6rem;
  border-radius:999px; font-size:.74rem; font-weight:600; white-space:nowrap;
  color:var(--c); background:color-mix(in srgb,var(--c) 13%,transparent);
  border:1px solid color-mix(in srgb,var(--c) 38%,transparent); }
.badge::before{ content:""; width:.45rem; height:.45rem; border-radius:50%; background:var(--c); }

/* ───────── 7. Stat strip above results ───────── */
.strip{ display:flex; flex-wrap:wrap; gap:.6rem; }
.stat{ flex:1 1 170px; padding:.7rem .95rem; border-radius:16px; background:var(--panel);
  border:1px solid var(--line-soft); min-width:0; }
.stat .k{ color:var(--muted); font-size:.78rem; }
.stat .v{ font-family:var(--display); font-weight:650; font-size:1.55rem; letter-spacing:-.02em;
  font-variant-numeric:tabular-nums; line-height:1.2; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.stat .s{ color:var(--muted); font-size:.76rem; margin-top:.15rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.stat.best{ border-color:color-mix(in srgb,var(--best) 45%,transparent);
  background:linear-gradient(180deg,color-mix(in srgb,var(--best) 9%,var(--panel)),var(--panel)); }
.stat.best .v{ color:var(--best); }

/* ───────── 8. Price ladder (compare) ───────── */
.ladder{ display:flex; flex-direction:column; gap:.5rem; }
.rung{ display:grid; grid-template-columns:2.1rem minmax(0,2.3fr) minmax(140px,1.5fr) minmax(110px,auto) 6.6rem;
  align-items:center; gap:.9rem; padding:.8rem 1rem; border-radius:16px;
  background:var(--panel); border:1px solid var(--line-soft); }
.rung.low{ border-color:color-mix(in srgb,var(--best) 50%,transparent);
  background:linear-gradient(90deg,color-mix(in srgb,var(--best) 10%,var(--panel)),var(--panel) 60%); }
.rung .rk{ font-family:var(--display); font-weight:700; font-size:1.2rem; color:var(--faint); text-align:center; }
.rung.low .rk{ color:var(--best); }
.rung .who{ min-width:0; }
.rung .nm{ font-weight:600; font-size:.95rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-top:.3rem; }
.rung .mt{ color:var(--muted); font-size:.78rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.rung .bar{ height:10px; border-radius:99px; background:var(--line-soft); overflow:hidden; }
.rung .bar i{ display:block; height:100%; border-radius:99px; background:var(--c,#4DA3FF); }
.rung .px{ text-align:right; font-family:var(--display); font-weight:650; font-size:1.3rem; letter-spacing:-.02em;
  font-variant-numeric:tabular-nums; white-space:nowrap; }
.rung .px small{ display:block; font-family:var(--body); font-weight:400; font-size:.74rem; color:var(--muted); letter-spacing:0; }
.rung .dl{ text-align:right; font-weight:600; font-size:.85rem; color:var(--muted); font-variant-numeric:tabular-nums; }
.rung.low .dl{ color:var(--best); }
.callout{ padding:.75rem 1rem; border-radius:14px; background:var(--panel); border:1px solid var(--line-soft);
  color:var(--muted); font-size:.88rem; }
.callout b{ color:var(--text); }

/* ───────── 9. Market view cards + dataset cards ───────── */
.grid{ display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:.7rem; }
.grid.fit{ grid-template-columns:repeat(auto-fit,minmax(205px,1fr)); }
.grid.g3{ grid-template-columns:repeat(3,minmax(0,1fr)); }
.card{ --c:#4DA3FF; padding:.95rem 1.05rem; border-radius:18px; background:var(--panel);
  border:1px solid var(--line-soft); border-top:3px solid var(--c); min-width:0; }
.card.best{ border-color:color-mix(in srgb,var(--best) 55%,transparent); border-top-color:var(--best);
  box-shadow:0 0 0 1px color-mix(in srgb,var(--best) 25%,transparent); }
.card .top{ display:flex; align-items:center; justify-content:space-between; gap:.4rem; flex-wrap:wrap; }
.card .tag{ white-space:nowrap; font-size:.72rem; font-weight:700; color:#06101F; background:var(--best); padding:.1rem .5rem; border-radius:99px; }
.card .big{ font-family:var(--display); font-weight:650; font-size:1.6rem; letter-spacing:-.02em;
  font-variant-numeric:tabular-nums; margin-top:.55rem; line-height:1.1; }
.card .sub{ color:var(--muted); font-size:.8rem; margin-top:.2rem;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.card .row{ display:flex; justify-content:space-between; gap:.5rem; margin-top:.55rem; font-size:.82rem; color:var(--muted); }
.card .row b{ color:var(--text); font-weight:600; font-variant-numeric:tabular-nums; }
.card .meta{ margin-top:.55rem; font-size:.8rem; color:var(--muted); line-height:1.45; }

/* ───────── 10. Empty / landing states ───────── */
.hero{ padding:1.6rem .4rem .6rem; }
.hero h1{ font-family:var(--display); font-weight:700; font-size:2.1rem; letter-spacing:-.03em; margin:0; padding:0; line-height:1.1; }
.hero p{ color:var(--muted); margin:.5rem 0 0; font-size:1rem; max-width:62ch; }
.empty{ padding:2.2rem 1rem; text-align:center; color:var(--muted); border:1px dashed var(--line);
  border-radius:18px; background:color-mix(in srgb,var(--panel) 60%,transparent); }
.empty b{ color:var(--text); display:block; font-family:var(--display); font-size:1.15rem; margin-bottom:.3rem; }

@media (max-width: 900px){
  [data-testid="stMainBlockContainer"], .block-container{ padding:.6rem .8rem .4rem !important; }
  .rung{ grid-template-columns:1.6rem minmax(0,1fr) auto; }
  .rung .bar, .rung .dl{ display:none; }
  .top-stats{ display:none; }
  .hero h1{ font-size:1.6rem; }
  .grid.fit{ grid-template-columns:repeat(auto-fit,minmax(205px,1fr)); }
.grid.g3{ grid-template-columns:1fr; }
}
@media (prefers-reduced-motion: reduce){ *{ transition:none !important; } }
</style>
"""
