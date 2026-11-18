"""
RMS Price Database
==================
The whole interface is a single HTML page (index.html) injected into Streamlit, the same pattern as the
Sales dashboard. It searches, compares and switches theme locally in the browser, so it never waits on a
Streamlit rerun. Streamlit only does the parts a browser page cannot: the database and the hidden
admin panel (a quiet link in the page footer) where an admin uploads lists or a whole database file.

Run:  streamlit run PriceDatabase.py
"""
import hmac
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import database
import importer

st.set_page_config(page_title="RMS Price Database", page_icon="💊", layout="wide",
                   initial_sidebar_state="collapsed")

HERE = Path(__file__).parent
# index.html sits next to this file (so no folder has to be uploaded); ui/index.html is also accepted.
UI_FILE = next((p for p in (HERE / "index.html", HERE / "ui" / "index.html") if p.exists()), HERE / "index.html")

# Everything Streamlit draws around the page is removed, the HTML page fills the window, and the
# native Admin button stays out of sight (the page's footer link clicks it).
# (No angle brackets in here: st.html drops a style block that contains tag-like text.)
st.html("""
<style>
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], [data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"], #MainMenu, footer { display:none !important; }
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background:#FBFBFA !important; }
html[data-rms-theme="dark"] body, html[data-rms-theme="dark"] .stApp,
html[data-rms-theme="dark"] [data-testid="stAppViewContainer"], html[data-rms-theme="dark"] [data-testid="stMain"] { background:#0B0B0C !important; }
[data-testid="stMainBlockContainer"], .block-container, .main .block-container { padding:0 !important; max-width:100% !important; width:100% !important; }
[data-testid="stVerticalBlock"] { gap:0 !important; }
[data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > style), .element-container:has(> style) { display:none !important; }
iframe { width:100% !important; border:0 !important; display:block; height:100vh !important; height:100dvh !important; }
/* The page's footer Admin link clicks this button. The page hides it; with ?admin=1 in the address it stays
   visible here, just below the page, as a backup way in. */
.st-key-manage { padding:8px 16px; text-align:center; }
/* the Admin dialog: keep Streamlit's default red out of it */
[data-testid="stBaseButton-primary"] { background:#151514 !important; border-color:#151514 !important; color:#fff !important; }
[data-testid="stBaseButton-primary"] p { color:#fff !important; }
button[role="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"] p { color:#151514 !important; }
[data-baseweb="tab-highlight"] { background:#151514 !important; }
</style>
""")


# ───────────────────────────────────────────────────────────── data
@st.cache_data(show_spinner=False, max_entries=2)
def build_page(version: str, ui_mtime: float) -> str:
    """The HTML page with the database baked in. Rebuilt only when the data or the page file changes."""
    return UI_FILE.read_text(encoding="utf-8").replace("__DATA__", database.build_payload())


if not UI_FILE.exists():
    st.error("**index.html is missing from your GitHub repository.** It is the page itself and must sit in the same "
             "place as PriceDatabase.py. Upload index.html (from the zip) to the repository, then reboot the app.")
    st.stop()

try:
    seed_note = database.ensure_ready()
except Exception as exc:                          # never leave the page spinning: say what happened
    st.error(f"The price database could not be opened: {exc}")
    st.stop()


# ───────────────────────────────────────────────────────────── admin
MAX_TRIES = 5


def admin_password() -> str | None:
    """
    Optional. Set the RMS_ADMIN_PASSWORD environment variable, or `admin_password` in .streamlit/secrets.toml
    (or in the Secrets settings on Streamlit Community Cloud). Streamlit is only asked for secrets when a
    secrets file exists, because older versions print a red error when it does not.
    """
    env = os.environ.get("RMS_ADMIN_PASSWORD")
    if env:
        return env
    for f in (Path.home() / ".streamlit" / "secrets.toml", Path.cwd() / ".streamlit" / "secrets.toml"):
        if f.exists():
            try:
                if "admin_password" in st.secrets:
                    return str(st.secrets["admin_password"])
            except Exception:
                pass
    return None


def refresh_everything():
    st.cache_data.clear()
    st.rerun()


@st.cache_data(show_spinner=False, max_entries=8)
def parse_upload(name: str, data: bytes, currency: str | None):
    return importer.parse(name, data, currency)


def show_table(df: pd.DataFrame, **kwargs):
    try:
        st.dataframe(df, hide_index=True, width="stretch", **kwargs)
    except Exception:                               # older Streamlit has no width="stretch"
        st.dataframe(df, hide_index=True, use_container_width=True, **kwargs)


