<script lang="ts">
	import {
		projects,
		meta,
		colorFor,
		filterTxns,
		medianPsfByQuarter,
		statsFor,
		SALE_LABELS,
		type SaleCode,
		type Filters,
		type Series,
		type Dist
	} from '$lib/data';
	import { identity } from '$lib/identity';
	import { fmtPsf, fmtPrice, fmtPriceFull } from '$lib/format';
	import PromptHeading from '$lib/components/PromptHeading.svelte';
	import LineChart from '$lib/components/LineChart.svelte';
	import Histogram from '$lib/components/Histogram.svelte';

	// ── Selection state ───────────────────────────────────────────────────
	let selected = $state(new Set(projects.map((p) => p.project)));
	// Default to resale-only — mixing launch-priced new sales with recent
	// resales distorts the trend, especially for older leasehold projects.
	let sales = $state(new Set<SaleCode>(['3']));
	let tenure = $state<'all' | 'freehold' | 'leasehold'>('all');

	const SALE_OPTIONS: SaleCode[] = ['3', '2', '1']; // resale, sub-sale, new sale

	function toggleProject(name: string) {
		const next = new Set(selected);
		next.has(name) ? next.delete(name) : next.add(name);
		selected = next;
	}
	function toggleSale(code: SaleCode) {
		const next = new Set(sales);
		next.has(code) ? next.delete(code) : next.add(code);
		// Never allow an empty sale filter — fall back to resale.
		if (next.size === 0) next.add('3');
		sales = next;
	}

	const filters = $derived<Filters>({ sales, tenure });

	// Per selected project: filtered txns + derivations, with a stable color.
	const views = $derived(
		projects
			.map((p, i) => ({ p, color: colorFor(i) }))
			.filter(({ p }) => selected.has(p.project))
			.map(({ p, color }) => {
				const txns = filterTxns(p.transactions, filters);
				return {
					project: p,
					color,
					txns,
					points: medianPsfByQuarter(txns),
					stats: statsFor(txns)
				};
			})
	);

	const lineSeries = $derived<Series[]>(
		views
			.filter((v) => v.points.length > 0)
			.map((v) => ({ label: v.project.project, color: v.color, points: v.points }))
	);

	const dists = $derived<Dist[]>(
		views
			.filter((v) => v.txns.length > 0)
			.map((v) => ({ label: v.project.project, color: v.color, values: v.txns.map((t) => t.psf) }))
	);

	const activeSaleLabel = $derived(
		SALE_OPTIONS.filter((c) => sales.has(c))
			.map((c) => SALE_LABELS[c])
			.join(' + ')
	);

	const totalShown = $derived(views.reduce((n, v) => n + v.txns.length, 0));

	// Recent transactions across the selected/filtered set.
	const recent = $derived(
		views
			.flatMap((v) => v.txns.map((t) => ({ ...t, project: v.project.project, color: v.color })))
			.sort((a, b) => b.date.localeCompare(a.date))
			.slice(0, 12)
	);
</script>

<svelte:head>
	<title>Property Prices · properties.gaanesh.com</title>
</svelte:head>

<!-- Header -->
<section class="space-y-3">
	<PromptHeading path="properties" command="ura --watchlist">
		{identity.tagline}
	</PromptHeading>
	<h1 class="text-balance text-2xl font-semibold text-ink-900 dark:text-white sm:text-3xl">
		Singapore URA resale price viewer
	</h1>
	<p class="max-w-2xl text-pretty text-sm text-ink-600 dark:text-ghost-300">
		Median PSF trends and price distributions for a small personal watchlist of private residential
		projects. Derived from URA caveat data — read-only, no listings. Pick projects and segments to
		compare.
	</p>
</section>

<!-- Controls -->
<section
	class="rounded-3xl border border-ghost-200/60 bg-white/85 p-5 shadow-xl backdrop-blur-xl dark:border-ink-600/60 dark:bg-ink-900/60 sm:p-6"
