# properties.gaanesh.com

A fast, free, open analytics tool over Singapore URA private residential
transactions. It doesn't compete with the portals on listings or live
valuations — it wins on **analysis of the public URA caveat data**: median PSF
trends, realized returns, rental yields and league tables, with no login, no
ads, no paywall.

Built with SvelteKit + `adapter-static` and Tailwind (matching the sibling
`tools.gaanesh.com` repo), deployed to GitHub Pages.

## What it does

- **League table of every project** (~3,000) — search, filter (type, region,
  tenure, min volume) and sort by median PSF, price trend, return p.a., gross
  yield, size, velocity.
- **Compare up to 6 projects** — median-PSF-over-time overlay, PSF-vs-size
  scatter, PSF distribution, and a deep-dive panel.
- **Derived analytics computed server-side** at build time:
  - Median PSF time series (quarterly), segmented by sale type.
  - Approximate repeat-sale realized returns — annualised. The caveat feed has
    no unit number, so "same unit" is proxied by identical floor area + floor
    band within a project (a documented approximation; pair counts shown).
  - New-sale → resale uplift (launch vintage vs recent resale PSF).
  - PSF premium by floor band and by size bucket.
  - Liquidity / velocity (transactions per year).
  - Gross rental yield (URA rental medians × 12 ÷ sale median PSF).
- **Shareable URLs** — filters + selection are encoded in the query string and
  restored on load.

## Architecture (and why the API key is safe)

The URA AccessKey runs only server-side, in a scheduled GitHub Action. It pulls
all 4 transaction batches + the rental medians, computes the derived analytics,
and commits the results under `static/data/`:

- `index.json` — one compact record per project for the league table (~200 KB
  gzipped even with ~3,000 projects). Loaded once.
- `districts/D<nn>.json` — transaction-level detail + per-project breakdowns,
  **lazy-loaded** per district only when you open/compare a project, cached in
  memory.
- `meta.json` — refresh timestamp + coverage notes.

The browser never calls the URA API and never sees the key. The full dataset is
never shipped to the browser. Data is derived (not a raw caveat dump) and the
site is `noindex`.

## Local development

```sh
npm install                                    # Node ^20.19 || ^22.13 || >=24
npm run dev                                     # http://localhost:5173
npm run build                                   # static output in build/
npm run check                                   # svelte-check

# Re-bake data (server-side; key is never stored):
URA_ACCESS_KEY=xxxx python scripts/pull_ura.py  # needs `pip install requests`
python scripts/pull_ura.py --mock               # no key; baked sample
```

To restrict to a watchlist instead of all projects, set `WATCHLIST` at the top
of `scripts/pull_ura.py` (empty = every project).

## Automation

- `.github/workflows/refresh-ura.yml` — monthly cron + manual dispatch; re-bakes
  `static/data/`, commits if changed, then dispatches the deploy.
- `.github/workflows/deploy.yml` — builds and deploys to GitHub Pages.

## Licence & attribution

Data: URA, via the URA Data Service, under the
[Singapore Open Data Licence v1.0](https://data.gov.sg/open-data-licence). This
is a personal project, not affiliated with or endorsed by URA, provided "as is"
with no warranty. Caveat data covers ~80–90% of resale/sub-sale volume on a
60-month rolling window.
