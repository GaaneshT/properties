// Runtime data access. The committed JSON lives under static/data and is served
// at /data/... by GitHub Pages. We fetch the lightweight index up front and pull
// per-district transaction shards on demand (lazily, cached). The browser never
// calls the URA API — only these pre-baked, derived files.
import { base } from '$app/paths';

// ── Shapes (mirror scripts/pull_ura.py output) ──────────────────────────────
export type SaleCode = '1' | '2' | '3';
export type Category = 'condo' | 'ec' | 'landed' | 'other';
export type Region = 'CCR' | 'RCR' | 'OCR' | '';
export type TenureClass = 'freehold' | 'leasehold' | 'unknown';

export type IndexEntry = {
	project: string;
	street: string;
	district: string;
	region: Region;
	category: Category;
	tenureClass: TenureClass;
	basis: 'resale' | 'all';
	nAll: number;
	recent12: number;
	medianPsf: number;
	medianPrice: number;
	medianAreaSqft: number;
	trendPct: number | null;
	txnsPerYear: number;
	upliftPct: number | null;
	repeatPairs: number;
	repeatAnnReturn: number | null;
	floorPremiumPct: number | null;
	rentPsf: number | null;
	grossYield: number | null;
	yearly: [number, number, number][]; // [year, medianPsf, count]
};

export type RentalPoint = { refPeriod: string; median: number };

export type ShardTxn = {
	date: string;
	quarter: string;
	psf: number;
	price: number;
	areaSqft: number;
	floorRange: string;
	typeOfSale: string;
	tenureClass: TenureClass;
	propertyType: string;
};

export type FloorPremium = {
	floorRange: string;
	medianPsf: number;
	count: number;
	premiumPct: number | null;
};
export type SizePremium = {
	bucket: string;
	medianPsf: number;
	count: number;
	premiumPct: number | null;
};
export type RepeatSale = {
	areaSqft: number;
	floorRange: string;
	buyDate: string;
	sellDate: string;
	buyPrice: number;
	sellPrice: number;
	holdYears: number;
	annReturnPct: number;
	totalReturnPct: number;
};
export type Uplift = {
	newMedianPsf: number | null;
	newCount: number;
	currentResalePsf: number | null;
	upliftPct: number | null;
};

export type ShardProject = {
	project: string;
	street: string;
	district: string;
	region: Region;
	tenureClass: TenureClass;
	transactions: ShardTxn[];
	summary: Record<string, unknown>;
	byFloor: FloorPremium[];
	bySize: SizePremium[];
	uplift: Uplift;
	repeatStats: { pairs: number; medianAnnReturnPct: number | null; medianHoldYears: number | null };
	repeatSales: RepeatSale[];
	rental: { rentPsf: number | null; grossYield: number | null; series: RentalPoint[] };
};

export type Meta = {
	refreshedAt: string;
	source: string;
	service: string;
	projectCount: number;
	transactionCount: number;
	districtCount: number;
	rentalProjectCount?: number;
	recentCount?: number;
	recentLatest?: string | null;
	note: string;
	mock?: boolean;
};

// ── Fetching (cached) ────────────────────────────────────────────────────────
export const districtKey = (district: string) => (district ? `D${district}` : 'DNA');

let _index: Promise<IndexEntry[]> | null = null;
export function loadIndex(): Promise<IndexEntry[]> {
	return (_index ??= fetch(`${base}/data/index.json`).then((r) => {
		if (!r.ok) throw new Error(`index.json: ${r.status}`);
		return r.json();
	}));
}

let _meta: Promise<Meta> | null = null;
export function loadMeta(): Promise<Meta> {
	return (_meta ??= fetch(`${base}/data/meta.json`).then((r) => r.json()));
}

export type RecentTxn = {
	date: string; // 'YYYY-MM'
	project: string;
	street: string;
	district: string;
	region: Region;
	category: Category;
	price: number;
	psf: number;
	areaSqft: number;
	floorRange: string;
	typeOfSale: string;
	propertyType: string;
	tenureClass: TenureClass;
};

let _recent: Promise<RecentTxn[]> | null = null;
export function loadRecent(): Promise<RecentTxn[]> {
	return (_recent ??= fetch(`${base}/data/recent.json`).then((r) => {
		if (!r.ok) throw new Error(`recent.json: ${r.status}`);
		return r.json();
	}));
}

