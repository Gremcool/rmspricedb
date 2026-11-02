"""
SQLite storage for the price lists.

    datasets  one row per list (name, period, currency, when it was imported, ...)
    prices    one row per product price, linked to its list

The database file ships with the app (pricedb.sqlite). If it is missing or empty, it is rebuilt from
the Excel files in datasets/. If the host has a persistent '/data' volume it is used automatically.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

import importer

BASE_DIR = Path(__file__).parent
BUNDLED_DB = BASE_DIR / "pricedb.sqlite"
SEED_DIR = BASE_DIR / "datasets"
DATA_DIR = Path("/data") if os.path.isdir("/data") else BASE_DIR
DB_PATH = DATA_DIR / "pricedb.sqlite"

PALETTE_SIZE = 8       # list colours repeat after this many lists

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL UNIQUE,
    period TEXT DEFAULT '',
    kind TEXT DEFAULT 'Price list',
    native_currency TEXT DEFAULT 'USD',
    source_file TEXT DEFAULT '',
    fmt TEXT DEFAULT '',
    color_idx INTEGER DEFAULT 0,
    imported_at TEXT,
    unpriced INTEGER DEFAULT 0,
    duplicates INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    product TEXT NOT NULL,
    detail TEXT DEFAULT '',
    pack TEXT DEFAULT '',
    category TEXT DEFAULT '',
    subcat TEXT DEFAULT '',
    code TEXT DEFAULT '',
    note TEXT DEFAULT '',
    usd REAL,
    rwf REAL
);
CREATE INDEX IF NOT EXISTS idx_prices_dataset ON prices(dataset_id);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def _usable(path: Path) -> bool:
    """True if SQLite can open this file, write to it and pass an integrity check."""
    try:
        conn = sqlite3.connect(path, timeout=5)
        try:
            conn.executescript(SCHEMA)
            conn.commit()
            return conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return False


def _choose_location() -> None:
    """
    Pick where the database lives: the persistent /data volume if there is one, otherwise the app folder.
    If that folder is read-only, or SQLite cannot use it (some synced or network drives), fall back to a
    private copy in the system temp folder, so the app starts instead of crashing.
    """
    global DATA_DIR, DB_PATH
    candidates = ([Path("/data")] if os.path.isdir("/data") else []) + [BASE_DIR, Path(tempfile.gettempdir()) / "rms_pricedb"]
    for base in candidates:
        try:
            base.mkdir(parents=True, exist_ok=True)
            target = base / "pricedb.sqlite"
            if not target.exists() and BUNDLED_DB.exists() and BUNDLED_DB != target:
                shutil.copy(BUNDLED_DB, target)
        except OSError:
            continue
        if _usable(target):
            DATA_DIR, DB_PATH = base, target
            return
        try:                                   # a damaged copy: start again from the Excel files
            target.unlink()
        except OSError:
            continue
        if _usable(target):
            DATA_DIR, DB_PATH = base, target
            return
    raise RuntimeError("Could not create a usable database in any writable folder.")


def ensure_ready() -> str | None:
    """Make sure a usable database exists. Returns a message if something needed attention."""
    _choose_location()
    if list_datasets().empty:
        return seed_from_folder()
    return None


# ───────────────────────────────────────────────────────────── reading
def list_datasets() -> pd.DataFrame:
    conn = connect()
    try:
        return pd.read_sql(
            "SELECT d.*, COUNT(p.id) AS rows FROM datasets d LEFT JOIN prices p ON p.dataset_id = d.id "
            "GROUP BY d.id ORDER BY d.id", conn)
    finally:
        conn.close()


def version() -> str:
    """Changes whenever data is added, replaced or removed (used as a cache key)."""
    conn = connect()
    try:
        n, last = conn.execute("SELECT COUNT(*), MAX(imported_at) FROM datasets").fetchone()
        rows = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
        return f"{n}-{rows}-{last}"
    finally:
        conn.close()


def build_payload(max_rows: int | None = None) -> str:
    """
    Everything the browser needs, as compact JSON: column-wise, with repeated text stored once.
    Same idea as the Sales dashboard: the page searches and compares locally, so it never waits on a rerun.
    """
    conn = connect()
    try:
        ds = pd.read_sql("SELECT * FROM datasets ORDER BY id", conn)
        px = pd.read_sql(
            "SELECT id, dataset_id, product, detail, pack, category, subcat, note, usd, rwf FROM prices", conn)
    finally:
        conn.close()

    idx = {int(d): i for i, d in enumerate(ds["id"])}
    counts = px.groupby("dataset_id").size().to_dict()
    lists = [dict(id=int(r.id), label=r.label, period=r.period or "", kind=r.kind or "",
                  cur=r.native_currency, file=r.source_file or "", color=int(r.color_idx) % PALETTE_SIZE,
                  n=int(counts.get(r.id, 0)), at=(r.imported_at or "")[:10]) for r in ds.itertuples()]

    dicts, cols = {}, {}
    for name, col in (("detail", "detail"), ("pack", "pack"), ("cat", "category"), ("sub", "subcat"), ("note", "note")):
        codes, uniques = pd.factorize(px[col].fillna(""))
        dicts[name] = uniques.tolist()
        cols[name] = codes.tolist()
    cols["l"] = [idx[int(x)] for x in px["dataset_id"]]
    cols["p"] = px["product"].tolist()
    cols["u"] = [round(float(v), 6) if v == v else None for v in px["usd"]]
    cols["r"] = [round(float(v), 2) if v == v else None for v in px["rwf"]]
    out = json.dumps({"fx": importer.FX_RWF_PER_USD, "lists": lists, "dict": dicts, "n": len(px), "cols": cols},
                     separators=(",", ":"))
    return out.replace("</", "<\\/")                        # safe to embed in a script tag


def export_csv(label: str | None = None) -> bytes:
    conn = connect()
    try:
        q = ("SELECT d.label AS List, p.product AS Product, p.detail AS Details, p.pack AS Pack, "
             "p.category AS Category, p.note AS Note, p.usd AS USD, p.rwf AS RWF "
             "FROM prices p JOIN datasets d ON d.id = p.dataset_id")
        df = pd.read_sql(q + (" WHERE d.label = ?" if label else "") + " ORDER BY d.id, p.id",
                         conn, params=[label] if label else None)
    finally:
        conn.close()
    return df.to_csv(index=False).encode("utf-8-sig")


def db_bytes() -> bytes:
    """A consistent copy of the whole database file (for backup, or to commit back to GitHub)."""
    conn = connect()
    tmp = DATA_DIR / "_export.sqlite"
    try:
        if tmp.exists():
            tmp.unlink()
        dest = sqlite3.connect(tmp)
        conn.backup(dest)
        dest.close()
        return tmp.read_bytes()
    finally:
        conn.close()
        if tmp.exists():
            tmp.unlink()


# ───────────────────────────────────────────────────────────── writing
def save_dataset(parsed: importer.Parsed, label: str, period: str, source_file: str, replace: bool) -> int:
    """Store a parsed list. Returns the number of prices saved. Replaces a list with the same name when allowed."""
    label = label.strip()
    if not label:
        raise ValueError("Give the list a name.")
    conn = connect()
    try:
        row = conn.execute("SELECT id, color_idx FROM datasets WHERE label = ?", (label,)).fetchone()
        if row and not replace:
            raise ValueError(f"A list called '{label}' already exists. Tick 'Replace' to update it.")
        now = datetime.now().isoformat(timespec="seconds")
        if row:
            ds_id, color = row
            conn.execute("DELETE FROM prices WHERE dataset_id = ?", (ds_id,))
            conn.execute(
                "UPDATE datasets SET period=?, kind=?, native_currency=?, source_file=?, fmt=?, imported_at=?, "
                "unpriced=?, duplicates=? WHERE id=?",
                (period, parsed.kind, parsed.native_currency, source_file, parsed.fmt, now,
                 parsed.unpriced, parsed.duplicates, ds_id))
        else:
            used = conn.execute("SELECT COALESCE(MAX(color_idx), -1) + 1 FROM datasets").fetchone()[0]
            cur = conn.execute(
                "INSERT INTO datasets (label, period, kind, native_currency, source_file, fmt, color_idx, imported_at, "
                "unpriced, duplicates) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (label, period, parsed.kind, parsed.native_currency, source_file, parsed.fmt,
                 used % PALETTE_SIZE, now, parsed.unpriced, parsed.duplicates))
            ds_id = cur.lastrowid
        df = parsed.df.copy()
        df.insert(0, "dataset_id", ds_id)
        df.to_sql("prices", conn, if_exists="append", index=False)
        conn.commit()
        return len(df)
    finally:
        conn.close()


def delete_dataset(label: str) -> None:
    conn = connect()
    try:
        conn.execute("DELETE FROM datasets WHERE label = ?", (label,))     # prices go with it (cascade)
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()


def seed_from_folder() -> str | None:
    """Fill an empty database from the Excel/CSV files in datasets/. Returns a note about anything skipped."""
    if not SEED_DIR.exists():
        return None
    files = [p for p in SEED_DIR.iterdir()
             if p.suffix.lower() in (".xlsx", ".xls", ".csv") and not p.name.startswith(("~$", "."))]
    parsed = []
    problems = []
    for p in files:
        try:
            parsed.append((p, importer.parse(p.name, p.read_bytes())))
        except Exception as exc:
            problems.append(f"{p.name}: {exc}")
    parsed.sort(key=lambda t: (importer.PRESETS.get(t[1].fmt, (0, 0, 0, 99))[3], t[0].name))
    for p, res in parsed:
        try:
            save_dataset(res, res.label, res.period, p.name, replace=True)
        except Exception as exc:
            problems.append(f"{p.name}: {exc}")
    return "; ".join(problems) or None
