"""
RMS Price Database: search and compare medicine, consumable and lab prices across
RHIA (Jun 2026), RMS (2024, 2025), South Africa, Sri Lanka and UNICEF price lists.

Run:  streamlit run PriceDatabase.py
"""
import base64
import hashlib
import html

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data_loader as dl
from styles import CSS

st.set_page_config(
    page_title="RMS Price Database",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.html(CSS)   # note: st.html drops any <style> containing "<tag" text, so keep raw SVG out of the CSS

MAX_TRAY = 12          # items that can be compared at once
MAX_ROWS = 1000        # rows drawn in the results grid (CSV export is never capped)
QUICK = ["Paracetamol", "Amoxicillin", "Ceftriaxone", "Insulin", "Artemether", "Oxytocin",
         "Syringe", "Gloves"]
VIEWS = ["Results", "Compare", "Market view", "Datasets"]
SORTS = ["Best match", "Price: low to high", "Price: high to low", "Name: A to Z"]
LABEL_COLOR = {s.label: s.color for s in dl.SOURCES}
esc = html.escape


# ═══════════════════════════════════════════════════════════════ data
@st.cache_data(ttl=3 * 3600, show_spinner="Loading price lists…")
def load_db():
    db, report = dl.build_database()
    db["category"] = db["category"].replace("", "Uncategorised")
    return db, report


@st.cache_data(max_entries=128, show_spinner=False)
def run_search(query: str, _db: pd.DataFrame):
    return dl.search(_db, query)


db, report = load_db()
errors = report[report["error"].notna()]


# ═══════════════════════════════════════════════════════════════ state helpers
def set_query(value: str):
    st.session_state.q = value


def pick_quick():
    if st.session_state.get("quick"):
        st.session_state.q = st.session_state.quick
        st.session_state.quick = None


def add_to_tray(uids):
    tray = list(st.session_state.get("tray", []))
    new = [int(u) for u in uids if int(u) not in tray]
    take = new[: max(0, MAX_TRAY - len(tray))]
    st.session_state.tray = tray + take
    if take:
        skipped = len(new) - len(take)
        st.toast(f"Added {len(take)} to compare" + (f" ({skipped} skipped, limit is {MAX_TRAY})" if skipped else ""),
                 icon="✅")
    elif new:
        st.toast(f"Compare is full ({MAX_TRAY} items). Remove one first.", icon="⚠️")
    else:
        st.toast("Already in compare", icon="ℹ️")


def add_selected(grid_key: str):
    try:
        rows = list(st.session_state[grid_key]["selection"]["rows"])
    except (KeyError, TypeError):
        rows = []
    shown = st.session_state.get("_shown", [])
    add_to_tray([shown[i] for i in rows if i < len(shown)])


def add_cheapest_per_source():
    shown = st.session_state.get("_shown_all", [])
    if shown:
        sub = db.loc[shown]
        add_to_tray(sub.loc[sub.groupby("source_key")["usd"].idxmin(), "uid"].tolist())


def clear_tray():
    st.session_state.tray = []


def open_compare():
    st.session_state.view = "Compare"


def selected_rows(key: str) -> int:
    try:
        return len(st.session_state[key]["selection"]["rows"])
    except (KeyError, TypeError):
        return 0


# ═══════════════════════════════════════════════════════════════ header
_MARK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">'
    '<g transform="rotate(-38 19 19)"><rect x="3" y="11.5" width="32" height="15" rx="7.5" fill="#4DA3FF"/>'
    '<path d="M19 11.5h8.5a7.5 7.5 0 0 1 0 15H19z" fill="#FFC83D"/>'
    '<rect x="7" y="14" width="10" height="3" rx="1.5" fill="#fff" opacity=".45"/></g></svg>'
)
MARK = ('<img class="mark" alt="" width="38" height="38" src="data:image/svg+xml;base64,'
        + base64.b64encode(_MARK_SVG.encode()).decode() + '">')

tray_now = [u for u in st.session_state.get("tray", []) if u in db.index]
head_l, head_r = st.columns([6, 1.25], vertical_alignment="center")
with head_l:
    st.html(
        f"""<div class="topbar">{MARK}
<div class="brand">RMS Price Database<small>Compare what the same product costs across {db['source_key'].nunique()} price lists</small></div>
<div class="top-stats"><span class="chip"><b>{len(db):,}</b> prices</span>
<span class="chip"><b>{db['source_key'].nunique()}</b> sources</span>
<span class="chip">1 USD = <b>{dl.FX_RWF_PER_USD:,.0f}</b> RWF</span></div></div>"""
    )
