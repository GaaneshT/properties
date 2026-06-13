<script lang="ts">
	import { type Dist } from '$lib/data';
	import { fmtPsf } from '$lib/format';

	// One distribution per project, overlaid as grouped bars sharing a common
	// PSF axis so projects are directly comparable.
	let { dists, height = 240, bins = 12 }: { dists: Dist[]; height?: number; bins?: number } =
		$props();

	const PAD = { top: 12, right: 12, bottom: 30, left: 40 };
	const W = 720;
	const H = $derived(height);

	const allValues = $derived(dists.flatMap((d) => d.values));
	const min = $derived(allValues.length ? Math.min(...allValues) : 0);
	const max = $derived(allValues.length ? Math.max(...allValues) : 1);

	// Shared bin edges across every project.
	const edges = $derived.by(() => {
		const n = bins;
		if (min === max) return [min, min + 1];
		const w = (max - min) / n;
		return Array.from({ length: n + 1 }, (_, i) => min + i * w);
	});

	function binize(values: number[]) {
		const n = edges.length - 1;
		const counts = new Array(n).fill(0);
		const w = (max - min) / n || 1;
		for (const v of values) {
			let idx = Math.floor((v - min) / w);
			if (idx >= n) idx = n - 1;
			if (idx < 0) idx = 0;
			counts[idx]++;
		}
		return counts;
	}

	const binned = $derived(dists.map((d) => ({ ...d, counts: binize(d.values) })));
	const maxCount = $derived(Math.max(1, ...binned.flatMap((b) => b.counts)));

	const n = $derived(edges.length - 1);
	const plotW = $derived(W - PAD.left - PAD.right);
	const groupW = $derived(plotW / n);
	const barW = $derived((groupW * 0.8) / Math.max(1, dists.length));

	const sy = (count: number) =>
		H - PAD.bottom - (count / maxCount) * (H - PAD.top - PAD.bottom);
</script>

<div class="w-full">
	<svg viewBox="0 0 {W} {H}" class="h-auto w-full" role="img" aria-label="PSF distribution">
		<!-- Baseline -->
		<line
			x1={PAD.left}
			x2={W - PAD.right}
			y1={H - PAD.bottom}
			y2={H - PAD.bottom}
			stroke="var(--color-ink-600)"
			stroke-opacity="0.4"
		/>

		{#each binned as d, di}
			{#each d.counts as c, bi}
				{#if c > 0}
					<rect
						x={PAD.left + bi * groupW + groupW * 0.1 + di * barW}
						y={sy(c)}
						width={Math.max(1, barW - 1)}
						height={H - PAD.bottom - sy(c)}
						fill={d.color}
						fill-opacity="0.8"
						rx="1"
					>
						<title>{d.label}: {c} txns @ {fmtPsf(edges[bi])}–{fmtPsf(edges[bi + 1])} psf</title>
					</rect>
				{/if}
			{/each}
		{/each}

		<!-- X axis labels: a few bin edges -->
		{#each edges as e, i}
			{#if i % 3 === 0 || i === edges.length - 1}
				<text
					x={PAD.left + i * groupW}
					y={H - 10}
					text-anchor="middle"
					font-family="JetBrains Mono"
					font-size="10"
					fill="var(--color-ghost-400)">{fmtPsf(e)}</text
				>
			{/if}
		{/each}
	</svg>
</div>
