// Single source of truth for the viewer. The JSON is produced server-side by
// scripts/pull_ura.py and committed to data/. We import it at build time, so the
// front end never touches the URA API (and there's no AccessKey anywhere near
// the browser). Re-baking + redeploying is what refreshes the site.
import transactionsData from '../../data/transactions.json';
import metaData from '../../data/meta.json';

export type SaleCode = '1' | '2' | '3';

export type Transaction = {
	date: string; // 'YYYY-MM'
	year: number;
	quarter: string; // 'YYYY-Qn'
	psf: number;
	price: number;
	areaSqft: number;
	areaSqm: number;
	floorRange: string;
	typeOfSale: string; // SaleCode as string
	saleType: string; // human label
	propertyType: string;
	tenure: string;
	tenureClass: 'freehold' | 'leasehold' | 'unknown';
	noOfUnits: number;
};

export type Project = {
	project: string;
	street: string;
	marketSegment: string;
	district: string;
	x: string;
	y: string;
	transactions: Transaction[];
	summary: Record<string, unknown>;
};

export type Meta = {
	refreshedAt: string;
	source: string;
	service: string;
	watchlist: string[];
	projectCount: number;
	transactionCount: number;
	note: string;
	mock?: boolean;
};

export const projects: Project[] = (transactionsData as { projects: Project[] }).projects;
export const meta: Meta = metaData as Meta;

// Verified against a live URA response (2026-06): 1=new sale, 2=sub-sale,
// 3=resale. (2 and 3 are swapped vs the order one might assume.)
export const SALE_LABELS: Record<SaleCode, string> = {
	'1': 'new sale',
	'2': 'sub-sale',
	'3': 'resale'
};

// ── Color assignment for multi-project overlay ──────────────────────────────
export const SERIES_COLORS = [
	'var(--color-neon-cyan)',
	'var(--color-neon-violet)',
	'var(--color-neon-amber)',
	'var(--color-neon-rose)',
	'var(--color-neon-green)',
	'var(--color-neon-teal)'
];

export const colorFor = (index: number) => SERIES_COLORS[index % SERIES_COLORS.length];

// ── Filtering ───────────────────────────────────────────────────────────────
export type Filters = {
	sales: Set<SaleCode>; // which typeOfSale codes to include
	tenure: 'all' | 'freehold' | 'leasehold';
};

export function filterTxns(txns: Transaction[], f: Filters): Transaction[] {
	return txns.filter((t) => {
		if (!f.sales.has(t.typeOfSale as SaleCode)) return false;
		if (f.tenure !== 'all' && t.tenureClass !== f.tenure) return false;
		return true;
	});
}

// ── Aggregation (recomputed for the active filter) ──────────────────────────
function median(values: number[]): number {
	if (values.length === 0) return NaN;
	const s = [...values].sort((a, b) => a - b);
	const mid = Math.floor(s.length / 2);
	return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

export type QuarterPoint = { quarter: string; medianPsf: number; count: number };

// Chart input shapes (shared by the page and the chart components).
export type Series = { label: string; color: string; points: QuarterPoint[] };
export type Dist = { label: string; color: string; values: number[] };

export function medianPsfByQuarter(txns: Transaction[]): QuarterPoint[] {
	const byQ = new Map<string, number[]>();
	for (const t of txns) {
		const arr = byQ.get(t.quarter) ?? [];
		arr.push(t.psf);
		byQ.set(t.quarter, arr);
	}
	return [...byQ.entries()]
		.map(([quarter, psfs]) => ({
			quarter,
			medianPsf: Math.round(median(psfs) * 100) / 100,
			count: psfs.length
		}))
		.sort((a, b) => quarterToNum(a.quarter) - quarterToNum(b.quarter));
}

export function quarterToNum(q: string): number {
	// '2023-Q2' -> 2023*4 + 1
	const [y, qq] = q.split('-Q');
	return Number(y) * 4 + (Number(qq) - 1);
}

export type Stats = {
	count: number;
	medianPsf: number;
	minPsf: number;
	maxPsf: number;
	medianPrice: number;
	minPrice: number;
	maxPrice: number;
};

export function statsFor(txns: Transaction[]): Stats | null {
	if (txns.length === 0) return null;
	const psfs = txns.map((t) => t.psf);
	const prices = txns.map((t) => t.price);
	return {
		count: txns.length,
		medianPsf: Math.round(median(psfs) * 100) / 100,
		minPsf: Math.min(...psfs),
		maxPsf: Math.max(...psfs),
		medianPrice: Math.round(median(prices)),
		minPrice: Math.min(...prices),
		maxPrice: Math.max(...prices)
	};
}

// Histogram bins for the PSF distribution view.
export function histogram(
	values: number[],
	binCount = 12
): { x0: number; x1: number; n: number }[] {
	if (values.length === 0) return [];
	const min = Math.min(...values);
	const max = Math.max(...values);
	if (min === max) return [{ x0: min, x1: max, n: values.length }];
	const width = (max - min) / binCount;
	const bins = Array.from({ length: binCount }, (_, i) => ({
		x0: min + i * width,
		x1: min + (i + 1) * width,
		n: 0
	}));
	for (const v of values) {
		let idx = Math.floor((v - min) / width);
		if (idx >= binCount) idx = binCount - 1;
		bins[idx].n++;
	}
	return bins;
}