with head_r:
    cur = st.segmented_control("Currency", ["USD", "RWF"], default="USD", key="cur",
                               label_visibility="collapsed", width="stretch") or "USD"
pcol, ocol = ("usd", "rwf") if cur == "USD" else ("rwf", "usd")
ocur = "RWF" if cur == "USD" else "USD"

if len(errors):
    names = ", ".join(dl.SOURCE_BY_KEY[k].label for k in errors["key"])
    st.warning(f"Could not load: {names}. Check your connection, or place the Excel file in the data/ folder.")

# ═══════════════════════════════════════════════════════════════ search + filters
query = st.text_input("Search", key="q", label_visibility="collapsed",
                      placeholder="Search a medicine, brand or supply, e.g. amoxicillin 500mg, then press Enter")

f_src, f_sort, f_more = st.columns([6, 1.7, 1.1], vertical_alignment="center")
with f_src:
    sources = st.pills("Sources", [s.label for s in dl.SOURCES], selection_mode="multi", key="src",
                       label_visibility="collapsed") or []
with f_sort:
    sort = st.selectbox("Sort", SORTS, key="sort", label_visibility="collapsed")
with f_more:
    with st.popover("Filters", width="stretch"):
        cats_all = db["category"].value_counts().index.tolist()
        cats = st.multiselect("Category", cats_all, key="cats", placeholder="All categories")
        p1, p2 = st.columns(2)
        pmin = p1.number_input(f"Min price ({cur})", min_value=0.0, value=0.0, key="pmin", format="%g")
        pmax = p2.number_input(f"Max price ({cur})", min_value=0.0, value=0.0, key="pmax", format="%g",
                               help="0 means no limit")
        st.caption("Leave sources empty to search all of them.")

active = bool(query.strip() or sources or cats or pmin or pmax)

nav = st.segmented_control(
    "View", VIEWS, default="Results", key="view", label_visibility="collapsed",
    format_func=lambda v: f"Compare ({len(tray_now)})" if v == "Compare" and tray_now else v,
)
view = nav or "Results"


# ═══════════════════════════════════════════════════════════════ results (computed once)
def compute_results() -> tuple[pd.DataFrame, str]:
    hits, mode = run_search(query, db)
    if sources:
        hits = hits[hits["source"].isin(sources)]
    if cats:
        hits = hits[hits["category"].isin(cats)]
    if pmin:
        hits = hits[hits[pcol] >= pmin]
    if pmax:
        hits = hits[hits[pcol] <= pmax]
    if sort == "Price: low to high":
        hits = hits.sort_values(pcol)
    elif sort == "Price: high to low":
        hits = hits.sort_values(pcol, ascending=False)
    elif sort == "Name: A to Z":
        hits = hits.sort_values("name_norm")
    elif query.strip():
        hits = hits.sort_values(["score", pcol], ascending=[False, True])
    else:
        hits = hits.sort_values("name_norm")
    return hits, mode


res, mode = compute_results() if active else (db.iloc[0:0], "none")


# ═══════════════════════════════════════════════════════════════ small renderers
def badge(label: str) -> str:
    return f'<span class="badge" style="--c:{LABEL_COLOR.get(label, "#4DA3FF")}">{esc(label)}</span>'


def empty_state(title: str, body: str):
    st.html(f'<div class="empty"><b>{esc(title)}</b>{esc(body)}</div>')


def source_cards():
    """Landing + Datasets: one card per source."""
    cards = []
    for s in dl.SOURCES:
        sub = db[db["source_key"] == s.key]
        rep = report[report["key"] == s.key].iloc[0]
        if s.native_currency == "RWF":
            basis = f"Published in RWF. USD is converted at {dl.FX_RWF_PER_USD:,.0f}."
        else:
            basis = f"Published in USD, RWF at {dl.FX_RWF_PER_USD:,.0f}."
        hidden = []
        if rep["unpriced"]:
            hidden.append(f"{int(rep['unpriced']):,} without a price")
        if rep["duplicates"]:
            hidden.append(f"{int(rep['duplicates']):,} exact duplicates")
        hidden_txt = f" Not shown: {', '.join(hidden)}." if hidden else ""
        cards.append(
            f"""<div class="card" style="--c:{s.color}"><div class="top">{badge(s.label)}<span class="sub" style="margin:0">{esc(s.period)}</span></div>
<div class="big">{len(sub):,}<span style="font-size:.9rem;font-weight:500;color:var(--muted)"> prices</span></div>
<div class="sub">{esc(s.kind)}</div>
<div class="meta">{esc(basis)}{esc(hidden_txt)}</div></div>"""
        )
    st.html(f'<div class="grid g3">{"".join(cards)}</div>')


