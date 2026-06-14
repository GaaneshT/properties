<script lang="ts">
	import { quarterToNum, type QuarterPoint, type Series } from '$lib/data';
	import { fmtPsf } from '$lib/format';

	let { series, height = 320 }: { series: Series[]; height?: number } = $props();

	const PAD = { top: 16, right: 16, bottom: 34, left: 52 };
	const W = 720;
	const H = $derived(height);

	// Domain across all series.
	const allPoints = $derived(series.flatMap((s) => s.points));
	const xs = $derived(allPoints.map((p) => quarterToNum(p.quarter)));
	const ys = $derived(allPoints.map((p) => p.medianPsf));

	const xMin = $derived(xs.length ? Math.min(...xs) : 0);
	const xMax = $derived(xs.length ? Math.max(...xs) : 1);
	const yMinRaw = $derived(ys.length ? Math.min(...ys) : 0);
	const yMaxRaw = $derived(ys.length ? Math.max(...ys) : 1);
	// Pad the y-domain ~8% so lines don't kiss the frame.
	const yPad = $derived(Math.max(1, (yMaxRaw - yMinRaw) * 0.08));
	const yMin = $derived(yMinRaw - yPad);
	const yMax = $derived(yMaxRaw + yPad);

	const sx = (x: number) =>
		PAD.left + ((x - xMin) / Math.max(1, xMax - xMin)) * (W - PAD.left - PAD.right);
	const sy = (y: number) =>
		H - PAD.bottom - ((y - yMin) / Math.max(1, yMax - yMin)) * (H - PAD.top - PAD.bottom);

	const pathFor = (pts: QuarterPoint[]) =>
		pts
			.map(
				(p, i) => `${i === 0 ? 'M' : 'L'}${sx(quarterToNum(p.quarter)).toFixed(1)},${sy(p.medianPsf).toFixed(1)}`
			)
			.join(' ');

	// Y gridlines (5 ticks).
	const yTicks = $derived.by(() => {
		const n = 4;
		return Array.from({ length: n + 1 }, (_, i) => yMin + ((yMax - yMin) * i) / n);
	});

	// X labels — show a subset of quarters to avoid crowding.
	const xLabels = $derived.by(() => {
		const uniq = [...new Set(allPoints.map((p) => p.quarter))].sort(
			(a, b) => quarterToNum(a) - quarterToNum(b)
		);
		const step = Math.ceil(uniq.length / 6) || 1;
		return uniq.filter((_, i) => i % step === 0 || i === uniq.length - 1);
	});

	// Hover state.
	let hover: { x: number; y: number; label: string; q: string; psf: number; n: number } | null =
		$state(null);

	function onMove(e: MouseEvent) {
		const svg = e.currentTarget as SVGSVGElement;
		const rect = svg.getBoundingClientRect();
		const px = ((e.clientX - rect.left) / rect.width) * W;
		// Find nearest point across all series.
		let best: typeof hover = null;
		let bestDist = Infinity;
		for (const s of series) {
			for (const p of s.points) {
				const d = Math.abs(sx(quarterToNum(p.quarter)) - px);
				if (d < bestDist) {
					bestDist = d;
					best = {
						x: sx(quarterToNum(p.quarter)),
						y: sy(p.medianPsf),
						label: s.label,
						q: p.quarter,
						psf: p.medianPsf,
						n: p.count
					};
				}
			}
		}
		hover = bestDist < 40 ? best : null;
	}
</script>

<div class="w-full">
	<svg
		viewBox="0 0 {W} {H}"
		class="h-auto w-full select-none"
		role="img"
		aria-label="Median PSF over time"
		onmousemove={onMove}
		onmouseleave={() => (hover = null)}
	>
		<!-- Y grid + labels -->
		{#each yTicks as t}
			<line
				x1={PAD.left}
				x2={W - PAD.right}
				y1={sy(t)}
				y2={sy(t)}
				stroke="var(--color-ink-600)"
				stroke-opacity="0.25"
				stroke-width="1"
			/>
			<text
				x={PAD.left - 8}
				y={sy(t) + 3}
				text-anchor="end"
				font-family="JetBrains Mono"
				font-size="12"
				fill="var(--color-ghost-400)">{fmtPsf(t)}</text
			>
		{/each}

		<!-- X labels -->
		{#each xLabels as q}
			<text
				x={sx(quarterToNum(q))}
				y={H - 12}
				text-anchor="middle"
				font-family="JetBrains Mono"
				font-size="12"
				fill="var(--color-ghost-400)">{q}</text
			>
		{/each}

		<!-- Series -->
		{#each series as s}
			<path d={pathFor(s.points)} fill="none" stroke={s.color} stroke-width="2" />
			{#each s.points as p}
				<circle
					cx={sx(quarterToNum(p.quarter))}
					cy={sy(p.medianPsf)}
					r="2.5"
					fill={s.color}
				/>
			{/each}
		{/each}

		<!-- Hover marker -->
		{#if hover}
			<line
				x1={hover.x}
				x2={hover.x}
				y1={PAD.top}
				y2={H - PAD.bottom}
				stroke="var(--color-neon-cyan)"
				stroke-opacity="0.4"
				stroke-dasharray="3 3"
			/>
			<circle cx={hover.x} cy={hover.y} r="4.5" fill="none" stroke="var(--color-neon-cyan)" stroke-width="2" />
		{/if}
	</svg>

	{#if hover}
		<div
			class="mt-2 inline-flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-ghost-200/60 bg-white/95 px-3 py-1.5 font-mono text-[11px] text-ink-700 shadow-sm dark:border-ink-600/60 dark:bg-ink-900/80 dark:text-ghost-200"
		>
			<span class="font-semibold text-neon-cyan">{hover.q}</span>
			<span>{hover.label}</span>
			<span class="text-ink-900 dark:text-white">{fmtPsf(hover.psf)} psf</span>
			<span class="text-ghost-500">· {hover.n} txn{hover.n === 1 ? '' : 's'}</span>
		</div>
	{/if}
</div>
