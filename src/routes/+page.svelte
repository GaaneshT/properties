<script lang="ts">
	import { onMount } from 'svelte';
	import {
		loadIndex,
		loadProjects,
		filterTxns,
		medianPsfByQuarter,
		statsFor,
		colorFor,
		MAX_COMPARE,
		SALE_LABELS,
		REGION_LABELS,
		CATEGORY_LABELS,
		type IndexEntry,
		type ShardProject,
		type Category,
		type SaleCode,
		type Filters,
		type Series,
		type Dist,
		type ScatterSeries
	} from '$lib/data';
	import { fmtPsf, fmtPrice, fmtPriceFull, fmtArea, fmtTrend, sparklinePath } from '$lib/format';
	import SectionHeading from '$lib/components/SectionHeading.svelte';
	import LineChart from '$lib/components/LineChart.svelte';
	import Histogram from '$lib/components/Histogram.svelte';
	import Scatter from '$lib/components/Scatter.svelte';

	// ── Load ────────────────────────────────────────────────────────────────
	let entries = $state<IndexEntry[]>([]);
	let loading = $state(true);
	let loadError = $state<string | null>(null);

	onMount(async () => {
		try {
			entries = await loadIndex();
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	});

	// ── Filters ───────────────────────────────────────────────────────────────
	let search = $state('');
	let category = $state<Category | 'all'>('condo');
	let region = $state<'all' | 'CCR' | 'RCR' | 'OCR'>('all');
	let tenure = $state<'all' | 'freehold' | 'leasehold'>('all');
	let minVolume = $state(5); // ignore thinly-traded projects by default

	const ROW_CAP = 120;

	type SortKey = 'medianPsf' | 'trendPct' | 'medianPrice' | 'medianAreaSqft' | 'recent12' | 'nAll' | 'project';
	let sortKey = $state<SortKey>('nAll');
	let sortDir = $state<'asc' | 'desc'>('desc');

	function setSort(k: SortKey) {
		if (sortKey === k) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		else {
			sortKey = k;
			sortDir = k === 'project' ? 'asc' : 'desc';
		}
	}

	const filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		return entries.filter((e) => {
			if (category !== 'all' && e.category !== category) return false;
			if (region !== 'all' && e.region !== region) return false;
			if (tenure !== 'all' && e.tenureClass !== tenure) return false;
			if (e.nAll < minVolume) return false;
			if (q && !(`${e.project} ${e.street}`.toLowerCase().includes(q))) return false;
			return true;
		});
	});

	const sorted = $derived.by(() => {
		const arr = [...filtered];
		const dir = sortDir === 'asc' ? 1 : -1;
		arr.sort((a, b) => {
			if (sortKey === 'project') return a.project.localeCompare(b.project) * dir;
			const av = (a[sortKey] ?? -Infinity) as number;
			const bv = (b[sortKey] ?? -Infinity) as number;
			return (av - bv) * dir;
		});
		return arr;
	});

	const visible = $derived(sorted.slice(0, ROW_CAP));

	// ── KPI summary over the filtered set ──────────────────────────────────────
	function med(xs: number[]): number {
		if (!xs.length) return NaN;
		const s = [...xs].sort((a, b) => a - b);
		const m = Math.floor(s.length / 2);
		return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
	}
	const kpi = $derived.by(() => {
		const f = filtered;
		const trends = f.map((e) => e.trendPct).filter((t): t is number => t !== null);
		return {
			count: f.length,
			medianPsf: med(f.map((e) => e.medianPsf)),
			medianPrice: med(f.map((e) => e.medianPrice)),
			medianTrend: trends.length ? med(trends) : NaN
		};
	});

	// ── Selection / comparison ─────────────────────────────────────────────────
	let selected = $state<Set<string>>(new Set());
	let shardMap = $state<Map<string, ShardProject>>(new Map());
	let shardLoading = $state(false);

	function toggle(name: string) {
		const next = new Set(selected);
		if (next.has(name)) next.delete(name);
		else {
			if (next.size >= MAX_COMPARE) return;
			next.add(name);
		}
		selected = next;
	}
	const clearSelection = () => (selected = new Set());

	const selectedEntries = $derived(entries.filter((e) => selected.has(e.project)));

	// Lazily fetch district shards for whatever is selected.
	$effect(() => {
		const need = selectedEntries.filter((e) => !shardMap.has(e.project));
		if (need.length === 0) return;
		shardLoading = true;
		loadProjects(need)
			.then((m) => {
				const merged = new Map(shardMap);
				for (const [k, v] of m) merged.set(k, v);
				shardMap = merged;
			})
			.finally(() => (shardLoading = false));
	});

	// Chart-level filters (resale by default — mixing new launches distorts trends).
	let sales = $state<Set<SaleCode>>(new Set(['3']));
	let chartTenure = $state<'all' | 'freehold' | 'leasehold'>('all');
	const SALE_OPTIONS: SaleCode[] = ['3', '2', '1'];
	function toggleSale(c: SaleCode) {
		const next = new Set(sales);
		next.has(c) ? next.delete(c) : next.add(c);
		if (next.size === 0) next.add('3');
		sales = next;
	}
	const chartFilters = $derived<Filters>({ sales, tenure: chartTenure });

	const views = $derived.by(() => {
		return selectedEntries
			.map((e, i) => {
				const sp = shardMap.get(e.project);
				if (!sp) return null;
				const txns = filterTxns(sp.transactions, chartFilters);
				return {
					entry: e,
					color: colorFor(i),
					txns,
					points: medianPsfByQuarter(txns),
					stats: statsFor(txns)
				};
			})
			.filter((v): v is NonNullable<typeof v> => v !== null);
	});

	const lineSeries = $derived<Series[]>(
		views.filter((v) => v.points.length).map((v) => ({ label: v.entry.project, color: v.color, points: v.points }))
	);
	const dists = $derived<Dist[]>(
		views.filter((v) => v.txns.length).map((v) => ({ label: v.entry.project, color: v.color, values: v.txns.map((t) => t.psf) }))
	);
	const scatter = $derived<ScatterSeries[]>(
		views.filter((v) => v.txns.length).map((v) => ({ label: v.entry.project, color: v.color, points: v.txns.map((t) => ({ x: t.areaSqft, y: t.psf })) }))
	);

	const trendColor = (t: number | null) =>
		t === null ? 'text-ghost-500' : t > 1 ? 'text-neon-green' : t < -1 ? 'text-neon-rose' : 'text-ghost-400';

	const cols: { key: SortKey; label: string; help?: string }[] = [
		{ key: 'project', label: 'Project' },
		{ key: 'medianPsf', label: 'Median PSF' },
		{ key: 'trendPct', label: 'Trend', help: 'Change in yearly-median PSF over the window' },
		{ key: 'medianPrice', label: 'Median price' },
		{ key: 'medianAreaSqft', label: 'Median size' },
		{ key: 'recent12', label: 'Sold (12m)', help: 'Transactions in the last 12 months' },
		{ key: 'nAll', label: 'Total txns' }
	];
