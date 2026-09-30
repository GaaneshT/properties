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
		type IndexEntry,
		type ShardProject,
		type Category,
		type SaleCode,
		type Filters,
		type Series,
		type Dist,
		type ScatterSeries
	} from '$lib/data';
	import { fmtPsf, fmtPrice, fmtPriceFull, fmtTrend, sparklinePath } from '$lib/format';
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
			setTimeout(scrollToCompare, 500);
		}
	});

	function scrollToCompare() {
		const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
		document
			.getElementById('compare')
			?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' });
	}

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
			if (q && !`${e.project} ${e.street}`.toLowerCase().includes(q)) return false;
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
		if (typeof document !== 'undefined') setTimeout(scrollToCompare, 60);
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

	const shareLabel = $derived(copied ? 'Link copied' : canShare ? 'Share this view' : 'Copy share link');

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

	// Up is Field Green, down is Red Ochre, flat stays in Margin Grey.
	const trendColor = (t: number | null) =>
		t === null ? 'text-ghost-500' : t > 1 ? 'text-neon-green' : t < -1 ? 'text-neon-rose' : 'text-ghost-600';

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

	const ariaSort = (k: SortKey) =>
		sortKey === k ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none';

	// Shared control styles: the system's 3px field, panel and chip.
	const panel = 'rounded-[4px] border border-ghost-200 bg-ghost-50';
	const field = 'w-full rounded-[3px] border border-ghost-300 bg-ghost-50 px-3 py-2 text-sm text-ink-900';
	const fieldLabel = 'mb-1 block text-[12.5px] font-medium text-ghost-600';
	const chip = 'rounded-[3px] border px-3 py-1 text-[12.5px] font-medium transition';
	const chipOn = 'border-neon-cyan bg-neon-cyan text-ghost-50';
	const chipOff = 'border-ghost-300 text-ink-700 hover:border-neon-cyan hover:text-neon-cyan';
	const th = 'border-b border-ghost-300 px-3 py-3 align-bottom';
	const thBtn = 'inline-flex items-center gap-1 font-display text-[13px] leading-tight font-semibold transition hover:text-neon-cyan';
	const td = 'border-b border-ghost-200 px-3 py-2.5';
</script>

<svelte:head>
	<title>SG Property Analytics · properties.gaanesh.com</title>
</svelte:head>

<div class="phead">
	<h1>Singapore property analytics</h1>
	<p>
		Browse, filter and compare private residential projects on median PSF, price trend, size and
		transaction volume. Pick a few to compare side by side.
	</p>
</div>