def stat(k, v, s="", cls=""):
    return f'<div class="stat {cls}"><div class="k">{k}</div><div class="v">{v}</div><div class="s">{s}</div></div>'


def csv_bytes(df: pd.DataFrame) -> bytes:
    out = pd.DataFrame({
        "Source": df["source"], "Product": df["product"], "Details": df["detail"],
        "Pack / unit": df["pack"], "Category": df["category"], "Code": df["code"], "Note": df["note"],
        "Price (USD)": df["usd"].round(6), "Price (RWF)": df["rwf"].round(2),
    })
    return out.to_csv(index=False).encode("utf-8-sig")


# ═══════════════════════════════════════════════════════════════ view: Results
def view_results():
    if not active:
        st.html("""<div class="hero"><h1>Find a price, then see who sells it cheaper.</h1>
<p>Search once across every list. Tick the products you care about, add them to Compare, and rank them side by side.</p></div>""")
        st.pills("Try", QUICK, key="quick", on_change=pick_quick, label_visibility="collapsed")
        source_cards()
        return

    if res.empty:
        empty_state("No matches", "Try fewer words, a shorter spelling, or clear the filters.")
        tips = dl.suggest(db, query) if query.strip() else []
        if tips:
            st.caption("Did you mean")
            cols = st.columns(len(tips))
            for c, t in zip(cols, tips):
                c.button(t, key=f"tip_{t}", on_click=set_query, args=(t,), width="stretch")
        return

    n = len(res)
    low = res.loc[res[pcol].idxmin()]
    st.html(
        '<div class="strip">'
        + stat("Matches", f"{n:,}", f"in {res['source_key'].nunique()} of {db['source_key'].nunique()} sources")
        + stat("Lowest price", dl.fmt_price(low[pcol], cur), f"{esc(low['source'])}: {esc(low['product'])}", "best")
        + stat("Median price", dl.fmt_price(res[pcol].median(), cur), f"per unit as published, in {cur}")
        + stat("Highest price", dl.fmt_price(res[pcol].max(), cur), f"{dl.fmt_price(res[ocol].max(), ocur)}")
        + "</div>"
    )
    if mode == "substring":
        st.caption("No word-start matches, so showing matches found anywhere inside words.")

    shown = res.head(MAX_ROWS)
    st.session_state["_shown"] = shown["uid"].tolist()
    st.session_state["_shown_all"] = res["uid"].tolist()
    sig = hashlib.md5(repr((query.strip().lower(), tuple(sources), tuple(cats), sort, pmin, pmax)).encode()).hexdigest()[:8]
    gkey = f"grid_{sig}"
    n_sel = selected_rows(gkey)

    b1, b2, b3, b4, b5 = st.columns([1.25, 1.55, 1.3, 1.15, 2.6], vertical_alignment="center")
    b1.button(f"Add selected ({n_sel})" if n_sel else "Add selected", type="primary", disabled=n_sel == 0,
              on_click=add_selected, args=(gkey,), width="stretch", help="Tick rows in the table first")
    b2.button("Add cheapest per source", on_click=add_cheapest_per_source, width="stretch",
              help="Adds the lowest-priced match from each source. Check strength and form are comparable.")
    if tray_now:
        b3.button(f"Open compare ({len(tray_now)})", on_click=open_compare, width="stretch")
    b4.download_button("Export CSV", data=lambda: csv_bytes(res), file_name="rms_price_search.csv",
                       mime="text/csv", width="stretch")
    b5.caption(f"Showing {len(shown):,} of {n:,}" + ("  (narrow the search to see the rest, or export CSV)" if n > MAX_ROWS else ""))

    view_df = pd.DataFrame({
        "Source": shown["source"].values,
        "Product": shown["product"].values,
        f"Price ({cur})": shown[pcol].values,
        f"Price ({ocur})": shown[ocol].values,
        "Pack / unit": shown["pack"].values,
        "Details": shown["detail"].values,
        "Category": shown["category"].replace("Uncategorised", "").values,
        "Note": shown["note"].values,
    })
    fmt = {f"Price ({cur})": lambda v: dl.fmt_price(v, cur), f"Price ({ocur})": lambda v: dl.fmt_price(v, ocur)}
    sty = view_df.style.format(fmt)
    paint = getattr(sty, "map", None) or sty.applymap
    sty = paint(lambda v: f"color:{LABEL_COLOR.get(v, '#E9EFFA')};font-weight:600", subset=["Source"])
    sty = paint(lambda v: "font-weight:600", subset=[f"Price ({cur})"])

    st.dataframe(
        sty, key=gkey, on_select="rerun", selection_mode="multi-row", hide_index=True,
        height=min(620, 38 + 35 * len(view_df)), width="stretch",
        column_config={
            "Source": st.column_config.TextColumn(width="medium"),
            "Product": st.column_config.TextColumn(width="large"),
            f"Price ({cur})": st.column_config.TextColumn(width="small"),
            f"Price ({ocur})": st.column_config.TextColumn(width="small"),
            "Pack / unit": st.column_config.TextColumn(width="small", help="Selling unit or pack size, as published"),
            "Note": st.column_config.TextColumn(
                width="small", help="RHIA: who may prescribe it (see Datasets for the legend). RMS Master: Incoterm."),
        },
    )
    note = "Prices are per selling unit as published, so check Pack / unit before comparing across sources."
    if (res["source_key"] == "rhia").any():
        note += f" RHIA publishes in RWF; its USD is converted at {dl.FX_RWF_PER_USD:,.0f}, the rate used across all lists."
    st.caption(note)