>
	<div class="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
		<!-- Projects -->
		<div>
			<p class="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-ghost-500">projects</p>
			<div class="flex flex-wrap gap-2">
				{#each projects as p, i}
					{@const on = selected.has(p.project)}
					<button
						type="button"
						onclick={() => toggleProject(p.project)}
						class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-mono text-xs transition {on
							? 'border-transparent text-ink-900 dark:text-white'
							: 'border-ghost-200/70 text-ghost-500 hover:text-ink-900 dark:border-ink-600/70 dark:hover:text-white'}"
						style={on ? `background:${colorFor(i)}1a; box-shadow: inset 0 0 0 1px ${colorFor(i)}` : ''}
						aria-pressed={on}
					>
						<span class="h-2.5 w-2.5 rounded-full" style="background:{colorFor(i)}"></span>
						{p.project}
						<span class="text-ghost-500">· D{p.district}</span>
					</button>
				{/each}
			</div>
		</div>

		<!-- Filters -->
		<div class="grid gap-4 sm:grid-cols-2">
			<div>
				<p class="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-ghost-500">
					type of sale
				</p>
				<div class="flex flex-wrap gap-1.5">
					{#each SALE_OPTIONS as code}
						{@const on = sales.has(code)}
						<button
							type="button"
							onclick={() => toggleSale(code)}
							class="rounded-full px-3 py-1.5 font-mono text-xs transition {on
								? 'bg-ink-900 text-neon-cyan dark:bg-ink-700'
								: 'border border-ghost-200/70 text-ghost-500 hover:text-ink-900 dark:border-ink-600/70 dark:hover:text-white'}"
							aria-pressed={on}
						>
							{SALE_LABELS[code]}
						</button>
					{/each}
				</div>
			</div>

			<div>
				<p class="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-ghost-500">tenure</p>
				<div class="inline-flex rounded-full border border-ghost-200/70 bg-ghost-50 p-1 font-mono text-xs dark:border-ink-600/60 dark:bg-ink-900/60">
					{#each [{ id: 'all', label: 'all' }, { id: 'freehold', label: 'freehold' }, { id: 'leasehold', label: 'leasehold' }] as opt}
						<button
							type="button"
							onclick={() => (tenure = opt.id as typeof tenure)}
							class="rounded-full px-3 py-1 transition {tenure === opt.id
								? 'bg-ink-900 text-neon-cyan dark:bg-ink-700'
								: 'text-ghost-500 hover:text-ink-900 dark:hover:text-white'}"
						>{opt.label}</button>
					{/each}
				</div>
			</div>
		</div>
	</div>

	<p class="mt-4 font-mono text-[11px] text-ghost-500">
		showing <span class="text-neon-cyan">{totalShown}</span> transactions ·
		{activeSaleLabel}{tenure !== 'all' ? ` · ${tenure}` : ''}
	</p>
</section>

{#if views.length === 0}
	<p class="rounded-2xl border border-neon-amber/30 bg-neon-amber/5 p-5 font-mono text-sm text-neon-amber">
		Select at least one project above to see charts.
	</p>
{:else}
	<!-- Median PSF over time -->
	<section class="space-y-4">
		<PromptHeading path="trend" command={`median_psf --by quarter`}>
			median price-per-sqft by quarter · overlay to compare
		</PromptHeading>
		<div
			class="rounded-3xl border border-ghost-200/60 bg-white/85 p-4 shadow-xl backdrop-blur-xl dark:border-ink-600/60 dark:bg-ink-900/60 sm:p-6"
		>
			{#if lineSeries.length > 0}
				<!-- Legend -->
				<div class="mb-3 flex flex-wrap gap-x-4 gap-y-1">
					{#each lineSeries as s}
						<span class="inline-flex items-center gap-1.5 font-mono text-[11px] text-ink-700 dark:text-ghost-300">
							<span class="h-2.5 w-2.5 rounded-full" style="background:{s.color}"></span>{s.label}
						</span>
					{/each}
				</div>
				<LineChart series={lineSeries} />
			{:else}
				<p class="font-mono text-sm text-ghost-500">No transactions match the current filters.</p>
			{/if}
		</div>
	</section>

	<!-- Stats cards -->
	<section class="grid gap-4 md:grid-cols-2">
		{#each views as v}
			<div
				class="rounded-3xl border border-ghost-200/60 bg-white/85 p-5 shadow-lg backdrop-blur-xl dark:border-ink-600/60 dark:bg-ink-900/60"
				style="box-shadow: inset 0 1px 0 0 rgba(255,255,255,0.04), 0 0 0 1px {v.color}33"
			>
				<div class="flex items-center gap-2">
					<span class="h-3 w-3 rounded-full" style="background:{v.color}"></span>
					<h3 class="text-balance font-semibold text-ink-900 dark:text-white">{v.project.project}</h3>
				</div>
				<p class="mt-0.5 font-mono text-[11px] text-ghost-500">
					D{v.project.district} · {v.project.marketSegment} · {v.project.street}
				</p>

				{#if v.stats}
					<div class="mt-4 grid grid-cols-3 gap-3">
						<div class="rounded-xl border border-ghost-200/60 bg-ghost-50/70 p-3 dark:border-ink-600/60 dark:bg-ink-950/60">
							<p class="font-mono text-[10px] uppercase tracking-[0.15em] text-ghost-500">median psf</p>
							<p class="mt-1 text-xl font-bold text-ink-900 dark:text-white">{fmtPsf(v.stats.medianPsf)}</p>
						</div>
						<div class="rounded-xl border border-ghost-200/60 bg-ghost-50/70 p-3 dark:border-ink-600/60 dark:bg-ink-950/60">
							<p class="font-mono text-[10px] uppercase tracking-[0.15em] text-ghost-500">psf range</p>
							<p class="mt-1 text-sm font-semibold text-ink-900 dark:text-white">
								{fmtPsf(v.stats.minPsf)}–{fmtPsf(v.stats.maxPsf)}
							</p>
						</div>
						<div class="rounded-xl border border-ghost-200/60 bg-ghost-50/70 p-3 dark:border-ink-600/60 dark:bg-ink-950/60">
							<p class="font-mono text-[10px] uppercase tracking-[0.15em] text-ghost-500">txns</p>
							<p class="mt-1 text-xl font-bold text-neon-cyan">{v.stats.count}</p>
						</div>
					</div>
					<p class="mt-3 font-mono text-[11px] text-ghost-500">
						median price <span class="text-ink-900 dark:text-ghost-200">{fmtPriceFull(v.stats.medianPrice)}</span>
						· range {fmtPrice(v.stats.minPrice)}–{fmtPrice(v.stats.maxPrice)}
					</p>
				{:else}
					<p class="mt-4 font-mono text-sm text-ghost-500">No transactions match the filters.</p>
				{/if}
			</div>
		{/each}
	</section>

	<!-- Distribution -->
	<section class="space-y-4">
		<PromptHeading path="distribution" command="hist --by psf">
			price-per-sqft distribution (shared bins)
		</PromptHeading>
		<div
			class="rounded-3xl border border-ghost-200/60 bg-white/85 p-4 shadow-xl backdrop-blur-xl dark:border-ink-600/60 dark:bg-ink-900/60 sm:p-6"
		>
			{#if dists.length > 0}
				<div class="mb-3 flex flex-wrap gap-x-4 gap-y-1">
					{#each dists as d}
						<span class="inline-flex items-center gap-1.5 font-mono text-[11px] text-ink-700 dark:text-ghost-300">
							<span class="h-2.5 w-2.5 rounded-full" style="background:{d.color}"></span>{d.label}
						</span>
					{/each}
				</div>
				<Histogram {dists} />
			{:else}
				<p class="font-mono text-sm text-ghost-500">No transactions match the current filters.</p>
			{/if}
		</div>
	</section>

	<!-- Recent transactions -->
	<section class="space-y-4">
		<PromptHeading path="recent" command="tail -n 12">
			most recent transactions in the current view
		</PromptHeading>
		<div
			class="overflow-x-auto rounded-3xl border border-ghost-200/60 bg-white/85 shadow-xl backdrop-blur-xl dark:border-ink-600/60 dark:bg-ink-900/60"
		>
			<table class="w-full font-mono text-xs">
				<thead
					class="bg-ghost-50/70 text-left text-[10px] uppercase tracking-wide text-ghost-500 dark:bg-ink-950/60"
				>
					<tr>
						<th class="px-4 py-2.5">date</th>
						<th class="px-4 py-2.5">project</th>
						<th class="px-4 py-2.5">psf</th>
						<th class="px-4 py-2.5">price</th>
						<th class="px-4 py-2.5">area</th>
						<th class="px-4 py-2.5">floor</th>
						<th class="px-4 py-2.5">sale</th>
					</tr>
				</thead>
				<tbody>
					{#each recent as t}
						<tr class="border-t border-ghost-200/40 dark:border-ink-600/40">
							<td class="px-4 py-2 text-ghost-500">{t.date}</td>
							<td class="px-4 py-2">
								<span class="inline-flex items-center gap-1.5">
									<span class="h-2 w-2 rounded-full" style="background:{t.color}"></span>
									<span class="text-ink-900 dark:text-ghost-100">{t.project}</span>
								</span>
							</td>
							<td class="px-4 py-2 text-neon-cyan">{fmtPsf(t.psf)}</td>
							<td class="px-4 py-2 text-ink-900 dark:text-ghost-200">{fmtPriceFull(t.price)}</td>
							<td class="px-4 py-2 text-ghost-500">{t.areaSqft} sqft</td>
							<td class="px-4 py-2 text-ghost-500">{t.floorRange}</td>
							<td class="px-4 py-2 text-ghost-500">{t.saleType}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>
{/if}

<!-- Provenance line -->
<p class="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-ghost-500">
	<span class="dot-live"></span>
	data baked server-side from URA · the browser never calls the URA API
	{#if meta.mock}<span class="text-neon-amber">· MOCK SAMPLE</span>{/if}
</p>
