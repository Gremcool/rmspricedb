"""
RMS Price Database
==================
The whole interface is a single HTML page (ui/index.html) injected into Streamlit, the same pattern as the
Sales dashboard. It searches, compares and switches theme locally in the browser, so it never waits on a
Streamlit rerun. Streamlit only does the parts a browser page cannot: the database and the upload dialog.

Run:  streamlit run PriceDatabase.py
"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database
import importer

st.set_page_config(page_title="RMS Price Database", page_icon="💊", layout="wide",
                   initial_sidebar_state="collapsed")

UI_FILE = Path(__file__).parent / "ui" / "index.html"

# Everything Streamlit draws around the page is removed, the HTML page fills the window, and the
# native "Manage" button is floated into the empty corner of the page's top bar.
# (No angle brackets in here: st.html drops a style block that contains tag-like text.)
st.html("""
<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"], #MainMenu, footer { display:none !important; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:#FBFBFA !important; }
html[data-rms-theme="dark"] body, html[data-rms-theme="dark"] .stApp,
html[data-rms-theme="dark"] [data-testid="stAppViewContainer"], html[data-rms-theme="dark"] [data-testid="stMain"] { background:#0B0B0C !important; }
[data-testid="stMain"] { overflow:hidden !important; }
[data-testid="stMainBlockContainer"], .block-container { padding:0 !important; max-width:100% !important; }
[data-testid="stVerticalBlock"] { gap:0 !important; }
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > style) { display:none !important; }
[data-testid="stIFrame"] { height:100vh !important; height:100dvh !important; width:100% !important; border:0 !important; display:block; }