# ═══════════════════════════════════════════════════════════════ view: Compare
def ladder(items: pd.DataFrame) -> str:
    items = items.sort_values(pcol)
    lo, hi = items[pcol].min(), items[pcol].max()
    rows = []
    for rank, (_, r) in enumerate(items.iterrows(), 1):
        p = r[pcol]
        is_low = p == lo and len(items) > 1
        if len(items) == 1:
            delta = ""
        elif is_low:
            delta = "Lowest"
        else:
            ratio = p / lo
            delta = f"{ratio:.1f}× lowest" if ratio >= 10 else f"+{(ratio - 1) * 100:.0f}%"
        other = dl.fmt_price(r[ocol], ocur)
        if dl.SOURCE_BY_KEY[r["source_key"]].native_currency == ocur and r["source_key"] == "rhia":
            other += " published"
        meta = ", ".join(x for x in [r["detail"], f"pack: {r['pack']}" if r["pack"] else ""] if x)
        width = max(p / hi * 100, 1.5)
        rows.append(
            f"""<div class="rung {'low' if is_low else ''}" style="--c:{LABEL_COLOR[r['source']]}">
<div class="rk">{rank}</div>
<div class="who">{badge(r['source'])}<div class="nm" title="{esc(r['product'])}">{esc(r['product'])}</div><div class="mt">{esc(meta)}</div></div>
<div class="bar"><i style="width:{width:.1f}%"></i></div>
<div class="px">{dl.fmt_price(p, cur)}<small>{other}</small></div>
<div class="dl">{delta}</div></div>"""
        )
    return f'<div class="ladder">{"".join(rows)}</div>'


def view_compare():
    if not tray_now:
        empty_state("Nothing to compare yet",
                    "In Results, tick products and press Add selected, or use Add cheapest per source.")
        return

    tkey = "tray_ms_" + hashlib.md5(",".join(map(str, tray_now)).encode()).hexdigest()[:6]
    kept = st.multiselect(
        "In comparison", tray_now, default=tray_now, key=tkey, label_visibility="collapsed",
        format_func=lambda u: f"{db.at[u, 'source']}: {db.at[u, 'product'][:70]}",
    )
    if kept != tray_now:
        st.session_state.tray = list(kept)
    items = db.loc[kept] if kept else db.iloc[0:0]
    if items.empty:
        empty_state("Compare is empty", "Go back to Results and add some products.")
        return

    if len(items) == 1:
        st.info("Add at least one more product to see a comparison.")
    else:
        lo_r = items.loc[items[pcol].idxmin()]
        hi_r = items.loc[items[pcol].idxmax()]
        spread = hi_r[pcol] / lo_r[pcol] if lo_r[pcol] else float("inf")
        msg = (f"<b>{esc(lo_r['product'])}</b> from {esc(lo_r['source'])} is the lowest at "
               f"<b>{dl.fmt_price(lo_r[pcol], cur)}</b>. The highest costs <b>{spread:.1f}×</b> as much "
               f"({dl.fmt_price(hi_r[pcol], cur)}).")
        msg += " Strength, form and pack size can differ between these rows, so compare like with like before relying on the gap."
        st.html(f'<div class="callout">{msg}</div>')

    st.html(ladder(items))

    c1, c2, _ = st.columns([1.3, 1.1, 5])
    c1.download_button("Export comparison", data=lambda: csv_bytes(items), file_name="rms_price_compare.csv",
                       mime="text/csv", width="stretch")
    c2.button("Clear all", on_click=clear_tray, width="stretch")


