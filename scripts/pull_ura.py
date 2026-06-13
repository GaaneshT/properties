#!/usr/bin/env python3
"""
pull_ura.py — bake URA private-residential transaction data into static JSON.

Runs SERVER-SIDE only (GitHub Actions runner or your machine). The URA
AccessKey is read from the URA_ACCESS_KEY environment variable and never
written to any output file — the front end only ever reads the committed
data/*.json this script produces.

Flow:
  1. Exchange the permanent AccessKey for a per-day Token.
  2. Pull all 4 transaction batches (they don't map to regions — merge them).
  3. Filter to WATCHLIST, compute PSF + parsed dates, drop fields the charts
     don't need, and emit *derived* data/transactions.json + data/meta.json.

Usage:
  URA_ACCESS_KEY=xxxx python scripts/pull_ura.py        # live pull
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
# Config — edit this watchlist to add/remove projects. Names must match URA's
# `project` field exactly (upper-case, as returned by the API).
# ─────────────────────────────────────────────────────────────────────────────
WATCHLIST: list[str] = [
    "CARISSA PARK CONDOMINIUM",
    "REFLECTIONS AT KEPPEL BAY",
]

SQM_TO_SQFT = 10.7639

TOKEN_URL = "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
DATA_URL = "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1"
SERVICE = "PMI_Resi_Transaction"
BATCHES = (1, 2, 3, 4)

# URA's gateway 403s requests without a browser-ish User-Agent.
USER_AGENT = "properties.gaanesh.com data-baker (+https://properties.gaanesh.com)"

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# URA's PMI_Resi_Transaction typeOfSale codes (verified against a live response,
# 2026-06): 1 = New Sale, 2 = Sub Sale, 3 = Resale. NOTE: this is *not* the
# 1/2/3 = new/resale/subsale order one might assume — 2 and 3 are swapped.
# Confirmed empirically: two established resale projects returned 100% code "3".
SALE_TYPE_LABELS = {"1": "new sale", "2": "sub-sale", "3": "resale"}

# Map our normalized buckets to the typeOfSale codes they contain.
SEGMENTS = {
    "all": {"1", "2", "3"},
    "newSale": {"1"},
    "subSale": {"2"},
    "resale": {"3"},
}


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
            r = requests.get(DATA_URL, headers=headers, params=params, timeout=60)
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


def fetch_all(access_key: str) -> list[dict]:
    print("Exchanging AccessKey for daily token…")
    token = get_token(access_key)
    print("Pulling 4 transaction batches…")
    merged: list[dict] = []
    for b in BATCHES:
        merged.extend(get_batch(access_key, token, b))
        time.sleep(1)  # be polite to a flaky gateway
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Transform
# ─────────────────────────────────────────────────────────────────────────────
def parse_contract_date(mmyy: str) -> tuple[str, int, str] | None:
    """'0323' -> ('2023-03', 2023, '2023-Q1'). Returns None if unparseable."""
    if not mmyy or len(mmyy) != 4 or not mmyy.isdigit():
        return None
    mm = int(mmyy[:2])
    yy = int(mmyy[2:])
    if not 1 <= mm <= 12:
        return None
    year = 2000 + yy
    quarter = f"{year}-Q{(mm - 1) // 3 + 1}"
    return f"{year}-{mm:02d}", year, quarter


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


def normalize_transaction(raw: dict) -> dict | None:
    price = to_float(raw.get("price"))
    area_sqm = to_float(raw.get("area"))
    parsed = parse_contract_date(raw.get("contractDate", ""))
    if price is None or area_sqm is None or area_sqm <= 0 or parsed is None:
        return None

    date, year, quarter = parsed
    area_sqft = area_sqm * SQM_TO_SQFT
    psf = price / area_sqft
    type_of_sale = str(raw.get("typeOfSale", "")).strip()
    tenure = raw.get("tenure", "")

    return {
        "date": date,
        "year": year,
        "quarter": quarter,
        "psf": round(psf, 2),
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
    """Pre-computed summary blocks segmented by typeOfSale."""
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
        by_quarter = [
            {"quarter": q, "medianPsf": round(median(v), 2), "count": len(v)}
            for q, v in sorted(by_q.items())
        ]

        out[seg] = {
            "count": len(rows),
            "medianPsf": round(median(psfs), 2),
            "minPsf": round(min(psfs), 2),
            "maxPsf": round(max(psfs), 2),
            "minPrice": min(prices),
            "maxPrice": max(prices),
            "byQuarter": by_quarter,
        }
    return out


def build(projects_raw: list[dict]) -> dict:
    wanted = {name.upper() for name in WATCHLIST}
    # A project can appear once per batch — merge transactions by project name.
    by_name: dict[str, dict] = {}

    for proj in projects_raw:
        name = (proj.get("project") or "").strip()
        if name.upper() not in wanted:
            continue
        entry = by_name.setdefault(
            name,
            {
                "project": name,
                "street": proj.get("street") or "",
                "marketSegment": proj.get("marketSegment") or "",
                "district": "",
                "x": proj.get("x") or "",
                "y": proj.get("y") or "",
                "_raw_txns": [],
            },
        )
        # Fill descriptive fields if a later batch has them and we don't.
        for f in ("street", "marketSegment", "x", "y"):
            if not entry[f] and proj.get(f):
                entry[f] = proj[f]
        entry["_raw_txns"].extend(proj.get("transaction") or [])

    out_projects = []
    for name in sorted(by_name):
        entry = by_name[name]
        raw_txns = entry.pop("_raw_txns")
        # `district` lives on transaction records, not the project — lift the
        # first non-empty one we see.
        if not entry["district"]:
            entry["district"] = next(
                (str(t.get("district")).strip() for t in raw_txns if t.get("district")), ""
            )
        txns = [n for n in (normalize_transaction(t) for t in raw_txns) if n]
        txns.sort(key=lambda t: t["date"])
        entry["transactions"] = txns
        entry["summary"] = summarize(txns)
        out_projects.append(entry)
        print(f"  {name}: {len(txns)} usable transactions")

    found = {p["project"].upper() for p in out_projects}
    for name in WATCHLIST:
        if name.upper() not in found:
            print(f"  WARNING: watchlist project not found in URA data: {name!r}", file=sys.stderr)

    return {"projects": out_projects}


# ─────────────────────────────────────────────────────────────────────────────
# Mock data — proves the pipeline + charts without a key.
# ─────────────────────────────────────────────────────────────────────────────
def mock_raw() -> list[dict]:
    def txn(price, area, mmyy, sale, floor, tenure, ptype="Condominium"):
        return {
            "price": str(price),
            "area": str(area),
            "contractDate": mmyy,
            "typeOfSale": sale,
            "floorRange": floor,
            "tenure": tenure,
            "propertyType": ptype,
            "noOfUnits": "1",
            "district": "04",
            "typeOfArea": "Strata",
        }

    # Sale codes here use the verified URA mapping: 2 = sub-sale, 3 = resale.
    return [
        {
            "project": "CARISSA PARK CONDOMINIUM",
            "street": "FLORA DRIVE",
            "marketSegment": "OCR",
            "x": "42588.73299",
            "y": "37930.06537",
            "transaction": [
                txn(880000, 110.0, "0122", "3", "01-05", "Freehold"),
                txn(910000, 112.0, "0622", "3", "06-10", "Freehold"),
                txn(905000, 108.0, "1122", "2", "01-05", "Freehold"),
                txn(960000, 111.0, "0323", "3", "11-15", "Freehold"),
                txn(1010000, 115.0, "0923", "3", "06-10", "Freehold"),
                txn(1050000, 110.0, "0224", "3", "01-05", "Freehold"),
                txn(1120000, 118.0, "0824", "3", "11-15", "Freehold"),
                txn(1180000, 116.0, "0125", "3", "06-10", "Freehold"),
            ],
        },
        {
            "project": "REFLECTIONS AT KEPPEL BAY",
            "street": "KEPPEL BAY VIEW",
            "marketSegment": "RCR",
            "x": "27000.0",
            "y": "28000.0",
            "transaction": [
                txn(2100000, 150.0, "0122", "3", "11-15", "99 yrs lease commencing from 2007"),
                txn(2250000, 155.0, "0522", "3", "21-25", "99 yrs lease commencing from 2007"),
                txn(2180000, 148.0, "1022", "3", "06-10", "99 yrs lease commencing from 2007"),
                txn(2400000, 160.0, "0223", "1", "26-30", "99 yrs lease commencing from 2007"),
                txn(2350000, 152.0, "0823", "3", "16-20", "99 yrs lease commencing from 2007"),
                txn(2520000, 158.0, "0124", "3", "21-25", "99 yrs lease commencing from 2007"),
                txn(2600000, 162.0, "0724", "2", "26-30", "99 yrs lease commencing from 2007"),
                txn(2720000, 159.0, "1224", "3", "16-20", "99 yrs lease commencing from 2007"),
                txn(2800000, 165.0, "0425", "3", "31-35", "99 yrs lease commencing from 2007"),
            ],
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Bake URA transaction data to static JSON.")
    ap.add_argument("--mock", action="store_true", help="use baked sample data; no key needed")
    ap.add_argument("--dump-raw", metavar="FILE", help="also write the raw merged response here")
    args = ap.parse_args()

    if args.mock:
        print("MOCK mode — using baked sample response (no API call).")
        raw = mock_raw()
        source = "mock sample (not real URA data)"
    else:
        access_key = os.environ.get("URA_ACCESS_KEY")
        if not access_key:
            print(
                "ERROR: URA_ACCESS_KEY is not set. Set it, or run with --mock.",
                file=sys.stderr,
            )
            return 2
        raw = fetch_all(access_key)
        source = "URA Data Service · PMI_Resi_Transaction (60-month rolling window)"

    if args.dump_raw:
        Path(args.dump_raw).write_text(json.dumps(raw, indent=2), encoding="utf-8")
        print(f"Wrote raw merge to {args.dump_raw}")

    print("Filtering to watchlist and computing derived metrics…")
    data = build(raw)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    (DATA_DIR / "transactions.json").write_text(
        json.dumps(data, separators=(",", ":")), encoding="utf-8"
    )

    total = sum(len(p["transactions"]) for p in data["projects"])
    meta = {
        "refreshedAt": now.isoformat(),
        "source": source,
        "service": SERVICE,
        "watchlist": WATCHLIST,
        "projectCount": len(data["projects"]),
        "transactionCount": total,
        "note": (
            "Derived view (computed PSF, medians, distributions) over URA caveat "
            "data. Caveat data covers ~80–90% of resale/sub-sale volume on a "
            "60-month rolling window. Not affiliated with or endorsed by URA."
        ),
        "mock": bool(args.mock),
    }
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(
        f"Done. {len(data['projects'])} projects, {total} transactions -> "
        f"data/transactions.json (+ meta.json){' [MOCK]' if args.mock else ''}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
