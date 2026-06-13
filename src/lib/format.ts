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

export const fmtDate = (iso: string) => {
	try {
		return new Date(iso).toLocaleString(undefined, {
			dateStyle: 'medium',
			timeStyle: 'short'
		});
	} catch {
		return iso;
	}
};
