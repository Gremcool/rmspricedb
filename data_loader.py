"""
Data layer for the RMS Price Database.

Every price list is normalised into ONE table with the same columns, so search,
compare and charts work identically across sources.

Currency
--------
The five existing lists already carry both `Unit Price (USD)` and
`Unit Price (RWF)`, converted at a flat 1 USD = 1,300 RWF. The RHIA tariff is
published in RWF only, so its USD value is derived at that same rate. All six
sources therefore sit on one basis. Change `FX_RWF_PER_USD` if the rate changes.
"""
from __future__ import annotations

import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

FX_RWF_PER_USD = 1300.0

GITHUB_RAW_BASE_URL = "https://raw.githubusercontent.com/Gremcool/gremcool/main/excel_files"


@dataclass(frozen=True)
class SourceSpec:
    key: str
    label: str          # short name shown on badges
    file: str           # excel file name
    period: str         # shown on the dataset card
    kind: str           # what kind of price this is
    native_currency: str
    color: str          # one fixed colour per source, used everywhere
    origin: str         # "local" -> data/ folder, "github" -> GitHub raw (local fallback)


SOURCES: list[SourceSpec] = [
    SourceSpec("rhia", "RHIA Jun 2026", "RHIA_REIMBURSABLE_MEDICINES_LIST_JUNE-2026-1.xlsx",
               "June 2026", "Insurance reimbursement tariff", "RWF", "#FFC83D", "local"),
    SourceSpec("rms24", "RMS Master 2024", "FINAL MASTER LIST RMS JULY 2024.xlsx",
               "July 2024", "Price list", "USD", "#4DA3FF", "github"),
    SourceSpec("rms25", "RMS 2025", "RMS Price list 2025.xlsx",
               "2025", "Price list", "USD", "#9B8CFF", "github"),
    SourceSpec("sa22", "South Africa 2022", "SA Price List 2022.xlsx",
               "2022", "Price list", "USD", "#FF8A65", "github"),
    SourceSpec("lk24", "Sri Lanka 2024", "Sri Lanka Price List 2024.xlsx",
               "2024", "Price list", "USD", "#F472B6", "github"),
    SourceSpec("unicef", "UNICEF Africa", "Unicef African Price List.xlsx",
               "Latest supplied", "Price list", "USD", "#22D3EE", "github"),
]
SOURCE_BY_KEY = {s.key: s for s in SOURCES}
SOURCE_BY_LABEL = {s.label: s for s in SOURCES}

COLUMNS = ["uid", "source_key", "source", "product", "detail", "pack", "category", "subcat",
           "code", "note", "usd", "rwf", "search", "name_norm"]


# --------------------------------------------------------------------------- helpers
def _clean(v) -> str | None:
    """Collapse whitespace (incl. non-breaking spaces / newlines); None if empty."""
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


