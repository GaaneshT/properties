# properties.gaanesh.com

A static, **read-only** viewer over Singapore URA private residential transaction
data. Personal tool for observing resale prices and comparing projects — median
PSF trends and price distributions for a small watchlist. **Not** an
estate-agent site: no listings, no enquiries, no lead capture. Just data and
charts.

Built with SvelteKit + `adapter-static` + Tailwind v4 (matching the sibling
`tools.gaanesh.com` repo), deployed to GitHub Pages.

## How it works (and why the API key is safe)

```
        ┌─ GitHub Actions runner (monthly cron) ─────────────┐
        │  URA_ACCESS_KEY (Actions Secret, server-side only)  │
        │      │                                              │
        │      ▼   scripts/pull_ura.py                        │
        │  URA Data Service ──► derive PSF/medians/dists ──►  │  commits
        └──────────────────────────────────────── data/*.json ──┐
                                                                  ▼
   Browser ◄── static site (GitHub Pages) ◄── build imports data/*.json
   (never sees the key, never calls URA)
```

- **The AccessKey never reaches the browser.** It lives only as a GitHub Actions
  Secret and is read server-side via `os.environ["URA_ACCESS_KEY"]`. It is never
  committed, never bundled, never in client JS. (Calling URA from the browser
  would also fail CORS.)
- **Data is pre-baked.** A scheduled Action runs the key on the runner, computes
  _derived_ views, and commits `data/transactions.json` + `data/meta.json`. The
  front end imports those committed files at build time — so the public data is
  freely viewable, but the key that produced it is not shareable.
- **Redistribution-conscious.** The site shows derived metrics (computed PSF,
  medians, quarterly trends, distributions) for a short watchlist, not a wholesale
  dump of the caveat table.

## Local development

```sh
npm install            # uses engine-strict; needs Node ^20.19 || ^22.13 || >=24
npm run dev            # http://localhost:5173
npm run build          # static output in build/
npm run check          # svelte-check (types)
```

### Refreshing the data locally

```sh
# Live pull (needs your key; it is NOT stored anywhere):
URA_ACCESS_KEY=xxxxxxxx python scripts/pull_ura.py

# No key handy? Prove the pipeline with baked sample data:
python scripts/pull_ura.py --mock

# Inspect the raw URA response without committing it:
URA_ACCESS_KEY=xxxxxxxx python scripts/pull_ura.py --dump-raw raw.json
```

`pip install requests` is the only dependency.

### Adding projects to the watchlist

Edit the `WATCHLIST` list at the top of `scripts/pull_ura.py`. Names must match
URA's `project` field **exactly** (upper-case). Re-run the script (or the
Action) to re-bake. The front end picks up whatever projects are in the JSON.

```python
WATCHLIST = [
    "CARISSA PARK CONDOMINIUM",
    "REFLECTIONS AT KEPPEL BAY",
    # "THE SAIL @ MARINA BAY",
]
```

## Automation

- `.github/workflows/refresh-ura.yml` — monthly cron (`0 2 16 * *`, a day after
  URA's ~15th update) plus manual `workflow_dispatch`. Exchanges a fresh daily
  token, pulls all 4 batches with retry/backoff, re-bakes the JSON, commits if
  changed, then dispatches the deploy.
- `.github/workflows/deploy.yml` — builds and deploys to GitHub Pages on push to
  `main` (and on dispatch from the refresh workflow).

> A commit pushed by the default `GITHUB_TOKEN` does not trigger another
> workflow's `push` event, so the refresh workflow explicitly calls
> `gh workflow run deploy.yml` to rebuild after a data change.

## ⚠️ Manual steps (one-time — these can't be automated)

1. **Register for a URA Data Service AccessKey** at
   <https://eservice.ura.gov.sg/maps/api/reg.html>. You'll be asked to accept the
   **Singapore Open Data Licence v1.0** and the **API Terms of Service** — read
   them, and confirm the derived-display use here is fine (it is designed to be).
   The key arrives by email.
2. **Add the key as a GitHub Actions Secret** named **`URA_ACCESS_KEY`** under
   _repo → Settings → Secrets and variables → Actions → New repository secret_.
3. **Enable GitHub Pages**: _Settings → Pages → Build and deployment → Source =
   GitHub Actions_. Then add the DNS record for `properties.gaanesh.com` at your
   registrar (a `CNAME` to `GaaneshT.github.io`), the same way the other
   subdomains are set up. The repo's `static/CNAME` already pins the domain.

## URA response schema notes (verified against a live pull, 2026-06)

Verified field names on each transaction record:
`area` (sqm, string), `contractDate` (MMYY string), `district`, `floorRange`,
`noOfUnits`, `price` (string), `propertyType`, `tenure`, `typeOfArea`,
`typeOfSale`. Project-level: `project`, `street`, `marketSegment`, `x`, `y`.

Two things worth flagging:

- **`typeOfSale` codes are `1`=New Sale, `2`=Sub-Sale, `3`=Resale.** This is the
  opposite of the intuitive "2=resale, 3=sub-sale" order — `2` and `3` are
  swapped. Confirmed empirically: two established resale projects returned 100%
  code `3`. The parser and UI use the verified mapping.
- **`nettPrice` is not present** in `PMI_Resi_Transaction`; the parser never
  relied on it. `price` is used for PSF.

Derived per record: `psf = price / (area_sqm * 10.7639)`, `contractDate` parsed
to `YYYY-MM` + quarter, `tenureClass` (freehold/leasehold) inferred from
`tenure`.

## Licence & attribution

Data: URA, via the URA Data Service, under the
[Singapore Open Data Licence v1.0](https://data.gov.sg/open-data-licence). This
is a personal project, **not affiliated with or endorsed by URA**, provided
"as is" with no warranty. Caveat data covers ~80–90% of resale/sub-sale volume
on a 60-month rolling window. The site is `noindex` (personal, not a public
service).
