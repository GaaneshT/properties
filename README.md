# properties.gaanesh.com

A static, read-only viewer over Singapore URA private residential transaction
data. A personal tool for observing resale prices and comparing projects —
median PSF trends and price distributions for a small watchlist. Not an
estate-agent site: no listings, no enquiries, no lead capture. Just data and
charts.

Built with SvelteKit + `adapter-static` and Tailwind, matching the sibling
`tools.gaanesh.com` repo, and deployed to GitHub Pages.

## What it does

- Pick one or more projects from the watchlist and compare them side by side.
- Median price-per-sqft over time, overlaid across projects.
- Price-per-sqft distribution with basic stats (count, median, range).
- Segment by type of sale (resale by default) and tenure.

## How the data flows

The URA AccessKey runs only server-side, in a scheduled GitHub Action. It
exchanges a daily token, pulls the transaction batches, computes derived views
(PSF, medians, quarterly trends, distributions) for the watchlist, and commits
`data/transactions.json` + `data/meta.json`. The front end reads only those
committed files — the browser never calls the URA API and never sees the key.

## Licence & attribution

Data: URA, via the URA Data Service, under the
[Singapore Open Data Licence v1.0](https://data.gov.sg/open-data-licence). This
is a personal project, not affiliated with or endorsed by URA, provided "as is"
with no warranty. Caveat data covers ~80–90% of resale/sub-sale volume on a
60-month rolling window.
