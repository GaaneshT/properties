#!/usr/bin/env python3
"""
pull_ura.py — bake the full URA private-residential transaction dataset into
static JSON for a buyer's decision tool.

Runs SERVER-SIDE only. The URA AccessKey is read from URA_ACCESS_KEY and never
written to any output file — the front end only reads the committed JSON.

Output (written under static/data so GitHub Pages serves it at /data/...):
  index.json            compact per-project decision metrics for ALL projects
                        (median PSF, price/area ranges, appreciation trend,
                        volume, tenure, region). This is the browse surface.
  districts/D<nn>.json   transaction-level records + per-segment summaries,
                        grouped by district, loaded on demand for charts.
  meta.json             refresh timestamp + source note.

Usage:
  URA_ACCESS_KEY=xxxx python scripts/pull_ura.py        # live pull (all projects)
  python scripts/pull_ura.py --mock                     # no key; baked sample
  python scripts/pull_ura.py --dump-raw raw.json        # also save raw merge
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import requests

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
# Empty list = bake EVERY project. Put names here to restrict to a watchlist.
WATCHLIST: list[str] = []

SQM_TO_SQFT = 10.7639

TOKEN_URL = "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
DATA_URL = "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1"
SERVICE = "PMI_Resi_Transaction"
BATCHES = (1, 2, 3, 4)

USER_AGENT = "properties.gaanesh.com data-baker (+https://properties.gaanesh.com)"

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "static" / "data"
SHARD_DIR = DATA_DIR / "districts"

# Verified against a live URA response (2026-06): 1=New Sale, 2=Sub-Sale,
# 3=Resale. NOTE: 2 and 3 are swapped vs the order one might assume.
SALE_TYPE_LABELS = {"1": "new sale", "2": "sub-sale", "3": "resale"}
SEGMENTS = {"all": {"1", "2", "3"}, "newSale": {"1"}, "subSale": {"2"}, "resale": {"3"}}


# ─────────────────────────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────────────────────────
def get_token(access_key: str, *, retries: int = 4) -> str:
    headers = {"AccessKey": access_key, "User-Agent": USER_AGENT}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(TOKEN_URL, headers=headers, timeout=30)
            r.raise_for_status()
            payload = r.json()
            token = payload.get("Result")
            if payload.get("Status") == "Success" and token:
                return token
            raise RuntimeError(f"token response not successful: {payload}")
        except Exception as e:  # noqa: BLE001 — endpoint is flaky; retry on anything
            last_err = e
            wait = 2 ** attempt
            print(f"  token attempt {attempt + 1} failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"could not obtain token after {retries} attempts: {last_err}")


def get_batch(access_key: str, token: str, batch: int, *, retries: int = 4) -> list[dict]:
    headers = {"AccessKey": access_key, "Token": token, "User-Agent": USER_AGENT}
    params = {"service": SERVICE, "batch": batch}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(DATA_URL, headers=headers, params=params, timeout=90)
            r.raise_for_status()
            payload = r.json()
            if payload.get("Status") != "Success":
                raise RuntimeError(f"batch {batch} not successful: {payload.get('Message')!r}")
            result = payload.get("Result") or []
            print(f"  batch {batch}: {len(result)} projects")
            return result
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = 2 ** attempt
            print(f"  batch {batch} attempt {attempt + 1} failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"could not fetch batch {batch} after {retries} attempts: {last_err}")


RENTAL_SERVICE = "PMI_Resi_Rental_Median"


def get_rental(access_key: str, token: str, *, retries: int = 4) -> list[dict]:
    headers = {"AccessKey": access_key, "Token": token, "User-Agent": USER_AGENT}
    params = {"service": RENTAL_SERVICE}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(DATA_URL, headers=headers, params=params, timeout=90)
            r.raise_for_status()
            payload = r.json()
            if payload.get("Status") != "Success":
                raise RuntimeError(f"rental not successful: {payload.get('Message')!r}")
            result = payload.get("Result") or []
            print(f"  rental medians: {len(result)} projects")
            return result
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = 2 ** attempt
            print(f"  rental attempt {attempt + 1} failed ({e}); retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"  WARNING: could not fetch rental data ({last_err}); continuing without yields", file=sys.stderr)
    return []


def fetch_all(access_key: str) -> tuple[list[dict], list[dict]]:
    print("Exchanging AccessKey for daily token…")
    token = get_token(access_key)
    print("Pulling 4 transaction batches…")
    merged: list[dict] = []
    for b in BATCHES:
        merged.extend(get_batch(access_key, token, b))
        time.sleep(1)
    print("Pulling rental medians…")
    rental = get_rental(access_key, token)
    return merged, rental


# ─────────────────────────────────────────────────────────────────────────────
# Transform helpers
# ─────────────────────────────────────────────────────────────────────────────
def parse_contract_date(mmyy: str) -> tuple[str, int, str, int] | None:
    """'0323' -> ('2023-03', 2023, '2023-Q1', monthIndex). None if unparseable."""
    if not mmyy or len(mmyy) != 4 or not mmyy.isdigit():
        return None
    mm = int(mmyy[:2])
    yy = int(mmyy[2:])
    if not 1 <= mm <= 12:
        return None
    year = 2000 + yy
    quarter = f"{year}-Q{(mm - 1) // 3 + 1}"
    return f"{year}-{mm:02d}", year, quarter, year * 12 + (mm - 1)


def tenure_class(tenure: str) -> str:
    t = (tenure or "").lower()
    if "freehold" in t:
        return "freehold"
    if any(k in t for k in ("yrs", "year", "lease", "999")):
        return "leasehold"
    return "unknown"


def to_float(v) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(str(v).replace(",", ""))
    except (ValueError, TypeError):
        return None


def med(xs: list[float]) -> float:
    return round(median(xs), 2)


def normalize_transaction(raw: dict) -> dict | None:
    price = to_float(raw.get("price"))
    area_sqm = to_float(raw.get("area"))
    parsed = parse_contract_date(raw.get("contractDate", ""))
    if price is None or area_sqm is None or area_sqm <= 0 or parsed is None:
        return None
    date, year, quarter, month_index = parsed
    area_sqft = area_sqm * SQM_TO_SQFT
    type_of_sale = str(raw.get("typeOfSale", "")).strip()
    tenure = raw.get("tenure", "")
    return {
        "date": date,
        "year": year,
        "quarter": quarter,
        "monthIndex": month_index,
        "psf": round(price / area_sqft, 2),
        "price": round(price),
        "areaSqft": round(area_sqft),
        "areaSqm": round(area_sqm, 1),
        "floorRange": raw.get("floorRange") or "",
        "typeOfSale": type_of_sale,
        "saleType": SALE_TYPE_LABELS.get(type_of_sale, "other"),
        "propertyType": raw.get("propertyType") or "",
        "tenure": tenure,
        "tenureClass": tenure_class(tenure),
        "noOfUnits": int(to_float(raw.get("noOfUnits")) or 1),
    }


def summarize(txns: list[dict]) -> dict:
    """Per-segment summary blocks (for the detail/compare charts)."""
    out: dict[str, dict] = {}
    for seg, codes in SEGMENTS.items():
        rows = [t for t in txns if t["typeOfSale"] in codes]
        if not rows:
            out[seg] = {"count": 0}
            continue
        psfs = [t["psf"] for t in rows]
        prices = [t["price"] for t in rows]
        by_q: dict[str, list[float]] = {}
        for t in rows:
            by_q.setdefault(t["quarter"], []).append(t["psf"])
        out[seg] = {
            "count": len(rows),
            "medianPsf": med(psfs),
            "minPsf": round(min(psfs), 2),
            "maxPsf": round(max(psfs), 2),
            "medianPrice": round(median(prices)),
            "minPrice": min(prices),
            "maxPrice": max(prices),
            "byQuarter": [
                {"quarter": q, "medianPsf": med(v), "count": len(v)}
                for q, v in sorted(by_q.items())
            ],
        }
    return out


CONDO_TYPES = {"Condominium", "Apartment"}
EC_TYPES = {"Executive Condominium"}
LANDED_TYPES = {
    "Detached", "Semi-detached", "Terrace",
    "Strata Detached", "Strata Semi-detached", "Strata Terrace",
}


def categorize(txns: list[dict]) -> str:
    """Coarse property category by majority of transactions: condo / ec / landed."""
    counts = {"condo": 0, "ec": 0, "landed": 0, "other": 0}
    for t in txns:
        pt = t["propertyType"]
        if pt in EC_TYPES:
            counts["ec"] += 1
        elif pt in CONDO_TYPES:
            counts["condo"] += 1
        elif pt in LANDED_TYPES:
            counts["landed"] += 1
        else:
            counts["other"] += 1
    return max(counts, key=lambda k: counts[k])


def yearly_series(rows: list[dict]) -> list[list]:
    """Compact [[year, medianPsf, count], ...] for a sparkline + trend."""
    by_y: dict[int, list[float]] = {}
    for t in rows:
        by_y.setdefault(t["year"], []).append(t["psf"])
    return [[y, med(v), len(v)] for y, v in sorted(by_y.items())]


# ── Advanced analytics ───────────────────────────────────────────────────────
def repeat_sales(txns: list[dict]) -> tuple[list[dict], float | None, float | None]:
    """Approximate repeat-sale matching.

    The public caveat feed has NO unit number, so we proxy "same unit" by exact
    floor-area (sqm) + floor band within a project, then pair sales chronologically.
    This is a documented approximation — in stacks with many identical-size units
    it can mismatch — so we surface the pair count for context. Returns
    (pairs, median annualised return %, median holding years).
    """
    groups: dict[tuple, list[dict]] = {}
    for t in txns:
        if not t["floorRange"]:
            continue
        groups.setdefault((t["areaSqm"], t["floorRange"]), []).append(t)

    pairs: list[dict] = []
    for rows in groups.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: r["monthIndex"])
        for a, b in zip(rows, rows[1:]):
            months = b["monthIndex"] - a["monthIndex"]
            if months < 9 or a["price"] <= 0:  # <0.75yr → skip flips / same-quarter noise
                continue
            years = months / 12
            ann = ((b["price"] / a["price"]) ** (1 / years) - 1) * 100
            pairs.append({
                "areaSqft": b["areaSqft"],
                "floorRange": b["floorRange"],
                "buyDate": a["date"],
                "sellDate": b["date"],
                "buyPrice": a["price"],
                "sellPrice": b["price"],
                "holdYears": round(years, 1),
                "annReturnPct": round(ann, 1),
                "totalReturnPct": round((b["price"] / a["price"] - 1) * 100, 1),
            })
    anns = [p["annReturnPct"] for p in pairs]
    holds = [p["holdYears"] for p in pairs]
    pairs.sort(key=lambda p: p["sellDate"], reverse=True)
    return pairs, (med(anns) if anns else None), (med(holds) if holds else None)


def by_floor(rows: list[dict], proj_med: float) -> list[dict]:
    g: dict[str, list[float]] = {}
    for t in rows:
        if t["floorRange"]:
            g.setdefault(t["floorRange"], []).append(t["psf"])
    out = [
        {
            "floorRange": f,
            "medianPsf": med(v),
            "count": len(v),
            "premiumPct": round((med(v) / proj_med - 1) * 100, 1) if proj_med else None,
        }
        for f, v in g.items()
    ]
    out.sort(key=lambda r: r["floorRange"])
    return out


SIZE_BUCKETS = [
    (0, 600, "<600"),
    (600, 900, "600–900"),
    (900, 1200, "900–1,200"),
    (1200, 1500, "1,200–1,500"),
    (1500, 10**9, "1,500+"),
]


def by_size(rows: list[dict], proj_med: float) -> list[dict]:
    out = []
    for lo, hi, label in SIZE_BUCKETS:
        v = [t["psf"] for t in rows if lo <= t["areaSqft"] < hi]
        if v:
            out.append({
                "bucket": label,
                "medianPsf": med(v),
                "count": len(v),
                "premiumPct": round((med(v) / proj_med - 1) * 100, 1) if proj_med else None,
            })
    return out


def uplift(txns: list[dict], ref_month: int) -> dict:
    """New-sale (launch vintage) PSF vs current resale PSF."""
    new_psfs = [t["psf"] for t in txns if t["typeOfSale"] == "1"]
    resale = [t for t in txns if t["typeOfSale"] == "3"]
    recent = [t for t in resale if ref_month - t["monthIndex"] < 24] or resale
    new_med = med(new_psfs) if new_psfs else None
    cur_med = med([t["psf"] for t in recent]) if recent else None
    pct = round((cur_med / new_med - 1) * 100, 1) if (new_med and cur_med) else None
    return {
        "newMedianPsf": new_med,
        "newCount": len(new_psfs),
        "currentResalePsf": cur_med,
        "upliftPct": pct,
    }


def trend_pct(yearly: list[list]) -> float | None:
    """% change in yearly-median PSF, first reliable year -> last reliable year.

    Only counts years with >= 3 transactions so a single odd sale can't define a
    trend. None if there aren't two such years.
    """
    reliable = [row for row in yearly if row[2] >= 3]
    if len(reliable) < 2:
        return None
    first, last = reliable[0][1], reliable[-1][1]
    if first <= 0:
        return None
    return round((last / first - 1) * 100, 1)


def rperiod_num(p: str) -> int:
    """'2023Q4' -> sortable int."""
    try:
        return int(p[:4]) * 4 + (int(p[5]) - 1)
    except (ValueError, IndexError):
        return 0


def build_rental(rental_raw: list[dict]) -> dict[str, dict]:
    """name(upper) -> { rentPsf (latest monthly median $/sqft), series }."""
    out: dict[str, dict] = {}
    for p in rental_raw:
        name = (p.get("project") or "").strip()
        if not name:
            continue
        pts = []
        for rm in p.get("rentalMedian") or []:
            m = to_float(rm.get("median"))
            if m is None or not rm.get("refPeriod"):
                continue
            pts.append({"refPeriod": rm["refPeriod"], "median": round(m, 2)})
        if not pts:
            continue
        pts.sort(key=lambda x: rperiod_num(x["refPeriod"]))
        out[name.upper()] = {"rentPsf": pts[-1]["median"], "series": pts}
    return out


def build(
    projects_raw: list[dict], ref_month: int, rental_map: dict[str, dict] | None = None
) -> tuple[list[dict], dict[str, list[dict]]]:
    """Returns (index_entries, shards_by_district)."""
    rental_map = rental_map or {}
    wanted = {n.upper() for n in WATCHLIST} if WATCHLIST else None
    by_name: dict[str, dict] = {}

    for proj in projects_raw:
        name = (proj.get("project") or "").strip()
        if not name or (wanted is not None and name.upper() not in wanted):
            continue
        entry = by_name.setdefault(
            name,
            {
                "project": name,
                "street": proj.get("street") or "",
                "marketSegment": proj.get("marketSegment") or "",
                "x": proj.get("x") or "",
                "y": proj.get("y") or "",
                "_raw": [],
            },
        )
        for f in ("street", "marketSegment", "x", "y"):
            if not entry[f] and proj.get(f):
                entry[f] = proj[f]
        entry["_raw"].extend(proj.get("transaction") or [])

    index: list[dict] = []
    shards: dict[str, list[dict]] = {}

    for name in sorted(by_name):
        entry = by_name[name]
        raw_txns = entry.pop("_raw")
        district = next(
            (str(t.get("district")).strip() for t in raw_txns if t.get("district")), ""
        )
        txns = [n for n in (normalize_transaction(t) for t in raw_txns) if n]
        if not txns:
            continue
        txns.sort(key=lambda t: t["date"])

        # Buyer-facing stats favour resale; fall back to all if no resale.
        resale = [t for t in txns if t["typeOfSale"] == "3"]
        basis_rows = resale if resale else txns
        basis = "resale" if resale else "all"

        psfs = [t["psf"] for t in basis_rows]
        prices = [t["price"] for t in basis_rows]
        areas = [t["areaSqft"] for t in basis_rows]
        proj_med = med(psfs)
        yearly = yearly_series(basis_rows)
        recent12 = sum(1 for t in basis_rows if ref_month - t["monthIndex"] < 12)

        # Advanced analytics.
        rs_pairs, rs_ann, rs_hold = repeat_sales(txns)
        up = uplift(txns, ref_month)
        floors = by_floor(basis_rows, proj_med)
        sizes = by_size(basis_rows, proj_med)
        months = [t["monthIndex"] for t in txns]
        span_years = max((max(months) - min(months)) / 12, 1.0)
        txns_per_year = round(len(txns) / span_years, 1)
        floor_premium = (
            round((floors[-1]["medianPsf"] / floors[0]["medianPsf"] - 1) * 100, 1)
            if len(floors) >= 2 and floors[0]["medianPsf"]
            else None
        )

        # Gross rental yield: latest monthly median rent PSF × 12 ÷ sale median PSF.
        rent = rental_map.get(name.upper())
        rent_psf = rent["rentPsf"] if rent else None
        gross_yield = (
            round(rent_psf * 12 / proj_med * 100, 2) if (rent_psf and proj_med) else None
        )
        ptypes = sorted({t["propertyType"] for t in txns if t["propertyType"]})
        tclass = max(
            {t["tenureClass"] for t in txns},
            key=lambda c: sum(1 for t in txns if t["tenureClass"] == c),
        )
        tenure_sample = next((t["tenure"] for t in txns if t["tenure"]), "")
        dkey = f"D{district}" if district else "DNA"

        # Lean index — only what the league table + KPIs + sparkline need. Heavier
        # detail (ranges, property types, breakdowns) lives in the district shards.
        index.append(
            {
                "project": name,
                "street": entry["street"],
                "district": district,
                "region": entry["marketSegment"],
                "category": categorize(txns),
                "tenureClass": tclass,
                "basis": basis,
                "nAll": len(txns),
                "recent12": recent12,
                "medianPsf": med(psfs),
                "medianPrice": round(median(prices)),
                "medianAreaSqft": round(median(areas)),
                "trendPct": trend_pct(yearly),
                "txnsPerYear": txns_per_year,
                "upliftPct": up["upliftPct"],
                "repeatPairs": len(rs_pairs),
                "repeatAnnReturn": rs_ann,
                "floorPremiumPct": floor_premium,
                "rentPsf": rent_psf,
                "grossYield": gross_yield,
                "yearly": yearly,
            }
        )

        # Trim per-transaction records to just what the client charts/table need
        # (keeps committed shards lean). saleType label + year are derived client-side.
        slim = [
            {
                "date": t["date"],
                "quarter": t["quarter"],
                "psf": t["psf"],
                "price": t["price"],
                "areaSqft": t["areaSqft"],
                "floorRange": t["floorRange"],
                "typeOfSale": t["typeOfSale"],
                "tenureClass": t["tenureClass"],
                "propertyType": t["propertyType"],
            }
            for t in txns
        ]
        shards.setdefault(dkey, []).append(
            {
                "project": name,
                "street": entry["street"],
                "district": district,
                "region": entry["marketSegment"],
                "tenureClass": tclass,
                "transactions": slim,
                "summary": summarize(txns),
                "byFloor": floors,
                "bySize": sizes,
                "uplift": up,
                "repeatStats": {
                    "pairs": len(rs_pairs),
                    "medianAnnReturnPct": rs_ann,
                    "medianHoldYears": rs_hold,
                },
                "repeatSales": rs_pairs[:80],
                "rental": {
                    "rentPsf": rent_psf,
                    "grossYield": gross_yield,
                    "series": rent["series"] if rent else [],
                },
            }
        )

    return index, shards


# ─────────────────────────────────────────────────────────────────────────────
# Mock
# ─────────────────────────────────────────────────────────────────────────────
def mock_raw() -> list[dict]:
    def txn(price, area, mmyy, sale, floor, tenure, district, ptype="Condominium"):
        return {
            "price": str(price), "area": str(area), "contractDate": mmyy,
            "typeOfSale": sale, "floorRange": floor, "tenure": tenure,
            "propertyType": ptype, "noOfUnits": "1", "district": district,
            "typeOfArea": "Strata",
        }

    return [
        {
            "project": "CARISSA PARK CONDOMINIUM", "street": "FLORA DRIVE",
            "marketSegment": "OCR", "x": "42588.73", "y": "37930.07",
            "transaction": [
                txn(880000, 110.0, "0122", "3", "01-05", "Freehold", "17"),
                txn(910000, 112.0, "0622", "3", "06-10", "Freehold", "17"),
                txn(905000, 108.0, "1122", "2", "01-05", "Freehold", "17"),
                txn(960000, 111.0, "0323", "3", "11-15", "Freehold", "17"),
                txn(1010000, 115.0, "0923", "3", "06-10", "Freehold", "17"),
                txn(1050000, 110.0, "0224", "3", "01-05", "Freehold", "17"),
                txn(1120000, 118.0, "0824", "3", "11-15", "Freehold", "17"),
                txn(1180000, 116.0, "0125", "3", "06-10", "Freehold", "17"),
            ],
        },
        {
            "project": "REFLECTIONS AT KEPPEL BAY", "street": "KEPPEL BAY VIEW",
            "marketSegment": "RCR", "x": "27000.0", "y": "28000.0",
            "transaction": [
                txn(2100000, 150.0, "0122", "3", "11-15", "99 yrs lease commencing from 2007", "04"),
                txn(2250000, 155.0, "0522", "3", "21-25", "99 yrs lease commencing from 2007", "04"),
                txn(2180000, 148.0, "1022", "3", "06-10", "99 yrs lease commencing from 2007", "04"),
                txn(2400000, 160.0, "0223", "1", "26-30", "99 yrs lease commencing from 2007", "04"),
                txn(2350000, 152.0, "0823", "3", "16-20", "99 yrs lease commencing from 2007", "04"),
                txn(2520000, 158.0, "0124", "3", "21-25", "99 yrs lease commencing from 2007", "04"),
                txn(2600000, 162.0, "0724", "2", "26-30", "99 yrs lease commencing from 2007", "04"),
                txn(2720000, 159.0, "1224", "3", "16-20", "99 yrs lease commencing from 2007", "04"),
                txn(2800000, 165.0, "0425", "3", "31-35", "99 yrs lease commencing from 2007", "04"),
            ],
        },
    ]


def mock_rental() -> list[dict]:
    def rm(period, median, d):
        return {"refPeriod": period, "median": median, "psf25": median - 0.3, "psf75": median + 0.4, "district": d}

    return [
        {
            "project": "CARISSA PARK CONDOMINIUM", "street": "FLORA DRIVE", "x": "1", "y": "1",
            "rentalMedian": [rm("2024Q3", 3.2, "17"), rm("2024Q4", 3.3, "17"), rm("2025Q1", 3.4, "17")],
        },
        {
            "project": "REFLECTIONS AT KEPPEL BAY", "street": "KEPPEL BAY VIEW", "x": "1", "y": "1",
            "rentalMedian": [rm("2024Q3", 4.6, "04"), rm("2024Q4", 4.8, "04"), rm("2025Q1", 5.0, "04")],
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def max_month(projects_raw: list[dict]) -> int:
    best = 0
    for p in projects_raw:
        for t in p.get("transaction") or []:
            parsed = parse_contract_date(t.get("contractDate", ""))
            if parsed and parsed[3] > best:
                best = parsed[3]
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description="Bake URA transaction data to static JSON.")
    ap.add_argument("--mock", action="store_true", help="use baked sample data; no key needed")
    ap.add_argument("--dump-raw", metavar="FILE", help="also write the raw merged response here")
    args = ap.parse_args()

    if args.mock:
        print("MOCK mode — using baked sample response (no API call).")
        raw = mock_raw()
        rental_raw = mock_rental()
        source = "mock sample (not real URA data)"
    else:
        access_key = os.environ.get("URA_ACCESS_KEY")
        if not access_key:
            print("ERROR: URA_ACCESS_KEY is not set. Set it, or run with --mock.", file=sys.stderr)
            return 2
        raw, rental_raw = fetch_all(access_key)
        source = "URA Data Service · PMI_Resi_Transaction + PMI_Resi_Rental_Median (60-month window)"

    if args.dump_raw:
        Path(args.dump_raw).write_text(json.dumps(raw), encoding="utf-8")
        print(f"Wrote raw merge to {args.dump_raw}")

    ref_month = max_month(raw) or 0
    rental_map = build_rental(rental_raw)
    scope = "all projects" if not WATCHLIST else f"{len(WATCHLIST)} watchlist projects"
    print(f"Building derived data ({scope}); {len(rental_map)} projects with rental medians…")
    index, shards = build(raw, ref_month, rental_map)

    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    # Clear stale shards so removed districts don't linger.
    for old in SHARD_DIR.glob("*.json"):
        old.unlink()

    # index sorted by transaction volume (most-traded first) for a sensible default.
    index.sort(key=lambda e: e["nAll"], reverse=True)
    (DATA_DIR / "index.json").write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")

    total_txns = 0
    for dkey, projs in shards.items():
        total_txns += sum(len(p["transactions"]) for p in projs)
        (SHARD_DIR / f"{dkey}.json").write_text(
            json.dumps(projs, separators=(",", ":")), encoding="utf-8"
        )

    now = datetime.now(timezone.utc)
    meta = {
        "refreshedAt": now.isoformat(),
        "source": source,
        "service": SERVICE,
        "projectCount": len(index),
        "transactionCount": total_txns,
        "districtCount": len(shards),
        "rentalProjectCount": len(rental_map),
        "note": (
            "Derived view (computed PSF, medians, trends, distributions, approximate "
            "repeat-sale returns) over URA caveat data. Caveat data covers ~80–90% of "
            "resale/sub-sale volume on a 60-month rolling window. Repeat-sale matching "
            "is approximate: the feed has no unit number, so 'same unit' is proxied by "
            "identical floor area + floor band within a project. Not affiliated with or "
            "endorsed by URA."
        ),
        "mock": bool(args.mock),
    }
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(
        f"Done. {len(index)} projects, {total_txns} transactions across "
        f"{len(shards)} district shards{' [MOCK]' if args.mock else ''}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
