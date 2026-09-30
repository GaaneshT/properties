<script lang="ts">
	import { quarterToNum, type QuarterPoint, type Series } from '$lib/data';
	import { fmtPsf } from '$lib/format';

	let { series, height = 320 }: { series: Series[]; height?: number } = $props();

	const PAD = { top: 16, right: 16, bottom: 34, left: 56 };

	// Drawn at the container's real width so axis labels stay at 12px on a
	// phone instead of being scaled down with a fixed viewBox.
	let cw = $state(0);
	const W = $derived(Math.max(280, cw || 720));
	const H = $derived(Math.round(Math.min(height, Math.max(220, W * 0.62))));

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

	// X labels: the axis is time-scaled and quarters can be missing, so pick
	// labels by distance on screen rather than by index.
	const xLabels = $derived.by(() => {
		const uniq = [...new Set(allPoints.map((p) => p.quarter))].sort(
			(a, b) => quarterToNum(a) - quarterToNum(b)
		);
		const out: string[] = [];
		let lastX = -Infinity;
		for (const q of uniq) {
			const x = sx(quarterToNum(q));
			if (x - lastX >= 68) {
				out.push(q);
				lastX = x;
			}
		}
		return out;
	});

	// Hover / tap state.
	let hover: { x: number; y: number; label: string; q: string; psf: number; n: number } | null =
		$state(null);

	function onMove(e: PointerEvent) {
		const svg = e.currentTarget as SVGSVGElement;
		const rect = svg.getBoundingClientRect();
		const px = ((e.clientX - rect.left) / rect.width) * W;
		const py = ((e.clientY - rect.top) / rect.height) * H;
		// Nearest quarter first, then the nearest series at that quarter.
		let best: typeof hover = null;
		let bestDist = Infinity;
		for (const s of series) {
			for (const p of s.points) {
				const x = sx(quarterToNum(p.quarter));
				const y = sy(p.medianPsf);
				const d = Math.abs(x - px) * 4 + Math.abs(y - py);
				if (d < bestDist) {
					bestDist = d;
					best = { x, y, label: s.label, q: p.quarter, psf: p.medianPsf, n: p.count };
				}
			}
		}
		hover = best && Math.abs(best.x - px) < 40 ? best : null;
	}
</script>

<div class="w-full" bind:clientWidth={cw}>
	<svg
		viewBox="0 0 {W} {H}"
		width={W}
		height={H}
		class="chart block h-auto w-full touch-pan-y select-none"
		role="img"
		aria-label="Median PSF over time"
		onpointermove={onMove}
		onpointerdown={onMove}
		onpointerleave={() => (hover = null)}
	>
		<!-- Y grid + labels -->
		{#each yTicks as t}
			<line x1={PAD.left} x2={W - PAD.right} y1={sy(t)} y2={sy(t)} stroke="var(--rule)" stroke-width="1" />
			<text x={PAD.left - 8} y={sy(t) + 4} text-anchor="end" font-size="12" fill="var(--faint)"
				>{fmtPsf(t)}</text
			>
		{/each}

		<!-- X labels -->
		{#each xLabels as q}
			<text
				x={sx(quarterToNum(q))}
				y={H - 12}
				text-anchor={sx(quarterToNum(q)) > W - PAD.right - 30 ? 'end' : 'middle'}
				font-size="12"
				fill="var(--faint)"
				>{q}</text
			>
		{/each}

		<!-- Series -->
		{#each series as s}
			<path d={pathFor(s.points)} fill="none" stroke={s.color} stroke-width="2" />
			{#each s.points as p}
				<circle cx={sx(quarterToNum(p.quarter))} cy={sy(p.medianPsf)} r="2.5" fill={s.color} />
			{/each}
		{/each}

		<!-- Hover marker -->
		{#if hover}
			<line
				x1={hover.x}
				x2={hover.x}
				y1={PAD.top}
				y2={H - PAD.bottom}
				stroke="var(--ink2)"
				stroke-opacity="0.35"
				stroke-dasharray="3 3"
			/>
			<circle cx={hover.x} cy={hover.y} r="4.5" fill="var(--card)" stroke="var(--ink)" stroke-width="1.5" />
		{/if}
	</svg>

	<!-- Readout. Always occupies its line so hovering never shifts the page. -->
	<p class="tabular mt-2 flex min-h-[30px] flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-ink-700">
		{#if hover}
			<span class="font-semibold text-ink-900">{hover.q}</span>
			<span>{hover.label}</span>
			<span class="font-semibold text-ink-900">{fmtPsf(hover.psf)} psf</span>
			<span class="text-ghost-600">{hover.n} txn{hover.n === 1 ? '' : 's'}</span>
		{:else}
			<span class="text-ghost-600">Hover or tap the chart for a quarter's median.</span>
		{/if}
	</p>
</div>