# ═══════════════════════════════════════════════════════════════ view: Market view
def view_market():
    if not active or res.empty:
        empty_state("Search for a product first",
                    "Market view shows how each source prices your search: lowest, median, highest.")
        return

    g = res.groupby("source").agg(n=("uid", "size"), lo=(pcol, "min"), med=(pcol, "median"), hi=(pcol, "max"))
    g = g.sort_values("med")
    best_lo = g["lo"].min()
    cards = []
    for label, r in g.iterrows():
        sub = res[res["source"] == label]
        lo_row = sub.loc[sub[pcol].idxmin()]
        best = r["lo"] == best_lo
        cards.append(
            f"""<div class="card {'best' if best else ''}" style="--c:{LABEL_COLOR[label]}">
<div class="top">{badge(label)}{'<span class="tag">Lowest</span>' if best else ''}</div>
<div class="big">{dl.fmt_price(r['lo'], cur)}</div>
<div class="sub" title="{esc(lo_row['product'])}">{esc(lo_row['product'])}</div>
<div class="row"><span>Median</span><b>{dl.fmt_price(r['med'], cur)}</b></div>
<div class="row"><span>Highest</span><b>{dl.fmt_price(r['hi'], cur)}</b></div>
<div class="row"><span>Matches</span><b>{int(r['n']):,}</b></div></div>"""
        )
    st.html(f'<div class="grid fit">{"".join(cards)}</div>')

    top = st.columns([6, 1.3], vertical_alignment="center")
    top[0].caption("Each dot is one product. Diamonds mark the median per source.")
    log = top[1].toggle("Log scale", value=True, help="Spreads out prices that differ by orders of magnitude")

    plot = res if len(res) <= 3000 else res.sample(3000, random_state=1)
    order = g.index.tolist()
    plot = plot.assign(Price=plot[pcol], Pack=plot["pack"], Source=plot["source"], Product=plot["product"])
    fig = px.strip(plot, x="Price", y="Source", color="Source", color_discrete_map=LABEL_COLOR,
                   category_orders={"Source": order}, hover_name="Product", hover_data={"Pack": True, "Source": False},
                   log_x=log)
    fig.update_traces(marker=dict(size=8, opacity=.8, line=dict(width=0)), jitter=.6)
    fig.add_trace(go.Scatter(
        x=g["med"], y=g.index, mode="markers", name="Median", hoverinfo="skip",
        marker=dict(symbol="diamond", size=14, color="#FFFFFF", line=dict(color="#0A1020", width=2)),
    ))
    fig.update_layout(
        height=110 + 62 * len(order), showlegend=False, margin=dict(l=0, r=8, t=6, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#8B9BB8", family="DM Sans, system-ui, sans-serif"),
        xaxis=dict(title=f"Price per unit ({cur})", gridcolor="#1B2745", zeroline=False,
                   tickprefix="$" if cur == "USD" else "RWF "),
        yaxis=dict(title="", gridcolor="#1B2745", categoryorder="array", categoryarray=order[::-1]),
        hoverlabel=dict(bgcolor="#16213A", font=dict(color="#E9EFFA")),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ═══════════════════════════════════════════════════════════════ view: Datasets
def view_datasets():
    source_cards()
    cols = st.columns(len(dl.SOURCES))
    for col, s in zip(cols, dl.SOURCES):
        col.download_button(f"{s.label} CSV", data=lambda k=s.key: csv_bytes(db[db["source_key"] == k]),
                            file_name=f"{s.key}_prices.csv", mime="text/csv", key=f"dl_{s.key}", width="stretch")

    c1, c2 = st.columns([1.4, 6], vertical_alignment="center")
    c1.button("Reload price lists", on_click=st.cache_data.clear, width="stretch")
    c2.caption(
        f"Every list is shown in USD and RWF at 1 USD = {dl.FX_RWF_PER_USD:,.0f} RWF. "
        "Prices cache for 3 hours. Source of each file: "
        + ", ".join(f"{dl.SOURCE_BY_KEY[r.key].label} ({r.origin})" for r in report.itertuples() if not r.error)
    )

    legend = dl.rhia_legend()
    if legend:
        with st.expander("RHIA prescriber codes (the Note column)"):
            st.dataframe(pd.DataFrame(legend, columns=["Code", "Meaning"]), hide_index=True, width="stretch",
                         height=min(420, 38 + 35 * len(legend)))


{"Results": view_results, "Compare": view_compare, "Market view": view_market, "Datasets": view_datasets}[view]()
