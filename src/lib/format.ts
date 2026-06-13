export const fmtPsf = (n: number) =>
	Number.isFinite(n) ? `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—';

export const fmtPrice = (n: number) => {
	if (!Number.isFinite(n)) return '—';
	if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
	if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
	return `$${n}`;
};

export const fmtPriceFull = (n: number) =>
	Number.isFinite(n) ? `$${Math.round(n).toLocaleString()}` : '—';

export const fmtArea = (n: number) =>
	Number.isFinite(n) ? `${n.toLocaleString(undefined, { maximumFractionDigits: 0 })} sqft` : '—';

export const fmtTrend = (n: number | null) => {
	if (n === null || !Number.isFinite(n)) return '—';
	const sign = n > 0 ? '+' : '';
	return `${sign}${n.toFixed(1)}%`;
};

export const fmtDate = (iso: string) => {
	try {
		return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
	} catch {
		return iso;
	}
};

/** Build an SVG path for a tiny sparkline from y-values. */
export function sparklinePath(values: number[], width = 80, height = 24, pad = 2): string {
	if (values.length === 0) return '';
	const min = Math.min(...values);
	const max = Math.max(...values);
	const range = max - min || 1;
	const stepX = (width - pad * 2) / (values.length - 1 || 1);
	return values
		.map((v, i) => {
			const x = pad + i * stepX;
			const y = height - pad - ((v - min) / range) * (height - pad * 2);
			return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`;
		})
		.join(' ');
}
