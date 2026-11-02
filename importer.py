"""
Turns an uploaded price list (Excel or CSV) into one clean table.

The six lists you already use are recognised by their column layout (not by file name, so renamed
files still work). Any other file is read with a generic rule: a product/description column and a
price column whose header says USD or RWF.

Every list ends up with the same columns:
    product, detail, pack, category, subcat, code, note, usd, rwf
Both currencies are always filled in at FX_RWF_PER_USD, the rate your existing lists already use.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

import pandas as pd

FX_RWF_PER_USD = 1300.0
COLUMNS = ["product", "detail", "pack", "category", "subcat", "code", "note", "usd", "rwf"]


# ───────────────────────────────────────────────────────────── helpers
def _clean(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = re.sub(r"\s+", " ", str(v).replace("\xa0", " ")).strip()
    return s or None


def _num_text(v) -> str | None:
    """20.0 -> '20', 0.012 -> '0.012', '28' -> '28'."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return str(int(v)) if float(v).is_integer() else f"{v:g}"
    return _clean(v)


def _fix_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c).replace("\xa0", " ")).strip() for c in df.columns]
    return df


def _sentence(s: str) -> str:
    s = _clean(s) or ""
    return s[:1].upper() + s[1:].lower() if s.isupper() else s


def _blank(n: int = 0) -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS, index=range(n))


def _find(cols: list[str], *needles: str) -> str | None:
    for c in cols:
        if any(n in c.lower() for n in needles):
            return c
    return None


MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def guess_period(filename: str) -> str:
    """'..._JULY_2024.xlsx' -> 'Jul 2024', '..._2025.xlsx' -> '2025', otherwise ''."""
    stem = re.sub(r"[_\-.]+", " ", filename.rsplit(".", 1)[0])
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+((?:19|20)\d{2})\b", stem, re.I)
    if m:
        return f"{m.group(1).title()} {m.group(2)}"
    m = re.search(r"\b((?:19|20)\d{2})\b", stem)
    return m.group(1) if m else ""


def prettify(filename: str) -> str:
    stem = re.sub(r"[_]+", " ", filename.rsplit(".", 1)[0]).strip()
    return re.sub(r"\s+", " ", stem)


# ───────────────────────────────────────────────────────────── file access
class Source:
    """Holds the uploaded bytes so a file can be read several times."""

    def __init__(self, name: str, data: bytes):
        self.name, self.data = name, data
        self.is_csv = name.lower().endswith(".csv")

    def read(self, **kw) -> pd.DataFrame:
        buf = BytesIO(self.data)
        return pd.read_csv(buf, **kw) if self.is_csv else pd.read_excel(buf, **kw)


# ───────────────────────────────────────────────────────────── layout parsers
def _parse_rms(src: Source, cat_prefix: str, name_col: str, pack_col: str, note_col: str | None):
    raw = _fix_cols(src.read())
    cat_col = next(c for c in raw.columns if c.upper().startswith(cat_prefix.upper()))
    out = _blank(len(raw))
    out["product"] = raw[name_col].map(_clean)
    out["pack"] = raw[pack_col].map(_num_text)
    out["category"] = raw[cat_col].map(_clean)
    if note_col:
        out["note"] = raw[note_col].map(_clean)
    out["usd"] = pd.to_numeric(raw["Unit Price (USD)"], errors="coerce")
    out["rwf"] = pd.to_numeric(raw["Unit Price (RWF)"], errors="coerce")
    return out


def _parse_sa(src: Source):
    raw = _fix_cols(src.read()).reset_index(drop=True)
    # A row with a dosage form starts a product; rows without one are extra ingredients of the
    # combination product above it (e.g. Lidocaine + Adrenaline).
    group = raw["Dosage Form"].notna().cumsum()

    def component(r) -> str:
        parts = [_clean(r["Active Ingredients"]), _num_text(r["Strength"]), _clean(r["Unit"])]
        return " ".join(p for p in parts if p)

    raw["_comp"] = raw.apply(component, axis=1)
    g = raw.groupby(group, sort=True).agg(
        product=("_comp", lambda s: " + ".join(x for x in s if x)),
        detail=("Dosage Form", "first"), pack=("Pack Size", "first"),
        usd=("Unit Price (USD)", "first"), rwf=("Unit Price (RWF)", "first"),
    ).reset_index(drop=True)
    out = _blank(len(g))
    out["product"] = g["product"].map(_clean)
    out["detail"] = g["detail"].map(_clean)
    out["pack"] = g["pack"].map(_num_text)
    out["usd"] = pd.to_numeric(g["usd"], errors="coerce")
    out["rwf"] = pd.to_numeric(g["rwf"], errors="coerce")
    return out