def norm(text: str) -> str:
    """Lower-case, accent-free, '500mg' -> '500 mg', '0,25' -> '0.25'."""
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"(?<=\d),(?=\d)", ".", s)
    s = re.sub(r"(?<=\d)(?=[a-z])", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------- readers
def _read_excel(spec: SourceSpec, **kw) -> tuple[pd.DataFrame, str]:
    """Return (raw frame, where it came from). GitHub first for 'github' sources, local fallback."""
    local = DATA_DIR / spec.file
    if spec.origin == "github":
        try:
            r = requests.get(f"{GITHUB_RAW_BASE_URL}/{requests.utils.quote(spec.file)}", timeout=45)
            r.raise_for_status()
            from io import BytesIO
            return pd.read_excel(BytesIO(r.content), **kw), "GitHub"
        except Exception:
            if not local.exists():
                raise
    return pd.read_excel(local, **kw), "data/ folder"


def _blank(n: int = 0) -> pd.DataFrame:
    return pd.DataFrame(columns=["product", "detail", "pack", "category", "subcat", "code",
                                 "note", "usd", "rwf"], index=range(n))


def _parse_rms(spec: SourceSpec, cat_col: str, name_col: str, pack_col: str, note_col: str | None):
    raw, origin = _read_excel(spec)
    raw = _fix_cols(raw)
    cat_col = next(c for c in raw.columns if c.upper().startswith(cat_col.upper()))
    out = _blank(len(raw))
    out["product"] = raw[name_col].map(_clean)
    out["pack"] = raw[pack_col].map(_num_text)
    out["category"] = raw[cat_col].map(_clean)
    if note_col:
        out["note"] = raw[note_col].map(_clean)
    out["usd"] = pd.to_numeric(raw["Unit Price (USD)"], errors="coerce")
    out["rwf"] = pd.to_numeric(raw["Unit Price (RWF)"], errors="coerce")
    return out, origin


def _parse_sa(spec: SourceSpec):
    raw, origin = _read_excel(spec)
    raw = _fix_cols(raw).reset_index(drop=True)
    # A row with a dosage form starts a product; rows without one are extra ingredients
    # of the combination product above (e.g. Lidocaine + Adrenaline).
    group = raw["Dosage Form"].notna().cumsum()

    def component(r) -> str:
        parts = [_clean(r["Active Ingredients"]), _num_text(r["Strength"]), _clean(r["Unit"])]
        return " ".join(p for p in parts if p)

    raw["_comp"] = raw.apply(component, axis=1)
    g = raw.groupby(group, sort=True).agg(
        product=("_comp", lambda s: " + ".join(x for x in s if x)),
        detail=("Dosage Form", "first"),
        pack=("Pack Size", "first"),
        usd=("Unit Price (USD)", "first"),
        rwf=("Unit Price (RWF)", "first"),
    ).reset_index(drop=True)
    out = _blank(len(g))
    out["product"] = g["product"].map(_clean)
    out["detail"] = g["detail"].map(_clean)
    out["pack"] = g["pack"].map(_num_text)
    out["usd"] = pd.to_numeric(g["usd"], errors="coerce")
    out["rwf"] = pd.to_numeric(g["rwf"], errors="coerce")
    return out, origin


def _parse_lk(spec: SourceSpec):
    raw, origin = _read_excel(spec)
    raw = _fix_cols(raw)
    out = _blank(len(raw))
    medium = raw["medium_description"].map(_clean)
    out["product"] = medium.fillna(raw["short_description"].map(_clean))
    out["usd"] = pd.to_numeric(raw["Unit Price (USD)"], errors="coerce")
    out["rwf"] = pd.to_numeric(raw["Unit Price (RWF)"], errors="coerce")
    return out, origin


def _parse_unicef(spec: SourceSpec):
    raw, origin = _read_excel(spec)
    raw = _fix_cols(raw)
    out = _blank(len(raw))
    out["product"] = raw["Medicine"].map(_clean)
    out["usd"] = pd.to_numeric(raw["Unit Price (USD)"], errors="coerce")
    out["rwf"] = pd.to_numeric(raw["Unit Price (RWF)"], errors="coerce")
    return out, origin


_TOP_LEVEL = re.compile(r"^([A-Z])\s*\.\s*(\S.*)$")


def _parse_rhia(spec: SourceSpec):
    """
    RHIA tariff sheet: banner rows, then section-header rows (no code, no price) mixed in
    with priced rows. Level-1 headers ('A. ALIMENTARY TRACT...') become the category,
    level-2 headers ('A02 DRUGS FOR ACID RELATED DISORDERS') become the sub-category.
    """
    raw, origin = _read_excel(spec, sheet_name=0, header=None, skiprows=10)
    raw = raw.iloc[:, :7]
    raw.columns = ["sn", "code", "generic", "designation", "instr", "unit", "price"]

    cat = subcat = None
    rows = []
    for r in raw.itertuples(index=False):
        sn = _clean(r.sn)
        is_header = pd.isna(r.code) and pd.isna(r.designation) and pd.isna(r.price)
        if is_header:
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

    out = pd.DataFrame(rows, columns=["product", "detail", "pack", "category", "subcat",
                                      "code", "note", "rwf"])
    out["rwf"] = pd.to_numeric(out["rwf"], errors="coerce")
    out["usd"] = out["rwf"] / FX_RWF_PER_USD            # RHIA is RWF-native: derive USD
    return out, origin


def rhia_legend() -> list[tuple[str, str]]:
    """Prescriber-instruction codes (e.g. 'DT') and their meaning, from the RHIA workbook."""
    path = DATA_DIR / SOURCE_BY_KEY["rhia"].file
    if not path.exists():
        return []
    raw = pd.read_excel(path, sheet_name=1, header=None)
    out = []
    for v in raw.iloc[:, 1].dropna():
        text = _clean(v) or ""
        if ":" in text:
            code, meaning = text.split(":", 1)
            out.append((code.strip(), _sentence(meaning)))
    return out


_PARSERS = {
    "rhia": _parse_rhia,
    "rms24": lambda s: _parse_rms(s, "TYPE", "Product descritpion", "Pack size", "Incoterm"),
    "rms25": lambda s: _parse_rms(s, "Category", "Description", "offered pack size/unit", None),
    "sa22": _parse_sa,
    "lk24": _parse_lk,
    "unicef": _parse_unicef,
}


# --------------------------------------------------------------------------- build
def _load_one(spec: SourceSpec):
    try:
        df, origin = _PARSERS[spec.key](spec)
        return spec, df, origin, None
    except Exception as exc:                                    # keep the app alive
        return spec, None, None, f"{type(exc).__name__}: {exc}"


def build_database() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (all prices, per-source load report)."""
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(_load_one, SOURCES))

    frames, report = [], []
    for spec, df, origin, err in results:
        if df is None:
            report.append(dict(key=spec.key, rows_in_file=0, priced=0, duplicates=0,
                               unpriced=0, origin="-", error=err))
            continue
        n_file = len(df)
        df = df[df["product"].notna()].copy()

        # fill whichever currency is missing, at the shared rate
        df["usd"] = df["usd"].where(df["usd"] > 0)
        df["rwf"] = df["rwf"].where(df["rwf"] > 0)
        df["usd"] = df["usd"].fillna(df["rwf"] / FX_RWF_PER_USD)
        df["rwf"] = df["rwf"].fillna(df["usd"] * FX_RWF_PER_USD)

        priced = df[df["usd"].notna()].copy()
        n_unpriced = len(df) - len(priced)
        before = len(priced)
        priced = priced.drop_duplicates(subset=["product", "pack", "usd"])
        n_dup = before - len(priced)

        priced["source_key"] = spec.key
        priced["source"] = spec.label
        frames.append(priced)
        report.append(dict(key=spec.key, rows_in_file=n_file, priced=len(priced),
                           duplicates=n_dup, unpriced=n_unpriced, origin=origin, error=None))

    db = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    db["uid"] = db.index
    for c in ("detail", "pack", "category", "subcat", "code", "note"):
        db[c] = db[c].fillna("")
    db["name_norm"] = db["product"].map(norm)
    db["search"] = (db["product"] + " " + db["detail"] + " " + db["subcat"] + " "
                    + db["category"] + " " + db["code"]).map(norm)
    db = db.set_index("uid", drop=False)
    db.index.name = None
    return db[COLUMNS], pd.DataFrame(report)


# --------------------------------------------------------------------------- search
_TOKEN = re.compile(r"[a-z0-9]+(?:\.\d+)?")


def search(db: pd.DataFrame, query: str) -> tuple[pd.DataFrame, str]:
    """
    Every word must match. First pass matches at the start of words ('amox' -> 'amoxicillin',
    but 'b' will not match the middle of 'tablet'); if that finds nothing, a second pass
    matches anywhere ('cillin' -> 'amoxicillin'). Returns (rows with a 'score' column, mode).
    """
    tokens = _TOKEN.findall(norm(query))
    if not tokens:
        return db.assign(score=0), "all"

    for mode, prefix in (("word", r"(?<![a-z0-9])"), ("substring", "")):
        mask = pd.Series(True, index=db.index)
        score = pd.Series(0, index=db.index)
        for t in tokens:
            pat = prefix + re.escape(t)
            in_any = db["search"].str.contains(pat, regex=True)
            mask &= in_any
            score += db["name_norm"].str.contains(pat, regex=True).astype(int) * 2 + in_any.astype(int)
        if mask.any():
            hit = db[mask].copy()
            hit["score"] = score[mask] + hit["name_norm"].str.startswith(tokens[0]).astype(int) * 3
            return hit, mode
    return db.iloc[0:0].assign(score=0), "none"


def suggest(db: pd.DataFrame, query: str, limit: int = 6) -> list[str]:
    """'Did you mean' for typos. Needs rapidfuzz; silently returns [] without it."""
    try:
        from rapidfuzz import fuzz, process
    except ImportError:
        return []
    names = db["name_norm"].str.split(" ", n=1).str[0].drop_duplicates().tolist()
    q = norm(query).split(" ")[0]
    found = process.extract(q, names, scorer=fuzz.WRatio, limit=limit * 3, score_cutoff=78)
    out: list[str] = []
    for name, _score, _i in found:
        if len(name) > 3 and name not in out:
            out.append(name)
    return out[:limit]


# --------------------------------------------------------------------------- formatting
def fmt_usd(v) -> str:
    if v is None or pd.isna(v):
        return ""
    if v >= 1:
        return f"${v:,.2f}"
    if v >= 0.1:
        return f"${v:.3f}"
    return f"${v:.4f}" if v >= 0.0001 else "<$0.0001"


def fmt_rwf(v) -> str:
    if v is None or pd.isna(v):
        return ""
    return f"RWF {v:,.0f}" if v >= 100 else (f"RWF {v:,.1f}" if v >= 10 else f"RWF {v:,.2f}")


def fmt_price(v, currency: str) -> str:
    return fmt_usd(v) if currency == "USD" else fmt_rwf(v)
