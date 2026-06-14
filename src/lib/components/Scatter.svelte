<script lang="ts">
	import { type ScatterSeries } from '$lib/data';
	import { fmtPsf, fmtArea } from '$lib/format';

	// Each point: x = size (sqft), y = PSF. Reveals the size/price relationship
	// and lets you eyeball where a project sits vs others.
	let { series, height = 300 }: { series: ScatterSeries[]; height?: number } = $props();

	const PAD = { top: 14, right: 14, bottom: 40, left: 56 };
	const W = 720;
	const H = $derived(height);

	const pts = $derived(series.flatMap((s) => s.points));
	const xs = $derived(pts.map((p) => p.x));
	const ys = $derived(pts.map((p) => p.y));
	const xMin = $derived(xs.length ? Math.min(...xs) : 0);
	const xMax = $derived(xs.length ? Math.max(...xs) : 1);
	const yMin = $derived(ys.length ? Math.min(...ys) : 0);
	const yMax = $derived(ys.length ? Math.max(...ys) : 1);

	const sx = (x: number) =>
		PAD.left + ((x - xMin) / Math.max(1, xMax - xMin)) * (W - PAD.left - PAD.right);
	const sy = (y: number) =>
		H - PAD.bottom - ((y - yMin) / Math.max(1, yMax - yMin)) * (H - PAD.top - PAD.bottom);

	const yTicks = $derived(Array.from({ length: 5 }, (_, i) => yMin + ((yMax - yMin) * i) / 4));
	const xTicks = $derived(Array.from({ length: 5 }, (_, i) => xMin + ((xMax - xMin) * i) / 4));
</script>

<svg viewBox="0 0 {W} {H}" class="h-auto w-full" role="img" aria-label="PSF vs size scatter">
	{#each yTicks as t}
		<line
			x1={PAD.left}
			x2={W - PAD.right}
			y1={sy(t)}
			y2={sy(t)}
			stroke="var(--color-ink-500)"
			stroke-opacity="0.18"
		/>
		<text
			x={PAD.left - 8}
			y={sy(t) + 3}
			text-anchor="end"
			font-size="12"
			fill="var(--color-ghost-400)">{fmtPsf(t)}</text
		>
	{/each}
	{#each xTicks as t}
		<text
			x={sx(t)}
			y={H - 22}
			text-anchor="middle"
			font-size="12"
			fill="var(--color-ghost-400)">{Math.round(t).toLocaleString()}</text
		>
	{/each}
	<text
		x={(PAD.left + W - PAD.right) / 2}
		y={H - 6}
		text-anchor="middle"
		font-size="12"
		fill="var(--color-ghost-500)">size (sqft) →</text
	>

	{#each series as s}
		{#each s.points as p}
			<circle cx={sx(p.x)} cy={sy(p.y)} r="3" fill={s.color} fill-opacity="0.55">
				<title>{s.label}: {fmtPsf(p.y)} psf · {fmtArea(p.x)}</title>
			</circle>
		{/each}
	{/each}
</svg>
