"""
Live USD to RWF exchange rate.

Google has no public exchange-rate service, so this reads free sources that publish the same market (mid) rate,
trying them in turn:

    1. Currency API on the jsDelivr CDN          (no key, updated daily)
    2. Currency API on Cloudflare Pages          (the same data, a second host)
    3. ExchangeRate-API open endpoint            (no key, updated daily; asks for attribution)

The result is saved in the database. If every source is unreachable, the last saved rate is used, and if there is
none, DEFAULT_RATE. The page always says which of these three it is showing, so an old rate is never passed off
as a current one.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from datetime import datetime, timezone

DEFAULT_RATE = 1300.0                  # the fixed rate this app used before it had a live one
MIN_RATE, MAX_RATE = 300.0, 10000.0    # anything outside this is a bad answer, not an exchange rate
TIMEOUT = 4.0                          # seconds per source
BUDGET = 9.0                           # seconds for all sources together


def _parse_currency_api(data: dict) -> tuple[float, str]:
    return float(data["usd"]["rwf"]), str(data.get("date", ""))


def _parse_exchangerate_api(data: dict) -> tuple[float, str]:
    if data.get("result") != "success":
        raise ValueError(f"service said: {data.get('error-type') or data.get('result')}")
    return float(data["rates"]["RWF"]), str(data.get("time_last_update_utc", ""))[:16]


SOURCES = [
    ("Currency API (jsDelivr)", "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json", _parse_currency_api),
    ("Currency API (Cloudflare)", "https://latest.currency-api.pages.dev/v1/currencies/usd.json", _parse_currency_api),
    ("ExchangeRate-API", "https://open.er-api.com/v6/latest/USD", _parse_exchangerate_api),
]


def fetch_live(sources=None, timeout: float = TIMEOUT, budget: float = BUDGET) -> dict:
    """Ask each source in turn and return the first sane answer. Raises RuntimeError listing why each one failed."""
    started, problems = time.monotonic(), []
    for name, url, parse in (sources or SOURCES):
        if time.monotonic() - started > budget:
            problems.append(f"{name}: skipped (time budget used up)")
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "rms-price-database/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rate, asof = parse(data)
            if not math.isfinite(rate) or not (MIN_RATE <= rate <= MAX_RATE):
                raise ValueError(f"implausible rate {rate!r}")
            return {"rate": round(rate, 4), "source": name, "asof": asof, "live": True}
        except Exception as exc:
            problems.append(f"{name}: {type(exc).__name__}: {str(exc)[:90]}")
    raise RuntimeError("; ".join(problems) or "no sources configured")


def resolve(store, sources=None) -> dict:
    """
    The rate to use right now. `store` needs get(key, default) and set(key, value) (the database provides both).
    Returns {rate, source, asof, live, state, note} where state is 'live', 'saved' or 'fixed'.
    """
    try:
        got = fetch_live(sources)
        try:
            store.set("fx_rate", str(got["rate"])); store.set("fx_source", got["source"]); store.set("fx_asof", got["asof"])
            store.set("fx_fetched_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        except Exception:
            pass                                        # saving is a convenience; the live rate is still good
        return {**got, "state": "live", "note": ""}
    except Exception as exc:
        note = str(exc)
    try:
        saved = float(store.get("fx_rate", "") or 0)
        if MIN_RATE <= saved <= MAX_RATE:
            return {"rate": saved, "source": store.get("fx_source", "") or "an earlier lookup", "asof": store.get("fx_asof", "") or "",
                    "live": False, "state": "saved", "note": note, "fetched_at": store.get("fx_fetched_at", "") or ""}
    except Exception:
        pass                                            # a missing or unreadable saved rate just means "none saved"
    return {"rate": DEFAULT_RATE, "source": "", "asof": "", "live": False, "state": "fixed", "note": note}


def describe(info: dict) -> str:
    """One plain sentence for tooltips and the admin panel."""
    if info["state"] == "live":
        return f"Live rate from {info['source']}" + (f", as of {info['asof']}" if info.get("asof") else "") + "."
    if info["state"] == "saved":
        when = f" (looked up {info['fetched_at'][:16].replace('T', ' ')} UTC)" if info.get("fetched_at") else ""
        return f"The live source could not be reached, so this is the last saved rate{when}."
    return f"The live source could not be reached and no earlier rate was saved, so this is the fixed rate of {DEFAULT_RATE:,.0f}."