@st.dialog("Admin", width="large")
def admin_dialog():
    pwd = admin_password()
    if pwd and not st.session_state.get("admin_ok"):
        tries = st.session_state.get("admin_tries", 0)
        if tries >= MAX_TRIES:
            st.error("Too many wrong attempts. Reload the page to try again.")
            return
        st.caption("Enter the admin password.")
        entered = st.text_input("Admin password", type="password", label_visibility="collapsed", placeholder="Admin password")
        if st.button("Unlock", type="primary"):
            if hmac.compare_digest(entered.encode(), pwd.encode()):
                st.session_state.admin_ok = True
                st.session_state.admin_tries = 0
                st.rerun(scope="fragment")
            else:
                st.session_state.admin_tries = tries + 1
                time.sleep(1)                       # slows down guessing
                st.error("That password is not right.")
        return

    if not pwd:
        st.warning("No admin password is set, so anyone who finds this panel can change the data. Set one "
                   "(see the README, section Admin password) before sharing the app.")

    lists = database.list_datasets()
    tab_lists, tab_add, tab_db, tab_backup = st.tabs(["Lists", "Add a list", "Upload database", "Backup"])

    with tab_lists:
        if lists.empty:
            st.info("No lists yet. Add one in the next tab.")
        else:
            table = pd.DataFrame({
                "List": lists["label"], "Period": lists["period"], "Prices": lists["rows"],
                "Published in": lists["native_currency"], "File": lists["source_file"],
                "Added": lists["imported_at"].str[:10],
            })
            show_table(table, column_config={"Prices": st.column_config.NumberColumn(format="%d")})
            if int(lists["unpriced"].sum() + lists["duplicates"].sum()):
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
                   "“Unit Price (USD)” or “Unit Price (RWF)”. Uploading a list with the same name replaces it.")
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

    with tab_db:
        st.caption("Replace everything with a whole database file, for example the pricedb.sqlite you downloaded from "
                   "Backup on another copy of this app. The file is checked first and nothing changes if it is not a "
                   "valid RMS price database.")
        dbf = st.file_uploader("Database file", type=["sqlite", "sqlite3", "db"], key="dbfile", label_visibility="collapsed")
        if dbf is not None:
            try:
                info = database.inspect_database(dbf.getvalue())
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Valid price database: {len(info['lists'])} lists, {info['prices']:,} prices.")
                show_table(info["lists"], column_config={"Prices": st.column_config.NumberColumn(format="%d")})
                st.warning(f"This replaces the current database ({len(lists)} lists, {int(lists['rows'].sum()):,} prices). "
                           "The current one is kept as a backup copy on the server.")
                ok = st.checkbox("Yes, replace the current database")
                if st.button("Replace database", type="primary", disabled=not ok):
                    try:
                        database.replace_database(dbf.getvalue())
                    except Exception as exc:
                        st.error(str(exc))
                    else:
                        st.toast("Database replaced")
                        refresh_everything()

    with tab_backup:
        if str(database.DATA_DIR) == "/data":
            st.caption("Changes are saved on this server's persistent volume.")
        else:
            st.caption("Changes are saved on the server's disk. Free hosts such as Streamlit Community Cloud reset that "
                       "disk when the app restarts, so download the database and commit it to GitHub as "
                       "pricedb.sqlite to keep your changes.")
        st.download_button("Download database (pricedb.sqlite)", data=database.db_bytes(), file_name="pricedb.sqlite",
                           mime="application/octet-stream")
        st.download_button("Download all prices (CSV)", data=database.export_csv(), file_name="rms_all_prices.csv",
                           mime="text/csv")


# ───────────────────────────────────────────────────────────── page
if seed_note:
    st.warning(f"Some files in datasets/ could not be imported: {seed_note}")
if database.list_datasets().empty:
    st.warning("The database has no price lists yet. Upload pricedb.sqlite (or the datasets folder) to your GitHub "
               "repository, or add a list from the Admin link in the page footer.")

try:
    page_html = build_page(database.version(), UI_FILE.stat().st_mtime)
except Exception as exc:
    st.error(f"The page could not be built: {exc}")
    st.stop()
if hasattr(st, "iframe"):                       # current Streamlit
    st.iframe(page_html, height=800)
else:                                           # older Streamlit (st.components.v1.html is deprecated in new versions)
    components.html(page_html, height=800, scrolling=False)

# The page's footer link clicks this button. The page hides it; open the app with ?admin=1 to see it here instead.
if st.button("Admin", key="manage"):
    admin_dialog()