/* the Manage dialog: keep Streamlit's default red out of it */
[data-testid="stBaseButton-primary"] { background:#151514 !important; border-color:#151514 !important; color:#fff !important; }
[data-testid="stBaseButton-primary"] p { color:#fff !important; }
button[role="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"] p { color:#151514 !important; }
[data-baseweb="tab-highlight"] { background:#151514 !important; }
[data-testid="stDialog"] [role="dialog"] { border-radius:16px; }

.st-key-manage { position:fixed; top:10px; right:20px; z-index:100; width:auto !important; }
.st-key-manage button { height:36px; min-height:36px; padding:0 13px; border-radius:10px; font-size:13.5px; font-weight:550;
  background:#fff; color:#151514; border:1px solid #E9E9E5; }
html[data-rms-drawer] .st-key-manage { display:none !important; }
.st-key-manage button:hover { background:#F4F4F1; border-color:#D9D9D3; color:#151514; }
.st-key-manage button p { font-size:13.5px; font-weight:550; }
html[data-rms-theme="dark"] .st-key-manage button { background:#131314; color:#F1F1EF; border-color:#232326; }
html[data-rms-theme="dark"] .st-key-manage button:hover { background:#18181A; border-color:#34343A; color:#F1F1EF; }
@media (max-width: 640px) {
  .st-key-manage { right:12px; }
  .st-key-manage button { padding:0 10px; }
  .st-key-manage button p { display:none; }
}
</style>
""")


# ───────────────────────────────────────────────────────────── data
@st.cache_data(show_spinner=False, max_entries=2)
def build_page(version: str, ui_mtime: float) -> str:
    """The HTML page with the database baked in. Rebuilt only when the data or the page file changes."""
    return UI_FILE.read_text(encoding="utf-8").replace("__DATA__", database.build_payload())


seed_note = database.ensure_ready()


# ───────────────────────────────────────────────────────────── admin
def admin_password() -> str | None:
    """Optional. Set `admin_password` in .streamlit/secrets.toml, or the RMS_ADMIN_PASSWORD environment variable."""
    try:
        if "admin_password" in st.secrets:
            return str(st.secrets["admin_password"])
    except Exception:
        pass
    return os.environ.get("RMS_ADMIN_PASSWORD") or None


def refresh_everything():
    st.cache_data.clear()
    st.rerun()


@st.cache_data(show_spinner=False, max_entries=8)
def parse_upload(name: str, data: bytes, currency: str | None):
    return importer.parse(name, data, currency)


@st.dialog("Manage price lists", width="large")
def manage_dialog():
    pwd = admin_password()
    if pwd and not st.session_state.get("admin_ok"):
        st.caption("Enter the admin password to add, replace or remove lists.")
        entered = st.text_input("Admin password", type="password", label_visibility="collapsed", placeholder="Admin password")
        if st.button("Unlock", type="primary"):
            if entered == pwd:
                st.session_state.admin_ok = True
                st.rerun(scope="fragment")
            else:
                st.error("That password is not right.")
        return

    lists = database.list_datasets()
    tab_lists, tab_add, tab_backup = st.tabs(["Lists", "Add or update a list", "Backup"])

    with tab_lists:
        if lists.empty:
            st.info("No lists yet. Add one in the next tab.")
        else:
            table = pd.DataFrame({
                "List": lists["label"], "Period": lists["period"], "Prices": lists["rows"],
                "Published in": lists["native_currency"], "File": lists["source_file"],
                "Added": lists["imported_at"].str[:10],
            })
            st.dataframe(table, hide_index=True, width="stretch",
                         column_config={"Prices": st.column_config.NumberColumn(format="%d")})
            hidden = int(lists["unpriced"].sum() + lists["duplicates"].sum())
            if hidden:
                st.caption(f"{int(lists['unpriced'].sum()):,} rows without a price and "
                           f"{int(lists['duplicates'].sum()):,} exact duplicates were left out when importing.")
            with st.expander("Remove a list"):
                target = st.selectbox("List to remove", lists["label"].tolist(), label_visibility="collapsed")
                if st.button(f"Remove {target}"):
                    database.delete_dataset(target)
                    st.toast(f"Removed {target}")
                    refresh_everything()

    with tab_add:
        st.caption("Upload an Excel or CSV price list. The six built-in layouts are recognised automatically; "
                   "any other file needs a product or description column and a price column named like "
                   "“Unit Price (USD)” or “Unit Price (RWF)”.")
        f = st.file_uploader("Price list file", type=["xlsx", "xls", "csv"], label_visibility="collapsed")
        if f is not None:
            data, currency = f.getvalue(), None
            try:
                parsed = parse_upload(f.name, data, currency)
            except importer.NeedsCurrency as exc:
                st.warning(str(exc))
                currency = st.radio("Prices in this file are in", ["USD", "RWF"], horizontal=True)
                parsed = parse_upload(f.name, data, currency)
            except ValueError as exc:
                st.error(str(exc))
                parsed = None
            if parsed is not None:
                kind = "a custom list" if parsed.fmt == "generic" else f"a {importer.PRESETS[parsed.fmt][0]} list"
                skipped = parsed.unpriced + parsed.duplicates
                st.success(f"Recognised as {kind}: {len(parsed.df):,} prices"
                           + (f" ({skipped:,} rows skipped: no price or exact duplicate)" if skipped else "") + ".")
                c1, c2 = st.columns([3, 2])
                label = c1.text_input("List name", value=parsed.label, help="Shown on every result from this list.")
                period = c2.text_input("Period", value=parsed.period, help="For example Jun 2026 or 2025.")
                exists = label.strip() in set(lists["label"])
                replace = True
                if exists:
                    replace = st.checkbox(f"Replace the existing “{label.strip()}” list", value=True)
                if st.button("Add to database", type="primary", disabled=not label.strip() or (exists and not replace)):
                    try:
                        n = database.save_dataset(parsed, label, period.strip(), f.name, replace)
                    except Exception as exc:
                        st.error(str(exc))
                    else:
                        st.toast(f"Saved {n:,} prices to {label.strip()}")
                        refresh_everything()

    with tab_backup:
        if str(database.DATA_DIR) == "/data":
            st.caption("Changes are saved on this server's persistent volume.")
        else:
            st.caption("Changes are saved on the server's disk. Free hosts such as Streamlit Community Cloud reset that "
                       "disk when the app restarts, so download the database and commit it to GitHub as "
                       "pricedb.sqlite to keep your changes.")
        st.download_button("Download database (pricedb.sqlite)", data=database.db_bytes, file_name="pricedb.sqlite",
                           mime="application/octet-stream")
        st.download_button("Download all prices (CSV)", data=database.export_csv, file_name="rms_all_prices.csv",
                           mime="text/csv")
        if not pwd:
            st.caption("Tip: set an admin password (see README) so only you can change the data.")


# ───────────────────────────────────────────────────────────── page
if seed_note:
    st.warning(f"Some files in datasets/ could not be imported: {seed_note}")

page_html = build_page(database.version(), UI_FILE.stat().st_mtime)
if hasattr(st, "iframe"):                       # current Streamlit
    st.iframe(page_html, height=800)
else:                                           # older Streamlit (st.components.v1.html is deprecated in new versions)
    components.html(page_html, height=800, scrolling=False)

if st.button("Manage", icon=":material/settings:", key="manage", help="Add, update or remove price lists"):
    manage_dialog()