def _parse_lk(src: Source):
    raw = _fix_cols(src.read())
    out = _blank(len(raw))
    out["product"] = raw["medium_description"].map(_clean).fillna(raw["short_description"].map(_clean))
    out["usd"] = pd.to_numeric(raw["Unit Price (USD)"], errors="coerce")
    out["rwf"] = pd.to_numeric(raw["Unit Price (RWF)"], errors="coerce")
    return out


def _parse_unicef(src: Source):
    raw = _fix_cols(src.read())
    out = _blank(len(raw))
    out["product"] = raw["Medicine"].map(_clean)
    out["usd"] = pd.to_numeric(raw["Unit Price (USD)"], errors="coerce")
    out["rwf"] = pd.to_numeric(raw["Unit Price (RWF)"], errors="coerce")
    return out


_TOP_LEVEL = re.compile(r"^([A-Z])\s*\.\s*(\S.*)$")


def _rhia_header_row(src: Source) -> int | None:
    """Row index of the 'DRUG_CODE' header in the first sheet, or None if this is not an RHIA file."""
    try:
        head = src.read(sheet_name=0, header=None, nrows=25)
    except Exception:
        return None
    for i, row in head.iterrows():
        cells = {str(v).strip().upper() for v in row if pd.notna(v)}
        if "DRUG_CODE" in cells and "DESIGNATION" in cells:
            return int(i)
    return None


def _parse_rhia(src: Source, header_row: int):
    """
    RHIA tariff: banner rows, then section-header rows (no code, no price) mixed with priced rows.
    'A. ALIMENTARY TRACT...' becomes the category, 'A02 DRUGS FOR ACID RELATED DISORDERS' the sub-category.
    """
    raw = src.read(sheet_name=0, header=None, skiprows=header_row).iloc[:, :7]
    raw.columns = ["sn", "code", "generic", "designation", "instr", "unit", "price"]
    cat = subcat = None
    rows = []
    for r in raw.itertuples(index=False):
        sn = _clean(r.sn)
        if pd.isna(r.code) and pd.isna(r.designation) and pd.isna(r.price):
            if not sn:
                continue
            m = _TOP_LEVEL.match(sn)
            if m:
                cat, subcat = _sentence(m.group(2)), None
            elif re.match(r"^V\d", sn):
                cat, subcat = "Various", re.sub(r"^\S+\s+", "", sn)
            elif sn.upper().startswith("NON CLASSIFIED"):
                cat, subcat = "Non-classified devices and products", None
            else:
                subcat = _sentence(re.sub(r"^[A-Z0-9]+\s*[.\s]*\s*", "", sn, count=1))
            continue
        if pd.isna(r.code) or str(r.sn).strip().upper() == "SN":
            continue
        rows.append((_clean(r.designation), _clean(r.generic), _clean(r.unit), cat, subcat,
                     _clean(r.code), _clean(r.instr), r.price))
    out = pd.DataFrame(rows, columns=["product", "detail", "pack", "category", "subcat", "code", "note", "rwf"])
    out["rwf"] = pd.to_numeric(out["rwf"], errors="coerce")
    out["usd"] = out["rwf"] / FX_RWF_PER_USD
    return out


def _parse_generic(src: Source, currency: str | None):
    """Any other file: product/description column + a price column. Returns (frame, native currency)."""
    raw = _fix_cols(src.read())
    cols = list(raw.columns)
    prod = _find(cols, "product", "description", "medicine", "item", "drug", "name")
    usd = _find(cols, "usd", "$")
    rwf = _find(cols, "rwf", "frw")
    bare = _find(cols, "price", "cost", "tariff", "amount") if not (usd or rwf) else None
    if not prod:
        raise ValueError(f"No product or description column found. Columns in the file: {cols[:10]}.")
    if not (usd or rwf or bare):
        raise ValueError(f"No price column found. Name one like 'Unit Price (USD)'. Columns: {cols[:10]}.")
    if bare and currency not in ("USD", "RWF"):
        raise NeedsCurrency(f"The price column '{bare}' does not say which currency it is in.")
    out = _blank(len(raw))
    out["product"] = raw[prod].map(_clean)
    for field, needles in (("pack", ("pack",)), ("category", ("category", "type")), ("note", ("note", "incoterm"))):
        c = _find(cols, *needles)
        if c:
            out[field] = raw[c].map(_num_text if field == "pack" else _clean)
    if usd or rwf:
        out["usd"] = pd.to_numeric(raw[usd], errors="coerce") if usd else float("nan")
        out["rwf"] = pd.to_numeric(raw[rwf], errors="coerce") if rwf else float("nan")
        return out, "USD" if usd else "RWF"
    vals = pd.to_numeric(raw[bare], errors="coerce")
    out["usd"], out["rwf"] = (vals, float("nan")) if currency == "USD" else (float("nan"), vals)
    return out, currency