const _shards = new Map<string, Promise<ShardProject[]>>();
export function loadDistrict(dkey: string): Promise<ShardProject[]> {
	let p = _shards.get(dkey);
	if (!p) {
		p = fetch(`${base}/data/districts/${dkey}.json`).then((r) => {
			if (!r.ok) throw new Error(`${dkey}.json: ${r.status}`);
			return r.json();
		});
		_shards.set(dkey, p);
	}
	return p;
}

/** Fetch the ShardProject records for a set of index entries (dedupes shards). */
export async function loadProjects(entries: IndexEntry[]): Promise<Map<string, ShardProject>> {
	const dkeys = [...new Set(entries.map((e) => districtKey(e.district)))];
	const shards = await Promise.all(dkeys.map((k) => loadDistrict(k)));
	const byName = new Map<string, ShardProject>();
	for (const shard of shards) for (const p of shard) byName.set(p.project, p);
	const out = new Map<string, ShardProject>();
	for (const e of entries) {
		const p = byName.get(e.project);
		if (p) out.set(e.project, p);
	}
	return out;
}

// ── Labels (normal property jargon — kept, with a friendly expansion) ────────
export const SALE_LABELS: Record<SaleCode, string> = {
	'1': 'New sale',
	'2': 'Sub-sale',
	'3': 'Resale'
};

export const REGION_LABELS: Record<string, string> = {
	CCR: 'Core Central Region',
	RCR: 'Rest of Central Region',
	OCR: 'Outside Central Region'
};

export const CATEGORY_LABELS: Record<Category, string> = {
	condo: 'Condo / Apartment',
	ec: 'Executive Condo',
	landed: 'Landed',
	other: 'Other'
};

// ── Comparison palette ───────────────────────────────────────────────────────
export const SERIES_COLORS = [
	'var(--color-neon-cyan)',
	'var(--color-neon-violet)',
	'var(--color-neon-amber)',
	'var(--color-neon-rose)',
	'var(--color-neon-green)',
	'var(--color-neon-teal)'
];
export const colorFor = (i: number) => SERIES_COLORS[i % SERIES_COLORS.length];
export const MAX_COMPARE = 6;

// ── Filtering at the transaction level (for the comparison charts) ───────────
export type Filters = { sales: Set<SaleCode>; tenure: 'all' | 'freehold' | 'leasehold' };

export function filterTxns(txns: ShardTxn[], f: Filters): ShardTxn[] {
	return txns.filter((t) => {
		if (!f.sales.has(t.typeOfSale as SaleCode)) return false;
		if (f.tenure !== 'all' && t.tenureClass !== f.tenure) return false;
		return true;
	});
}

// ── Aggregation ──────────────────────────────────────────────────────────────
function median(values: number[]): number {
	if (values.length === 0) return NaN;
	const s = [...values].sort((a, b) => a - b);
	const mid = Math.floor(s.length / 2);
	return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

export type QuarterPoint = { quarter: string; medianPsf: number; count: number };
export type Series = { label: string; color: string; points: QuarterPoint[] };
export type Dist = { label: string; color: string; values: number[] };
export type ScatterPoint = { x: number; y: number };
export type ScatterSeries = { label: string; color: string; points: ScatterPoint[] };

export function quarterToNum(q: string): number {
	const [y, qq] = q.split('-Q');
	return Number(y) * 4 + (Number(qq) - 1);
}

export function medianPsfByQuarter(txns: ShardTxn[]): QuarterPoint[] {
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

export type Stats = {
	count: number;
	medianPsf: number;
	minPsf: number;
	maxPsf: number;
	medianPrice: number;
	minPrice: number;
	maxPrice: number;
	medianAreaSqft: number;
};

export function statsFor(txns: ShardTxn[]): Stats | null {
	if (txns.length === 0) return null;
	const psfs = txns.map((t) => t.psf);
	const prices = txns.map((t) => t.price);
	const areas = txns.map((t) => t.areaSqft);
	return {
		count: txns.length,
		medianPsf: Math.round(median(psfs) * 100) / 100,
		minPsf: Math.min(...psfs),
		maxPsf: Math.max(...psfs),
		medianPrice: Math.round(median(prices)),
		minPrice: Math.min(...prices),
		maxPrice: Math.max(...prices),
		medianAreaSqft: Math.round(median(areas))
	};
}
