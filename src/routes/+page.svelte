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
	let ready = $state(false); // URL parsed; safe to start writing it back

	onMount(async () => {
		try {
			entries = await loadIndex();
			applyUrl();
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
			ready = true;
		}
		// Arrived via a shared/“view history” link with a selection → scroll to it.
		if (typeof window !== 'undefined' && selected.size > 0) {
			setTimeout(
				() => document.getElementById('compare')?.scrollIntoView({ behavior: 'smooth' }),
				500
			);
		}
	});

	// Restore analysis from a shared link.
	function applyUrl() {
		const p = new URLSearchParams(location.search);
		const g = (k: string) => p.get(k);
		if (g('cat')) category = g('cat') as Category | 'all';
		if (g('region')) region = g('region') as typeof region;
		if (g('tenure')) tenure = g('tenure') as typeof tenure;
		if (g('q')) search = g('q')!;
		if (g('min') !== null) minVolume = Number(g('min')) || 0;
		if (g('sort')) sortKey = g('sort') as SortKey;
		if (g('dir')) sortDir = g('dir') as 'asc' | 'desc';
		if (g('sel')) selected = new Set(g('sel')!.split('~').filter(Boolean));
		if (g('sale')) sales = new Set(g('sale')!.split('') as SaleCode[]);
		if (g('ct')) chartTenure = g('ct') as typeof chartTenure;
		if (g('tab')) compareTab = g('tab') as typeof compareTab;
	}

	// Keep the URL in sync so any analysis is linkable/shareable.
	$effect(() => {
		if (!ready || typeof window === 'undefined') return;
		const p = new URLSearchParams();
		if (category !== 'condo') p.set('cat', category);
		if (region !== 'all') p.set('region', region);
		if (tenure !== 'all') p.set('tenure', tenure);
		if (search.trim()) p.set('q', search.trim());
		if (minVolume !== 5) p.set('min', String(minVolume));
		if (sortKey !== 'nAll') p.set('sort', sortKey);
		if (sortDir !== 'desc') p.set('dir', sortDir);
		if (selected.size) {
			p.set('sel', [...selected].join('~'));
			const saleCode = [...sales].sort().join('');
			if (saleCode !== '3') p.set('sale', saleCode);
			if (chartTenure !== 'all') p.set('ct', chartTenure);
			if (compareTab !== 'trend') p.set('tab', compareTab);
		}
		const qs = p.toString();
		history.replaceState(history.state, '', qs ? `?${qs}` : location.pathname);
	});

	// ── Filters ───────────────────────────────────────────────────────────────
	let search = $state('');
	let category = $state<Category | 'all'>('condo');
	let region = $state<'all' | 'CCR' | 'RCR' | 'OCR'>('all');
	let tenure = $state<'all' | 'freehold' | 'leasehold'>('all');
	let minVolume = $state(5); // ignore thinly-traded projects by default

	const ROW_CAP = 120;

	type SortKey =
		| 'medianPsf'
		| 'trendPct'
		| 'repeatAnnReturn'
		| 'grossYield'
		| 'medianPrice'
		| 'medianAreaSqft'
		| 'txnsPerYear'
		| 'recent12'
		| 'nAll'
		| 'project';
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

	// One-click: select a project, jump to its full transaction history.
	function viewHistory(name: string) {
		const next = new Set(selected);
		if (!next.has(name) && next.size < MAX_COMPARE) next.add(name);
		selected = next;
		compareTab = 'txns';
		if (typeof document !== 'undefined') {
			setTimeout(
				() => document.getElementById('compare')?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
				60
			);
		}
	}

	let copied = $state(false);
	let manualUrl = $state(''); // shown only if every copy path fails (e.g. http context)
	let canShare = $state(false);
	onMount(() => {
		canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';
	});

	function flashCopied() {
		copied = true;
		setTimeout(() => (copied = false), 1500);
	}

	async function shareLink() {
		const url = location.href;
		manualUrl = '';
		// 1) Native share sheet — best on mobile.
		if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
			try {
				await navigator.share({ title: 'SG Property Analytics', url });
				return;
			} catch (e) {
				if (e instanceof DOMException && e.name === 'AbortError') return; // user cancelled
				// otherwise fall through to copy
			}
		}
		// 2) Async Clipboard API (secure contexts).
		if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
			try {
				await navigator.clipboard.writeText(url);
				flashCopied();
				return;
			} catch {
				/* fall through */
			}
		}
		// 3) Legacy execCommand — works in insecure (http) contexts and old mobile.
		try {
			const ta = document.createElement('textarea');
			ta.value = url;
			ta.style.position = 'fixed';
			ta.style.top = '0';
			ta.style.opacity = '0';
			document.body.appendChild(ta);
			ta.focus();
			ta.select();
			const ok = document.execCommand('copy');
			document.body.removeChild(ta);
			if (ok) {
				flashCopied();
				return;
			}
		} catch {
			/* fall through */
		}
		// 4) Last resort: reveal the link for manual copy.
		manualUrl = url;
	}

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

	let compareTab = $state<'trend' | 'scatter' | 'dist' | 'detail' | 'txns'>('trend');
	const COMPARE_TABS = [
		{ id: 'trend', label: 'PSF over time' },
		{ id: 'scatter', label: 'PSF vs size' },
		{ id: 'dist', label: 'Distribution' },
		{ id: 'detail', label: 'Deep dive' },
		{ id: 'txns', label: 'All transactions' }
	] as const;

	const monthsAbbr = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
	const fmtMonth = (d: string) => {
		const [y, m] = d.split('-');
		return `${monthsAbbr[Number(m) - 1] ?? m} ${y}`;
	};

	const views = $derived.by(() => {
		return selectedEntries
			.map((e, i) => {
				const sp = shardMap.get(e.project);
				if (!sp) return null;
				const txns = filterTxns(sp.transactions, chartFilters);
				return {
					entry: e,
					color: colorFor(i),
					shard: sp,
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
		{
			key: 'repeatAnnReturn',
			label: 'Return p.a.',
			help: 'Median annualised return on approximate repeat sales (same size + floor band)'
		},
		{ key: 'grossYield', label: 'Gross yield', help: 'Latest median rent PSF × 12 ÷ sale median PSF' },
		{ key: 'medianPrice', label: 'Median price' },
		{ key: 'medianAreaSqft', label: 'Median size' },
		{ key: 'txnsPerYear', label: 'Sold/yr', help: 'Average transactions per year (liquidity)' },
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
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:flex lg:flex-wrap lg:items-end">
			<label class="col-span-2 sm:col-span-3 lg:min-w-[220px] lg:flex-1">
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
				<select bind:value={category} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-auto dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="condo">Condo / Apartment</option>
					<option value="ec">Executive Condo</option>
					<option value="landed">Landed</option>
					<option value="all">All types</option>
				</select>
			</label>

			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Region</span>
				<select bind:value={region} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-auto dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="all">All regions</option>
					<option value="CCR">CCR · Core Central</option>
					<option value="RCR">RCR · Rest of Central</option>
					<option value="OCR">OCR · Outside Central</option>
				</select>
			</label>

			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Tenure</span>
				<select bind:value={tenure} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-auto dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="all">All tenures</option>
					<option value="freehold">Freehold</option>
					<option value="leasehold">Leasehold</option>
				</select>
			</label>

			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Min. total txns</span>
				<input type="number" min="0" bind:value={minVolume} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-28 dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100" />
			</label>
		</div>
		<div class="mt-3 flex flex-wrap items-center justify-between gap-2">
			<p class="text-xs text-ghost-500">
				Showing {Math.min(visible.length, kpi.count)} of {kpi.count.toLocaleString()} projects
				{#if kpi.count > ROW_CAP}· refine filters or search to narrow{/if}
			</p>
			<button
				type="button"
				onclick={shareLink}
				class="rounded-lg border border-ghost-200/70 px-3 py-1.5 text-xs text-ghost-600 transition hover:border-neon-cyan/50 hover:text-ink-900 dark:border-ink-600/70 dark:text-ghost-300 dark:hover:text-white"
				title="Share a link to this exact view (filters + selection)"
			>
				{copied ? '✓ Link copied' : canShare ? '🔗 Share this view' : '🔗 Copy share link'}
			</button>
		</div>
		{#if manualUrl}
			<div class="mt-2 flex items-center gap-2">
				<input
					readonly
					value={manualUrl}
					onfocus={(e) => e.currentTarget.select()}
					class="w-full rounded-lg border border-ghost-200/70 bg-ghost-50 px-3 py-1.5 text-xs text-ink-900 dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100"
					aria-label="Shareable link — tap to select and copy"
				/>
			</div>
			<p class="mt-1 text-[11px] text-ghost-500">Tap the link above to select, then copy.</p>
		{/if}
	</section>

	<!-- Cards (mobile/tablet) -->
	<section class="space-y-3 lg:hidden">
		<div class="flex items-center gap-2">
			<label class="flex flex-1 items-center gap-2 rounded-lg border border-ghost-200/70 bg-white px-3 py-2 dark:border-ink-600/70 dark:bg-ink-950/70">
				<span class="text-xs text-ghost-500">Sort</span>
				<select bind:value={sortKey} class="flex-1 bg-transparent text-sm text-ink-900 dark:text-ghost-100">
					{#each cols.filter((c) => c.key !== 'project') as c}
						<option value={c.key}>{c.label}</option>
					{/each}
				</select>
			</label>
			<button
				type="button"
				onclick={() => (sortDir = sortDir === 'asc' ? 'desc' : 'asc')}
				class="rounded-lg border border-ghost-200/70 px-3 py-2 text-sm text-ghost-600 dark:border-ink-600/70 dark:text-ghost-300"
			>{sortDir === 'asc' ? '▲ Asc' : '▼ Desc'}</button>
		</div>

		<div class="max-h-[64vh] space-y-2 overflow-auto">
			{#each visible as e (e.project)}
				{@const sel = selected.has(e.project)}
				<button
					type="button"
					onclick={() => toggle(e.project)}
					disabled={!sel && selected.size >= MAX_COMPARE}
					class="w-full rounded-xl border p-3 text-left transition disabled:opacity-40 {sel
						? 'border-neon-cyan/60 bg-neon-cyan/5'
						: 'border-ghost-200/60 bg-white/85 dark:border-ink-600/60 dark:bg-ink-900/60'}"
				>
					<div class="flex items-start justify-between gap-2">
						<div class="min-w-0">
							<div class="truncate font-medium text-ink-900 dark:text-white">{e.project}</div>
							<div class="truncate text-xs text-ghost-500">{e.street} · D{e.district} · {e.region} · {e.tenureClass}</div>
						</div>
						<span class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] {sel ? 'border-neon-cyan text-neon-cyan' : 'border-ghost-300 text-ghost-500 dark:border-ink-500'}">{sel ? '✓ added' : 'compare'}</span>
					</div>
					<div class="mt-2.5 grid grid-cols-3 gap-x-3 gap-y-2 text-xs">
						<div><div class="text-ghost-500">Median PSF</div><div class="font-semibold text-ink-900 dark:text-ghost-100">{fmtPsf(e.medianPsf)}</div></div>
						<div><div class="text-ghost-500">Trend</div><div class="font-semibold {trendColor(e.trendPct)}">{fmtTrend(e.trendPct)}</div></div>
						<div><div class="text-ghost-500">Return p.a.</div><div class="font-semibold {trendColor(e.repeatAnnReturn)}">{fmtTrend(e.repeatAnnReturn)}</div></div>
						<div><div class="text-ghost-500">Gross yield</div><div class="font-semibold text-ink-900 dark:text-ghost-100">{e.grossYield != null ? `${e.grossYield.toFixed(1)}%` : '—'}</div></div>
						<div><div class="text-ghost-500">Median price</div><div class="font-semibold text-ink-900 dark:text-ghost-100">{fmtPrice(e.medianPrice)}</div></div>
						<div><div class="text-ghost-500">Sold/yr</div><div class="font-semibold text-ink-900 dark:text-ghost-100">{e.txnsPerYear}</div></div>
					</div>
				</button>
			{/each}
			{#if visible.length === 0}
				<p class="rounded-xl border border-ghost-200/60 p-6 text-center text-sm text-ghost-500 dark:border-ink-600/60">No projects match these filters.</p>
			{/if}
		</div>
	</section>

	<!-- Table (desktop): fixed-height, internal scroll, sticky header -->
	<section class="hidden max-h-[58vh] overflow-auto rounded-2xl border border-ghost-200/60 bg-white/85 lg:block dark:border-ink-600/60 dark:bg-ink-900/60">
		<table class="w-full text-sm">
			<thead class="sticky top-0 z-10 border-b border-ghost-200/60 bg-white/95 text-left text-xs uppercase tracking-wide text-ghost-500 backdrop-blur dark:border-ink-600/60 dark:bg-ink-900/95">
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
							<button
								type="button"
								onclick={() => viewHistory(e.project)}
								class="text-left font-medium text-ink-900 transition hover:text-neon-cyan dark:text-white dark:hover:text-neon-cyan"
								title="View full transaction history"
							>{e.project}</button>
							<div class="text-xs text-ghost-500">
								{e.street} · D{e.district} · <span title={REGION_LABELS[e.region] ?? ''}>{e.region}</span> · {e.tenureClass}
							</div>
						</td>
						<td class="px-3 py-2.5 font-medium text-ink-900 dark:text-ghost-100">{fmtPsf(e.medianPsf)}</td>
						<td class="px-3 py-2.5">
							<div class="flex items-center gap-2">
								<svg viewBox="0 0 80 24" class="h-6 w-16 shrink-0" preserveAspectRatio="none" aria-hidden="true">
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
						<td class="px-3 py-2.5 font-medium {trendColor(e.repeatAnnReturn)}" title={e.repeatPairs ? `${e.repeatPairs} repeat pairs` : 'no repeat sales found'}>{fmtTrend(e.repeatAnnReturn)}</td>
						<td class="px-3 py-2.5 text-ink-700 dark:text-ghost-200">{e.grossYield != null ? `${e.grossYield.toFixed(1)}%` : '—'}</td>
						<td class="px-3 py-2.5 text-ink-700 dark:text-ghost-200">{fmtPrice(e.medianPrice)}</td>
						<td class="px-3 py-2.5 text-ghost-600 dark:text-ghost-300">{e.medianAreaSqft.toLocaleString()}</td>
						<td class="px-3 py-2.5 text-ghost-600 dark:text-ghost-300">{e.txnsPerYear}</td>
						<td class="px-3 py-2.5 text-ghost-500">{e.nAll.toLocaleString()}</td>
					</tr>
				{/each}
				{#if visible.length === 0}
					<tr><td colspan="10" class="px-3 py-8 text-center text-sm text-ghost-500">No projects match these filters.</td></tr>
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
								<div><dt class="text-xs text-ghost-500">Trend (5yr)</dt><dd class="font-medium {trendColor(v.entry.trendPct)}">{fmtTrend(v.entry.trendPct)}</dd></div>
								<div><dt class="text-xs text-ghost-500">Return p.a.</dt><dd class="font-medium {trendColor(v.entry.repeatAnnReturn)}">{fmtTrend(v.entry.repeatAnnReturn)}</dd></div>
							</dl>
						{:else}
							<p class="mt-3 text-sm text-ghost-500">No transactions match the chart filters.</p>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Charts (tabbed to keep the page compact) -->
			<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
				<div class="mb-4 inline-flex flex-wrap rounded-full border border-ghost-200/70 bg-ghost-50 p-1 text-xs dark:border-ink-600/60 dark:bg-ink-950/60">
					{#each COMPARE_TABS as t}
						<button
							type="button"
							onclick={() => (compareTab = t.id)}
							class="rounded-full px-3 py-1.5 transition {compareTab === t.id ? 'bg-ink-900 text-neon-cyan dark:bg-ink-700' : 'text-ghost-500 hover:text-ink-900 dark:hover:text-white'}"
						>{t.label}</button>
					{/each}
				</div>

				{#if compareTab === 'trend'}
					{#if lineSeries.length}<LineChart series={lineSeries} />{:else}<p class="text-sm text-ghost-500">No data for the current filters.</p>{/if}
				{:else if compareTab === 'scatter'}
					{#if scatter.length}<Scatter series={scatter} />{:else}<p class="text-sm text-ghost-500">No data for the current filters.</p>{/if}
				{:else if compareTab === 'dist'}
					{#if dists.length}<Histogram {dists} />{:else}<p class="text-sm text-ghost-500">No data for the current filters.</p>{/if}
				{:else if compareTab === 'txns'}
					<!-- Full per-project transaction history (from the district shard) -->
					<p class="mb-3 text-xs text-ghost-500">
						Every matching transaction over the 60-month window (newest first), honouring the sale-type
						and tenure filters above. Caveats are month-dated.
					</p>
					<div class="grid gap-4 {views.length > 1 ? 'md:grid-cols-2' : ''}">
						{#each views as v}
							<div class="rounded-xl border border-ghost-200/60 dark:border-ink-600/50" style="box-shadow: inset 0 0 0 1px {v.color}22">
								<div class="flex items-center gap-2 border-b border-ghost-200/60 px-3 py-2 dark:border-ink-600/50">
									<span class="h-2.5 w-2.5 rounded-full" style="background:{v.color}"></span>
									<h4 class="truncate text-sm font-semibold text-ink-900 dark:text-white">{v.entry.project}</h4>
									<span class="ml-auto text-xs text-ghost-500">{v.txns.length} txns</span>
								</div>
								{#if v.txns.length}
									<div class="max-h-[50vh] overflow-auto">
										<table class="w-full text-xs">
											<thead class="sticky top-0 bg-white/95 text-left text-[10px] uppercase tracking-wide text-ghost-500 dark:bg-ink-900/95">
												<tr>
													<th class="px-3 py-2 font-medium">Month</th>
													<th class="px-3 py-2 font-medium">Price</th>
													<th class="px-3 py-2 font-medium">PSF</th>
													<th class="px-3 py-2 font-medium">Size</th>
													<th class="px-3 py-2 font-medium">Floor</th>
													<th class="px-3 py-2 font-medium">Sale</th>
												</tr>
											</thead>
											<tbody>
												{#each [...v.txns].reverse() as t, i (i)}
													<tr class="border-t border-ghost-200/40 dark:border-ink-600/30">
														<td class="whitespace-nowrap px-3 py-1.5 text-ghost-500">{fmtMonth(t.date)}</td>
														<td class="whitespace-nowrap px-3 py-1.5 font-medium text-ink-900 dark:text-ghost-100">{fmtPriceFull(t.price)}</td>
														<td class="whitespace-nowrap px-3 py-1.5 text-ink-700 dark:text-ghost-200">{fmtPsf(t.psf)}</td>
														<td class="whitespace-nowrap px-3 py-1.5 text-ghost-600 dark:text-ghost-300">{t.areaSqft.toLocaleString()} sqft</td>
														<td class="whitespace-nowrap px-3 py-1.5 text-ghost-600 dark:text-ghost-300">{t.floorRange || '—'}</td>
														<td class="whitespace-nowrap px-3 py-1.5 text-ghost-600 dark:text-ghost-300">{SALE_LABELS[t.typeOfSale as SaleCode] ?? '—'}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									</div>
								{:else}
									<p class="px-3 py-4 text-sm text-ghost-500">No transactions match the current filters.</p>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<!-- Deep dive: floor & size premium, repeat-sale returns, uplift -->
					<div class="grid gap-4 md:grid-cols-2">
						{#each views as v}
							<div class="rounded-xl border border-ghost-200/60 p-4 dark:border-ink-600/50" style="box-shadow: inset 0 0 0 1px {v.color}22">
								<div class="flex items-center gap-2">
									<span class="h-2.5 w-2.5 rounded-full" style="background:{v.color}"></span>
									<h4 class="truncate text-sm font-semibold text-ink-900 dark:text-white">{v.entry.project}</h4>
								</div>

								<div class="mt-3 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
									<div class="rounded-lg bg-ghost-50 p-2 dark:bg-ink-950/60">
										<div class="text-ghost-500">Return p.a.</div>
										<div class="mt-0.5 font-semibold {trendColor(v.shard.repeatStats.medianAnnReturnPct)}">{fmtTrend(v.shard.repeatStats.medianAnnReturnPct)}</div>
										<div class="text-[10px] text-ghost-500">{v.shard.repeatStats.pairs} pairs</div>
									</div>
									<div class="rounded-lg bg-ghost-50 p-2 dark:bg-ink-950/60">
										<div class="text-ghost-500">Gross yield</div>
										<div class="mt-0.5 font-semibold text-ink-900 dark:text-white">{v.shard.rental.grossYield != null ? `${v.shard.rental.grossYield.toFixed(1)}%` : '—'}</div>
										<div class="text-[10px] text-ghost-500">{v.shard.rental.rentPsf != null ? `$${v.shard.rental.rentPsf}/sqft/mo` : 'no rent data'}</div>
									</div>
									<div class="rounded-lg bg-ghost-50 p-2 dark:bg-ink-950/60">
										<div class="text-ghost-500">New→resale</div>
										<div class="mt-0.5 font-semibold {trendColor(v.shard.uplift.upliftPct)}">{fmtTrend(v.shard.uplift.upliftPct)}</div>
										<div class="text-[10px] text-ghost-500">{v.shard.uplift.newCount} new sales</div>
									</div>
									<div class="rounded-lg bg-ghost-50 p-2 dark:bg-ink-950/60">
										<div class="text-ghost-500">Velocity</div>
										<div class="mt-0.5 font-semibold text-ink-900 dark:text-white">{v.entry.txnsPerYear}/yr</div>
										<div class="text-[10px] text-ghost-500">{v.shard.repeatStats.medianHoldYears ?? '—'}y hold</div>
									</div>
								</div>

								<!-- Floor premium -->
								{#if v.shard.byFloor.length > 1}
									<p class="mt-3 text-xs font-medium text-ghost-500">PSF by floor band</p>
									<div class="mt-1 space-y-1">
										{#each v.shard.byFloor as f}
											<div class="flex items-center gap-2 text-xs">
												<span class="w-14 shrink-0 text-ghost-500">{f.floorRange}</span>
												<div class="h-3 flex-1 overflow-hidden rounded bg-ghost-100 dark:bg-ink-800">
													<div class="h-full rounded" style="width:{Math.min(100, (f.medianPsf / Math.max(...v.shard.byFloor.map((x) => x.medianPsf))) * 100)}%; background:{v.color}"></div>
												</div>
												<span class="w-16 shrink-0 text-right text-ink-700 dark:text-ghost-200">{fmtPsf(f.medianPsf)}</span>
												<span class="w-12 shrink-0 text-right {trendColor(f.premiumPct)}">{fmtTrend(f.premiumPct)}</span>
											</div>
										{/each}
									</div>
								{/if}

								<!-- Size premium -->
								{#if v.shard.bySize.length > 1}
									<p class="mt-3 text-xs font-medium text-ghost-500">PSF by size</p>
									<div class="mt-1 space-y-1">
										{#each v.shard.bySize as s}
											<div class="flex items-center gap-2 text-xs">
												<span class="w-20 shrink-0 text-ghost-500">{s.bucket}</span>
												<div class="h-3 flex-1 overflow-hidden rounded bg-ghost-100 dark:bg-ink-800">
													<div class="h-full rounded" style="width:{Math.min(100, (s.medianPsf / Math.max(...v.shard.bySize.map((x) => x.medianPsf))) * 100)}%; background:{v.color}"></div>
												</div>
												<span class="w-16 shrink-0 text-right text-ink-700 dark:text-ghost-200">{fmtPsf(s.medianPsf)}</span>
												<span class="w-12 shrink-0 text-right {trendColor(s.premiumPct)}">{fmtTrend(s.premiumPct)}</span>
											</div>
										{/each}
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</section>
{/if}