class NeedsCurrency(ValueError):
    """The file has a single price column with no currency in its header."""


# ───────────────────────────────────────────────────────────── detection
# format key -> (label base, kind, native currency, order used when seeding)
PRESETS = {
    "rhia":   ("RHIA", "Insurance reimbursement tariff", "RWF", 0),
    "rms24":  ("RMS Master", "Price list", "USD", 1),
    "rms25":  ("RMS", "Price list", "USD", 2),
    "sa":     ("South Africa", "Price list", "USD", 3),
    "lk":     ("Sri Lanka", "Price list", "USD", 4),
    "unicef": ("UNICEF Africa", "Price list", "USD", 5),
}


def detect(src: Source) -> str:
    """Name of the recognised layout, or 'generic'."""
    if not src.is_csv and _rhia_header_row(src) is not None:
        return "rhia"
    try:
        cols = {c.lower() for c in _fix_cols(src.read(nrows=3)).columns}
    except Exception:
        return "generic"
    if {"active ingredients", "dosage form"} <= cols:
        return "sa"
    if "medium_description" in cols:
        return "lk"
    if "product descritpion" in cols:
        return "rms24"
    if "description" in cols and "offered pack size/unit" in cols:
        return "rms25"
    if "medicine" in cols and any(c.startswith("unit price") for c in cols):
        return "unicef"
    return "generic"


@dataclass
class Parsed:
    df: pd.DataFrame          # clean rows, both currencies filled
    fmt: str                  # detected layout
    label: str                # suggested list name
    period: str
    kind: str
    native_currency: str
    unpriced: int             # rows dropped because they have no price
    duplicates: int           # exact duplicate rows dropped


def parse(name: str, data: bytes, currency: str | None = None) -> Parsed:
    """Read a file and return clean rows plus suggested name/period. Raises ValueError with a clear message."""
    src = Source(name, data)
    fmt = detect(src)
    native = None
    try:
        if fmt == "rhia":
            df = _parse_rhia(src, _rhia_header_row(src))
        elif fmt == "rms24":
            df = _parse_rms(src, "TYPE", "Product descritpion", "Pack size", "Incoterm")
        elif fmt == "rms25":
            df = _parse_rms(src, "Category", "Description", "offered pack size/unit", None)
        elif fmt == "sa":
            df = _parse_sa(src)
        elif fmt == "lk":
            df = _parse_lk(src)
        elif fmt == "unicef":
            df = _parse_unicef(src)
        else:
            df, native = _parse_generic(src, currency)
    except NeedsCurrency:
        raise
    except pd.errors.ParserError as exc:
        raise ValueError("The file could not be read as a table. If product names contain commas, put the name "
                         f"in quotes. Details: {exc}") from exc
    except Exception as exc:
        if fmt == "generic":
            raise ValueError(str(exc)) from exc
        raise ValueError(f"The file looks like a {PRESETS[fmt][0]} list but could not be read: {exc}") from exc

    # make sure both currencies exist, at the shared rate
    df = df[df["product"].notna()].copy()
    for c in ("usd", "rwf"):
        df[c] = pd.to_numeric(df[c], errors="coerce").where(lambda s: s > 0)
    df["usd"] = df["usd"].fillna(df["rwf"] / FX_RWF_PER_USD)
    df["rwf"] = df["rwf"].fillna(df["usd"] * FX_RWF_PER_USD)
    priced = df[df["usd"].notna()].copy()
    unpriced = len(df) - len(priced)
    before = len(priced)
    for c in ("detail", "pack", "category", "subcat", "code", "note"):
        priced[c] = priced[c].fillna("")
    priced = priced.drop_duplicates(subset=["product", "pack", "usd"])
    if priced.empty:
        raise ValueError("No rows with a product name and a price were found in this file.")

    period = guess_period(name)
    if fmt in PRESETS:
        base, kind, native, _ = PRESETS[fmt]
        label = f"{base} {period}".strip()
    else:
        label, kind, native = prettify(name), "Custom list", native or "USD"
    return Parsed(priced[COLUMNS].reset_index(drop=True), fmt, label, period, kind, native,
                  int(unpriced), int(before - len(priced)))