<div class="caveat">
	<p>
		<b>Figures are derived, not republished.</b> They are computed from URA caveat data over a 60-month
		rolling window, resale-weighted by default. Caveat data covers ~80–90% of resale/sub-sale volume, and
		repeat-sale returns are an approximation (<a href="#method" class="lnk">how they're computed</a>).
	</p>
</div>

{#if loading}
	<p class="{panel} mt-10 p-8 text-center text-[15px] text-ghost-600" role="status">Loading project data…</p>
{:else if loadError}
	<div class="mt-10 rounded-[3px] border border-l-[3px] border-ghost-200 border-l-neon-rose bg-ghost-50 px-[22px] py-[18px]" role="alert">
		<p class="text-[15.5px] leading-relaxed text-ink-700">
			<b class="font-semibold text-neon-rose">Couldn't load the project data.</b>
			{loadError}. Reload the page to try again.
		</p>
	</div>
{:else}
	<!-- Summary of the filtered set -->
	<dl class="kpis mt-10">
		<div><dt>Projects in view</dt><dd>{kpi.count.toLocaleString()}</dd></div>
		<div><dt>Median PSF</dt><dd>{fmtPsf(kpi.medianPsf)}</dd></div>
		<div><dt>Median price</dt><dd>{fmtPrice(kpi.medianPrice)}</dd></div>
		<div><dt>Median trend</dt><dd>{fmtTrend(Number.isFinite(kpi.medianTrend) ? kpi.medianTrend : null)}</dd></div>
	</dl>

	<!-- Filters -->
	<section class="{panel} mt-6 p-4 sm:p-5" aria-label="Filters">
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:flex lg:flex-wrap lg:items-end">
			<label class="col-span-2 sm:col-span-3 lg:min-w-[220px] lg:flex-1">
				<span class={fieldLabel}>Search project or street</span>
				<input type="search" bind:value={search} placeholder="e.g. Reflections, Clematis…" class={field} />
			</label>

			<label class="lg:shrink-0">
				<span class={fieldLabel}>Type</span>
				<select bind:value={category} class="{field} pr-9 lg:w-auto">
					<option value="condo">Condo / Apartment</option>
					<option value="ec">Executive Condo</option>
					<option value="landed">Landed</option>
					<option value="all">All types</option>
				</select>
			</label>

			<label class="lg:shrink-0">
				<span class={fieldLabel}>Region</span>
				<select bind:value={region} class="{field} pr-9 lg:w-auto">
					<option value="all">All regions</option>
					<option value="CCR">CCR · Core Central</option>
					<option value="RCR">RCR · Rest of Central</option>
					<option value="OCR">OCR · Outside Central</option>
				</select>
			</label>

			<label class="lg:shrink-0">
				<span class={fieldLabel}>Tenure</span>
				<select bind:value={tenure} class="{field} pr-9 lg:w-auto">
					<option value="all">All tenures</option>
					<option value="freehold">Freehold</option>
					<option value="leasehold">Leasehold</option>
				</select>
			</label>

			<label class="lg:shrink-0">
				<span class={fieldLabel}>Min. total txns</span>
				<input type="number" min="0" bind:value={minVolume} class="{field} lg:w-28" />
			</label>
		</div>
		<div class="mt-4 flex flex-wrap items-center justify-between gap-3">
			<p class="tabular text-[13px] text-ghost-600">
				Showing {Math.min(visible.length, kpi.count)} of {kpi.count.toLocaleString()} projects
				{#if kpi.count > ROW_CAP}· refine filters or search to narrow{/if}
			</p>
			<button
				type="button"
				onclick={shareLink}
				class="{chip} {copied ? chipOn : chipOff}"
				title="Share a link to this exact view (filters + selection)">{shareLabel}</button
			>
			<span class="sr-only" aria-live="polite">{copied ? 'Link copied to the clipboard' : ''}</span>
		</div>
		{#if manualUrl}
			<label class="mt-3 block">
				<span class={fieldLabel}>Shareable link. Tap to select, then copy.</span>
				<input readonly value={manualUrl} onfocus={(e) => e.currentTarget.select()} class="{field} py-1.5 text-[13px]" />
			</label>
		{/if}
	</section>

	<!-- Project list (mobile/tablet) -->
	<section class="mt-5 lg:hidden" aria-label="Projects">
		<div class="flex items-center gap-2">
			<label class="flex min-w-0 flex-1 items-center gap-2">
				<span class="shrink-0 text-[12.5px] font-medium text-ghost-600">Sort by</span>
				<select bind:value={sortKey} class="{field} min-w-0 flex-1 py-1.5 pr-9">
					{#each cols.filter((c) => c.key !== 'project') as c}
						<option value={c.key}>{c.label}</option>
					{/each}
				</select>
			</label>
			<button
				type="button"
				onclick={() => (sortDir = sortDir === 'asc' ? 'desc' : 'asc')}
				class="{chip} {chipOff} shrink-0 py-1.5"
				aria-label="Sort direction: {sortDir === 'asc' ? 'ascending' : 'descending'}"
				>{sortDir === 'asc' ? '↑ Asc' : '↓ Desc'}</button
			>
		</div>

		<ul class="scroller {panel} mt-3 max-h-[64vh] overflow-auto">
			{#each visible as e (e.project)}
				{@const sel = selected.has(e.project)}
				<li class="border-b border-ghost-200 last:border-b-0">
					<button
						type="button"
						onclick={() => toggle(e.project)}
						disabled={!sel && selected.size >= MAX_COMPARE}
						aria-pressed={sel}
						class="block w-full px-4 py-3.5 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-45 {sel
							? 'bg-neon-cyan/[0.07]'
							: 'hover:bg-neon-cyan/[0.045]'}"
					>
						<span class="flex items-start justify-between gap-3">
							<span class="min-w-0">
								<span class="block truncate font-medium text-ink-900">{e.project}</span>
								<span class="block truncate text-[12.5px] text-ghost-600"
									>{e.street} · D{e.district} · {e.region} · {e.tenureClass}</span
								>
							</span>
							<span
								class="shrink-0 rounded-[3px] border px-2 py-0.5 text-[12px] font-medium {sel
									? 'border-neon-cyan bg-neon-cyan text-ghost-50'
									: 'border-ghost-300 text-ink-700'}">{sel ? 'Added' : 'Compare'}</span
							>
						</span>
						<!-- Three headline figures; the rest live in Compare once selected. -->
						<span class="tabular mt-2.5 grid grid-cols-3 gap-x-3 text-[12.5px]">
							<span><span class="block text-ghost-600">Median PSF</span><span class="block font-semibold text-ink-900">{fmtPsf(e.medianPsf)}</span></span>
							<span><span class="block text-ghost-600">Trend</span><span class="block font-semibold {trendColor(e.trendPct)}">{fmtTrend(e.trendPct)}</span></span>
							<span><span class="block text-ghost-600">Median price</span><span class="block font-semibold text-ink-900">{fmtPrice(e.medianPrice)}</span></span>
						</span>
					</button>
				</li>
			{/each}
			{#if visible.length === 0}
				<li class="p-6 text-center text-[15px] text-ghost-600">No projects match these filters.</li>
			{/if}
		</ul>
	</section>

	<!-- Table (desktop): fixed-height, internal scroll, sticky header -->
	<section class="scroller {panel} mt-5 hidden max-h-[58vh] overflow-auto lg:block" aria-label="Projects">
		<table class="w-full border-separate border-spacing-0 text-sm">
			<thead class="sticky top-0 z-10 bg-ghost-50 text-left">
				<tr>
					<th scope="col" class="{th} font-display text-[13px] font-semibold text-ink-700">Compare</th>
					{#each cols as c}
						<th scope="col" aria-sort={ariaSort(c.key)} class="{th} {c.key === 'project' ? '' : 'text-right'}">
							<button
								type="button"
								onclick={() => setSort(c.key)}
								title={c.help}
								class="{thBtn} {sortKey === c.key ? 'text-ink-900' : 'text-ink-700'}"
							>
								{c.label}
								{#if sortKey === c.key}<span class="text-neon-cyan" aria-hidden="true">{sortDir === 'asc' ? '↑' : '↓'}</span>{/if}
							</button>
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each visible as e (e.project)}
					{@const sel = selected.has(e.project)}
					<tr class="transition-colors {sel ? 'bg-neon-cyan/[0.07]' : 'hover:bg-neon-cyan/[0.045]'}">
						<td class={td}>
							<input
								type="checkbox"
								checked={sel}
								disabled={!sel && selected.size >= MAX_COMPARE}
								onchange={() => toggle(e.project)}
								class="h-4 w-4"
								aria-label={`Compare ${e.project}`}
							/>
						</td>
						<td class={td}>
							<button
								type="button"
								onclick={() => viewHistory(e.project)}
								class="text-left font-medium text-ink-900 transition hover:text-neon-cyan"
								title="View full transaction history">{e.project}</button
							>
							<div class="text-[12.5px] text-ghost-600">
								{e.street} · D{e.district} · <span title={REGION_LABELS[e.region] ?? ''}>{e.region}</span> · {e.tenureClass}
							</div>
						</td>
						<td class="{td} text-right font-medium text-ink-900">{fmtPsf(e.medianPsf)}</td>
						<td class={td}>
							<span class="flex items-center justify-end gap-2">
								<svg viewBox="0 0 80 24" class="h-6 w-16 shrink-0 {trendColor(e.trendPct)}" preserveAspectRatio="none" aria-hidden="true">
									<path d={sparklinePath(e.yearly.map((y) => y[1]))} fill="none" stroke="currentColor" stroke-width="1.5" />
								</svg>
								<span class="min-w-[3.25rem] text-right font-medium {trendColor(e.trendPct)}">{fmtTrend(e.trendPct)}</span>
							</span>
						</td>
						<td
							class="{td} text-right font-medium {trendColor(e.repeatAnnReturn)}"
							title={e.repeatPairs ? `${e.repeatPairs} repeat pairs` : 'no repeat sales found'}>{fmtTrend(e.repeatAnnReturn)}</td
						>
						<td class="{td} text-right text-ink-700">{e.grossYield != null ? `${e.grossYield.toFixed(1)}%` : '—'}</td>
						<td class="{td} text-right text-ink-700">{fmtPrice(e.medianPrice)}</td>
						<td class="{td} text-right text-ghost-600">{e.medianAreaSqft.toLocaleString()}</td>
						<td class="{td} text-right text-ghost-600">{e.txnsPerYear}</td>
						<td class="{td} text-right text-ghost-600">{e.nAll.toLocaleString()}</td>
					</tr>
				{/each}
				{#if visible.length === 0}
					<tr><td colspan="10" class="px-3 py-8 text-center text-[15px] text-ghost-600">No projects match these filters.</td></tr>
				{/if}
			</tbody>
		</table>
	</section>

	<!-- Comparison -->
	<section id="compare" class="mt-[66px] scroll-mt-8" aria-labelledby="compare-h">
		<SectionHeading title="Compare" id="compare-h" count="{selected.size} of {MAX_COMPARE} selected">
			{#snippet actions()}
				{#if selected.size > 0}
					<button type="button" onclick={clearSelection} class="{chip} {chipOff}">Clear selection</button>
				{/if}
			{/snippet}
			Select projects above to overlay their price trends and distributions.
		</SectionHeading>

		{#if selected.size === 0}
			<p class="{panel} mt-5 px-[22px] py-[18px] text-[15px] text-ink-700">
				Nothing selected yet. Select up to {MAX_COMPARE} projects above to compare them here.
			</p>
		{:else}
			<!-- Chart filters -->
			<div class="{panel} mt-5 flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3.5">
				<div class="flex flex-wrap items-center gap-2" role="group" aria-label="Sale type">
					<span class="text-[12.5px] font-medium text-ghost-600">Sale type</span>
					{#each SALE_OPTIONS as code}
						{@const on = sales.has(code)}
						<button type="button" onclick={() => toggleSale(code)} aria-pressed={on} class="{chip} {on ? chipOn : chipOff}"
							>{SALE_LABELS[code]}</button
						>
					{/each}
				</div>
				<label class="flex items-center gap-2">
					<span class="text-[12.5px] font-medium text-ghost-600">Tenure</span>
					<select bind:value={chartTenure} class="rounded-[3px] border border-ghost-300 bg-ghost-50 py-1 pr-8 pl-2 text-[13px] text-ink-900">
						<option value="all">All</option>
						<option value="freehold">Freehold</option>
						<option value="leasehold">Leasehold</option>
					</select>
				</label>
				{#if shardLoading}<span class="text-[12.5px] text-ghost-600" role="status">Loading transactions…</span>{/if}
			</div>

			<!-- Legend, carrying each project's medians under the chart filters -->
			<ul class="tabular mt-4 flex flex-wrap gap-x-6 gap-y-1.5" aria-label="Selected projects">
				{#each views as v}
					<li class="inline-flex items-center gap-2 text-[13px]">
						<span class="h-2.5 w-2.5 shrink-0 rounded-full" style="background:{v.color}" aria-hidden="true"></span>
						<span class="font-medium text-ink-900">{v.entry.project}</span>
						{#if v.stats}
							<span class="text-ghost-600">{fmtPsf(v.stats.medianPsf)} psf · {fmtPrice(v.stats.medianPrice)}</span>
						{:else}
							<span class="text-ghost-600">no sales match the filters</span>
						{/if}
					</li>
				{/each}
			</ul>

			<!-- Charts (tabbed to keep the page compact) -->
			<div class="{panel} mt-4 p-4 sm:p-5">
				<div class="mb-5 flex flex-wrap gap-1.5" role="group" aria-label="Chart view">
					{#each COMPARE_TABS as t}
						<button
							type="button"
							onclick={() => (compareTab = t.id)}
							aria-pressed={compareTab === t.id}
							class="{chip} {compareTab === t.id ? chipOn : chipOff}">{t.label}</button
						>
					{/each}
				</div>

				{#if compareTab === 'trend'}
					{#if lineSeries.length}<LineChart series={lineSeries} />{:else}<p class="text-[15px] text-ghost-600">No data for the current filters.</p>{/if}
				{:else if compareTab === 'scatter'}
					{#if scatter.length}<Scatter series={scatter} />{:else}<p class="text-[15px] text-ghost-600">No data for the current filters.</p>{/if}
				{:else if compareTab === 'dist'}
					{#if dists.length}<Histogram {dists} />{:else}<p class="text-[15px] text-ghost-600">No data for the current filters.</p>{/if}
				{:else if compareTab === 'txns'}
					<!-- Full per-project transaction history (from the district shard) -->
					<p class="mb-5 max-w-[46em] text-[13.5px] text-ghost-600">
						Every matching transaction over the 60-month window (newest first), honouring the sale-type
						and tenure filters above. Caveats are month-dated.
					</p>
					<div class="grid gap-x-6 gap-y-8 {views.length > 1 ? 'md:grid-cols-2' : ''}">
						{#each views as v}
							<div class="min-w-0">
								<div class="flex items-center gap-2 pb-2">
									<span class="h-2.5 w-2.5 shrink-0 rounded-full" style="background:{v.color}" aria-hidden="true"></span>
									<h4 class="truncate text-[14px] font-semibold text-ink-900" title={v.entry.project}>{v.entry.project}</h4>
									<span class="tabular ml-auto shrink-0 text-[12.5px] text-ghost-600">{v.txns.length} txns</span>
								</div>
								{#if v.txns.length}
									<div class="scroller max-h-[50vh] overflow-auto">
										<table class="w-full border-separate border-spacing-0 text-[13px]">
											<thead class="sticky top-0 bg-ghost-50 text-left">
												<tr>
													<th scope="col" class="border-b border-ghost-300 px-2 py-2 font-display text-[12.5px] font-semibold text-ink-700">Month</th>
													<th scope="col" class="border-b border-ghost-300 px-2 py-2 text-right font-display text-[12.5px] font-semibold text-ink-700">Price</th>
													<th scope="col" class="border-b border-ghost-300 px-2 py-2 text-right font-display text-[12.5px] font-semibold text-ink-700">PSF</th>
													<th scope="col" class="border-b border-ghost-300 px-2 py-2 text-right font-display text-[12.5px] font-semibold text-ink-700">Size</th>
													<th scope="col" class="border-b border-ghost-300 px-2 py-2 font-display text-[12.5px] font-semibold text-ink-700">Floor</th>
													<th scope="col" class="border-b border-ghost-300 px-2 py-2 font-display text-[12.5px] font-semibold text-ink-700">Sale</th>
												</tr>
											</thead>
											<tbody>
												{#each [...v.txns].reverse() as t, i (i)}
													<tr>
														<td class="border-b border-ghost-200 px-2 py-1.5 whitespace-nowrap text-ghost-600">{fmtMonth(t.date)}</td>
														<td class="border-b border-ghost-200 px-2 py-1.5 text-right whitespace-nowrap font-medium text-ink-900">{fmtPriceFull(t.price)}</td>
														<td class="border-b border-ghost-200 px-2 py-1.5 text-right whitespace-nowrap text-ink-700">{fmtPsf(t.psf)}</td>
														<td class="border-b border-ghost-200 px-2 py-1.5 text-right whitespace-nowrap text-ghost-600">{t.areaSqft.toLocaleString()} sqft</td>
														<td class="border-b border-ghost-200 px-2 py-1.5 whitespace-nowrap text-ghost-600">{t.floorRange || '—'}</td>
														<td class="border-b border-ghost-200 px-2 py-1.5 whitespace-nowrap text-ghost-600">{SALE_LABELS[t.typeOfSale as SaleCode] ?? '—'}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									</div>
								{:else}
									<p class="border-t border-ghost-300 py-4 text-sm text-ghost-600">No transactions match the current filters.</p>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<!-- Deep dive: floor & size premium, repeat-sale returns, uplift -->
					<div class="grid gap-x-8 gap-y-8 md:grid-cols-2">
						{#each views as v}
							<div class="min-w-0">
								<div class="flex items-center gap-2 border-b border-ghost-300 pb-2">
									<span class="h-2.5 w-2.5 shrink-0 rounded-full" style="background:{v.color}" aria-hidden="true"></span>
									<h4 class="truncate text-[14px] font-semibold text-ink-900" title={v.entry.project}>{v.entry.project}</h4>
								</div>

								<dl class="tabular mt-3 grid grid-cols-2 gap-2 text-center text-[12.5px] sm:grid-cols-4">
									<div class="rounded-[3px] bg-ghost-100 px-2 py-2.5">
										<dt class="text-ghost-600">Return p.a.</dt>
										<dd class="mt-0.5 text-[14px] font-semibold {trendColor(v.shard.repeatStats.medianAnnReturnPct)}">{fmtTrend(v.shard.repeatStats.medianAnnReturnPct)}</dd>
										<dd class="text-[12px] text-ghost-600">{v.shard.repeatStats.pairs} pairs</dd>
									</div>
									<div class="rounded-[3px] bg-ghost-100 px-2 py-2.5">
										<dt class="text-ghost-600">Gross yield</dt>
										<dd class="mt-0.5 text-[14px] font-semibold text-ink-900">{v.shard.rental.grossYield != null ? `${v.shard.rental.grossYield.toFixed(1)}%` : '—'}</dd>
										<dd class="text-[12px] text-ghost-600">{v.shard.rental.rentPsf != null ? `$${v.shard.rental.rentPsf}/sqft/mo` : 'no rent data'}</dd>
									</div>
									<div class="rounded-[3px] bg-ghost-100 px-2 py-2.5">
										<dt class="text-ghost-600">New→resale</dt>
										<dd class="mt-0.5 text-[14px] font-semibold {trendColor(v.shard.uplift.upliftPct)}">{fmtTrend(v.shard.uplift.upliftPct)}</dd>
										<dd class="text-[12px] text-ghost-600">{v.shard.uplift.newCount} new sales</dd>
									</div>
									<div class="rounded-[3px] bg-ghost-100 px-2 py-2.5">
										<dt class="text-ghost-600">Velocity</dt>
										<dd class="mt-0.5 text-[14px] font-semibold text-ink-900">{v.entry.txnsPerYear}/yr</dd>
										<dd class="text-[12px] text-ghost-600">{v.shard.repeatStats.medianHoldYears ?? '—'}y hold</dd>
									</div>
								</dl>

								<!-- Floor premium -->
								{#if v.shard.byFloor.length > 1}
									<p class="mt-4 text-[12.5px] font-medium text-ghost-600">PSF by floor band</p>
									<div class="tabular mt-1.5 space-y-1.5">
										{#each v.shard.byFloor as f}
											<div class="flex items-center gap-2 text-[12.5px]">
												<span class="w-14 shrink-0 text-ghost-600">{f.floorRange}</span>
												<div class="h-2.5 flex-1 overflow-hidden rounded-[2px] bg-ghost-100">
													<div class="h-full rounded-[2px]" style="width:{Math.min(100, (f.medianPsf / Math.max(...v.shard.byFloor.map((x) => x.medianPsf))) * 100)}%; background:{v.color}"></div>
												</div>
												<span class="w-16 shrink-0 text-right text-ink-700">{fmtPsf(f.medianPsf)}</span>
												<span class="w-14 shrink-0 text-right {trendColor(f.premiumPct)}">{fmtTrend(f.premiumPct)}</span>
											</div>
										{/each}
									</div>
								{/if}

								<!-- Size premium -->
								{#if v.shard.bySize.length > 1}
									<p class="mt-4 text-[12.5px] font-medium text-ghost-600">PSF by size</p>
									<div class="tabular mt-1.5 space-y-1.5">
										{#each v.shard.bySize as s}
											<div class="flex items-center gap-2 text-[12.5px]">
												<span class="w-20 shrink-0 text-ghost-600">{s.bucket}</span>
												<div class="h-2.5 flex-1 overflow-hidden rounded-[2px] bg-ghost-100">
													<div class="h-full rounded-[2px]" style="width:{Math.min(100, (s.medianPsf / Math.max(...v.shard.bySize.map((x) => x.medianPsf))) * 100)}%; background:{v.color}"></div>
												</div>
												<span class="w-16 shrink-0 text-right text-ink-700">{fmtPsf(s.medianPsf)}</span>
												<span class="w-14 shrink-0 text-right {trendColor(s.premiumPct)}">{fmtTrend(s.premiumPct)}</span>
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