</script>

<svelte:head>
	<title>SG Property Analytics · properties.gaanesh.com</title>
</svelte:head>

<!-- Header -->
<section class="space-y-2">
	<span class="text-xs font-semibold uppercase tracking-[0.15em] text-neon-cyan">URA caveat data</span>
	<h1 class="text-3xl font-semibold text-ink-900 dark:text-white">Singapore property analytics</h1>
	<p class="max-w-2xl text-sm text-ink-600 dark:text-ghost-300">
		Browse, filter and compare private residential projects on median PSF, price trend, size and
		transaction volume. Pick a few to compare side by side. Figures are derived from URA caveat data
		(60-month window), resale-weighted by default.
	</p>
</section>

{#if loading}
	<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-8 text-center text-sm text-ghost-500 dark:border-ink-600/60 dark:bg-ink-900/60">
		Loading data…
	</div>
{:else if loadError}
	<div class="rounded-2xl border border-neon-rose/40 bg-neon-rose/5 p-6 text-sm text-neon-rose">
		Couldn't load data: {loadError}
	</div>
{:else}
	<!-- KPI strip -->
	<section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
		{#each [{ label: 'Projects in view', value: kpi.count.toLocaleString() }, { label: 'Median PSF', value: fmtPsf(kpi.medianPsf) }, { label: 'Median price', value: fmtPrice(kpi.medianPrice) }, { label: 'Median trend', value: fmtTrend(Number.isFinite(kpi.medianTrend) ? kpi.medianTrend : null) }] as k}
			<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
				<p class="text-xs uppercase tracking-wide text-ghost-500">{k.label}</p>
				<p class="mt-1 text-2xl font-semibold text-ink-900 dark:text-white">{k.value}</p>
			</div>
		{/each}
	</section>

	<!-- Filters -->
	<section class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
		<div class="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-end">
			<label class="flex-1 min-w-[200px]">
				<span class="mb-1 block text-xs font-medium text-ghost-500">Search project or street</span>
				<input
					type="search"
					bind:value={search}
					placeholder="e.g. Reflections, Clematis…"
					class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm text-ink-900 dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100"
				/>
			</label>

			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Type</span>
				<select bind:value={category} class="rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="condo">Condo / Apartment</option>
					<option value="ec">Executive Condo</option>
					<option value="landed">Landed</option>
					<option value="all">All types</option>
				</select>
			</label>

			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Region</span>
				<select bind:value={region} class="rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="all">All regions</option>
					<option value="CCR">CCR · Core Central</option>
					<option value="RCR">RCR · Rest of Central</option>
					<option value="OCR">OCR · Outside Central</option>
				</select>
			</label>

			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Tenure</span>
				<select bind:value={tenure} class="rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="all">All tenures</option>
					<option value="freehold">Freehold</option>
					<option value="leasehold">Leasehold</option>
				</select>
			</label>

			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Min. total txns</span>
				<input type="number" min="0" bind:value={minVolume} class="w-28 rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100" />
			</label>
		</div>
		<p class="mt-3 text-xs text-ghost-500">
			Showing {Math.min(visible.length, kpi.count)} of {kpi.count.toLocaleString()} projects
			{#if kpi.count > ROW_CAP}· refine filters or search to narrow{/if}
		</p>
	</section>

	<!-- Table -->
	<section class="overflow-x-auto rounded-2xl border border-ghost-200/60 bg-white/85 dark:border-ink-600/60 dark:bg-ink-900/60">
		<table class="w-full text-sm">
			<thead class="border-b border-ghost-200/60 text-left text-xs uppercase tracking-wide text-ghost-500 dark:border-ink-600/60">
				<tr>
					<th class="px-3 py-3 font-medium">Compare</th>
					{#each cols as c}
						<th class="px-3 py-3 font-medium">
							<button
								type="button"
								onclick={() => setSort(c.key)}
								title={c.help}
								class="inline-flex items-center gap-1 transition hover:text-ink-900 dark:hover:text-white {sortKey === c.key ? 'text-ink-900 dark:text-white' : ''}"
							>
								{c.label}
								{#if sortKey === c.key}<span class="text-neon-cyan">{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
							</button>
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each visible as e (e.project)}
					{@const sel = selected.has(e.project)}
					<tr class="border-b border-ghost-200/40 transition hover:bg-ghost-50/70 dark:border-ink-600/30 dark:hover:bg-ink-800/40 {sel ? 'bg-neon-cyan/5' : ''}">
						<td class="px-3 py-2.5">
							<input
								type="checkbox"
								checked={sel}
								disabled={!sel && selected.size >= MAX_COMPARE}
								onchange={() => toggle(e.project)}
								class="h-4 w-4 rounded border-ghost-300 accent-[color:var(--color-neon-cyan)]"
								aria-label={`Compare ${e.project}`}
							/>
						</td>
						<td class="px-3 py-2.5">
							<div class="font-medium text-ink-900 dark:text-white">{e.project}</div>
							<div class="text-xs text-ghost-500">
								{e.street} · D{e.district} · <span title={REGION_LABELS[e.region] ?? ''}>{e.region}</span> · {e.tenureClass}
							</div>
						</td>
						<td class="px-3 py-2.5 font-medium text-ink-900 dark:text-ghost-100">{fmtPsf(e.medianPsf)}</td>
						<td class="px-3 py-2.5">
							<div class="flex items-center gap-2">
								<svg viewBox="0 0 80 24" class="h-6 w-20 shrink-0" preserveAspectRatio="none" aria-hidden="true">
									<path
										d={sparklinePath(e.yearly.map((y) => y[1]))}
										fill="none"
										stroke="currentColor"
										stroke-width="1.5"
										class={trendColor(e.trendPct)}
									/>
								</svg>
								<span class="font-medium {trendColor(e.trendPct)}">{fmtTrend(e.trendPct)}</span>
							</div>
						</td>
						<td class="px-3 py-2.5 text-ink-700 dark:text-ghost-200">{fmtPrice(e.medianPrice)}</td>
						<td class="px-3 py-2.5 text-ghost-600 dark:text-ghost-300">{e.medianAreaSqft.toLocaleString()}</td>
						<td class="px-3 py-2.5 text-ghost-600 dark:text-ghost-300">{e.recent12}</td>
						<td class="px-3 py-2.5 text-ghost-500">{e.nAll.toLocaleString()}</td>
					</tr>
				{/each}
				{#if visible.length === 0}
					<tr><td colspan="8" class="px-3 py-8 text-center text-sm text-ghost-500">No projects match these filters.</td></tr>
				{/if}
			</tbody>
		</table>
	</section>

	<!-- Comparison -->
	<section id="compare" class="space-y-5 scroll-mt-28">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<SectionHeading title="Compare" kicker="{selected.size}/{MAX_COMPARE} selected">
				Tick projects above to overlay their price trends and distributions.
			</SectionHeading>
			{#if selected.size > 0}
				<button type="button" onclick={clearSelection} class="rounded-lg border border-ghost-200/70 px-3 py-1.5 text-xs text-ghost-500 transition hover:text-ink-900 dark:border-ink-600/70 dark:hover:text-white">
					Clear selection
				</button>
			{/if}
		</div>

		{#if selected.size === 0}
			<div class="rounded-2xl border border-dashed border-ghost-300/60 bg-white/50 p-8 text-center text-sm text-ghost-500 dark:border-ink-600/60 dark:bg-ink-900/40">
				Nothing selected yet. Tick up to {MAX_COMPARE} projects in the table to compare them here.
			</div>
		{:else}
			<!-- Chart filters -->
			<div class="flex flex-wrap items-center gap-4 rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
				<div class="flex items-center gap-2">
					<span class="text-xs font-medium text-ghost-500">Sale type</span>
					{#each SALE_OPTIONS as code}
						{@const on = sales.has(code)}
						<button type="button" onclick={() => toggleSale(code)} class="rounded-full px-3 py-1 text-xs transition {on ? 'bg-ink-900 text-neon-cyan dark:bg-ink-700' : 'border border-ghost-200/70 text-ghost-500 dark:border-ink-600/70'}">{SALE_LABELS[code]}</button>
					{/each}
				</div>
				<div class="flex items-center gap-2">
					<span class="text-xs font-medium text-ghost-500">Tenure</span>
					<select bind:value={chartTenure} class="rounded-lg border border-ghost-200/70 bg-white px-2 py-1 text-xs dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
						<option value="all">All</option>
						<option value="freehold">Freehold</option>
						<option value="leasehold">Leasehold</option>
					</select>
				</div>
				{#if shardLoading}<span class="text-xs text-ghost-500">loading transactions…</span>{/if}
			</div>

			<!-- Legend -->
			<div class="flex flex-wrap gap-x-4 gap-y-1">
				{#each views as v}
					<span class="inline-flex items-center gap-1.5 text-xs text-ink-700 dark:text-ghost-300">
						<span class="h-2.5 w-2.5 rounded-full" style="background:{v.color}"></span>{v.entry.project}
					</span>
				{/each}
			</div>

			<!-- Stat cards -->
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
				{#each views as v}
					<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60" style="box-shadow: inset 0 0 0 1px {v.color}33">
						<div class="flex items-center gap-2">
							<span class="h-2.5 w-2.5 rounded-full" style="background:{v.color}"></span>
							<h3 class="truncate font-medium text-ink-900 dark:text-white">{v.entry.project}</h3>
						</div>
						{#if v.stats}
							<dl class="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
								<div><dt class="text-xs text-ghost-500">Median PSF</dt><dd class="font-semibold text-ink-900 dark:text-white">{fmtPsf(v.stats.medianPsf)}</dd></div>
								<div><dt class="text-xs text-ghost-500">Median price</dt><dd class="font-semibold text-ink-900 dark:text-white">{fmtPriceFull(v.stats.medianPrice)}</dd></div>
								<div><dt class="text-xs text-ghost-500">PSF range</dt><dd class="text-ink-700 dark:text-ghost-200">{fmtPsf(v.stats.minPsf)}–{fmtPsf(v.stats.maxPsf)}</dd></div>
								<div><dt class="text-xs text-ghost-500">Median size</dt><dd class="text-ink-700 dark:text-ghost-200">{fmtArea(v.stats.medianAreaSqft)}</dd></div>
								<div><dt class="text-xs text-ghost-500">Txns</dt><dd class="text-ink-700 dark:text-ghost-200">{v.stats.count}</dd></div>
								<div><dt class="text-xs text-ghost-500">Trend</dt><dd class="font-medium {trendColor(v.entry.trendPct)}">{fmtTrend(v.entry.trendPct)}</dd></div>
							</dl>
						{:else}
							<p class="mt-3 text-sm text-ghost-500">No transactions match the chart filters.</p>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Charts -->
			<div class="grid gap-4 lg:grid-cols-2">
				<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
					<h3 class="mb-3 text-sm font-medium text-ink-900 dark:text-white">Median PSF over time</h3>
					{#if lineSeries.length}<LineChart series={lineSeries} />{:else}<p class="text-sm text-ghost-500">No data for the current filters.</p>{/if}
				</div>
				<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
					<h3 class="mb-3 text-sm font-medium text-ink-900 dark:text-white">PSF vs size</h3>
					{#if scatter.length}<Scatter series={scatter} />{:else}<p class="text-sm text-ghost-500">No data for the current filters.</p>{/if}
				</div>
			</div>
			<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
				<h3 class="mb-3 text-sm font-medium text-ink-900 dark:text-white">PSF distribution</h3>
				{#if dists.length}<Histogram {dists} />{:else}<p class="text-sm text-ghost-500">No data for the current filters.</p>{/if}
			</div>
		{/if}
	</section>
{/if}
