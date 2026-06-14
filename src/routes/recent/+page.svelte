<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import {
		loadRecent,
		loadMeta,
		SALE_LABELS,
		REGION_LABELS,
		type RecentTxn,
		type Category,
		type SaleCode,
		type Meta
	} from '$lib/data';
	import { fmtPsf, fmtPriceFull, fmtArea } from '$lib/format';

	let rows = $state<RecentTxn[]>([]);
	let meta = $state<Meta | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);

	onMount(async () => {
		try {
			const [r, m] = await Promise.all([loadRecent(), loadMeta().catch(() => null)]);
			rows = r;
			meta = m;
		} catch (e) {
			loadError = e instanceof Error ? e.message : String(e);
		} finally {
			loading = false;
		}
	});

	// Filters
	let search = $state('');
	let category = $state<Category | 'all'>('all');
	let region = $state<'all' | 'CCR' | 'RCR' | 'OCR'>('all');
	let saleType = $state<'all' | SaleCode>('all');
	let district = $state('all');
	let sortBy = $state<'date' | 'price' | 'psf'>('date');

	const ROW_CAP = 200;

	const districts = $derived(
		[...new Set(rows.map((r) => r.district).filter(Boolean))].sort((a, b) => Number(a) - Number(b))
	);

	const fmtMonth = (d: string) => {
		const [y, m] = d.split('-');
		const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
		return `${months[Number(m) - 1] ?? m} ${y}`;
	};

	const filtered = $derived.by(() => {
		const q = search.trim().toLowerCase();
		let out = rows.filter((r) => {
			if (category !== 'all' && r.category !== category) return false;
			if (region !== 'all' && r.region !== region) return false;
			if (saleType !== 'all' && r.typeOfSale !== saleType) return false;
			if (district !== 'all' && r.district !== district) return false;
			if (q && !`${r.project} ${r.street}`.toLowerCase().includes(q)) return false;
			return true;
		});
		if (sortBy === 'price') out = [...out].sort((a, b) => b.price - a.price);
		else if (sortBy === 'psf') out = [...out].sort((a, b) => b.psf - a.psf);
		// 'date' keeps the pre-sorted most-recent-first order
		return out;
	});

	const visible = $derived(filtered.slice(0, ROW_CAP));
</script>

<svelte:head>
	<title>Recent transactions · properties.gaanesh.com</title>
</svelte:head>

<section class="space-y-2">
	<span class="text-xs font-semibold uppercase tracking-[0.15em] text-neon-cyan">URA caveats</span>
	<h1 class="text-3xl font-semibold text-ink-900 dark:text-white">Recent transactions</h1>
	<p class="max-w-2xl text-sm text-ink-600 dark:text-ghost-300">
		The latest private-residential caveats lodged with URA, market-wide. URA dates caveats by month,
		so these are ordered by most recent month{meta?.recentLatest ? ` (latest: ${fmtMonth(meta.recentLatest)})` : ''}.
	</p>
	<p class="max-w-2xl text-xs text-ghost-500">
		This is a market-wide snapshot of the most recent months only — so searching one project here
		shows just its latest sales. For a project's <strong>full 60-month transaction history</strong>,
		open <a href="{base}/" class="text-neon-cyan hover:underline">Analytics</a>, search the project,
		tick it, and use the “All transactions” tab.
	</p>
</section>

{#if loading}
	<div class="rounded-2xl border border-ghost-200/60 bg-white/85 p-8 text-center text-sm text-ghost-500 dark:border-ink-600/60 dark:bg-ink-900/60">
		Loading recent transactions…
	</div>
{:else if loadError}
	<div class="rounded-2xl border border-neon-rose/40 bg-neon-rose/5 p-6 text-sm text-neon-rose">
		Couldn't load data: {loadError}
	</div>
{:else}
	<!-- Filters -->
	<section class="rounded-2xl border border-ghost-200/60 bg-white/85 p-4 dark:border-ink-600/60 dark:bg-ink-900/60">
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:flex lg:flex-wrap lg:items-end">
			<label class="col-span-2 sm:col-span-3 lg:min-w-[220px] lg:flex-1">
				<span class="mb-1 block text-xs font-medium text-ghost-500">Search project or street</span>
				<input type="search" bind:value={search} placeholder="e.g. Clematis, Bedok…" class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm text-ink-900 dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100" />
			</label>
			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Type</span>
				<select bind:value={category} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-auto dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="all">All types</option>
					<option value="condo">Condo / Apartment</option>
					<option value="ec">Executive Condo</option>
					<option value="landed">Landed</option>
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
				<span class="mb-1 block text-xs font-medium text-ghost-500">District</span>
				<select bind:value={district} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-auto dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="all">All</option>
					{#each districts as d}<option value={d}>D{d}</option>{/each}
				</select>
			</label>
			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Sale type</span>
				<select bind:value={saleType} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-auto dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="all">All sales</option>
					<option value="3">Resale</option>
					<option value="1">New sale</option>
					<option value="2">Sub-sale</option>
				</select>
			</label>
			<label>
				<span class="mb-1 block text-xs font-medium text-ghost-500">Sort by</span>
				<select bind:value={sortBy} class="w-full rounded-lg border border-ghost-200/70 bg-white px-3 py-2 text-sm lg:w-auto dark:border-ink-600/70 dark:bg-ink-950/70 dark:text-ghost-100">
					<option value="date">Most recent</option>
					<option value="price">Highest price</option>
					<option value="psf">Highest PSF</option>
				</select>
			</label>
		</div>
		<p class="mt-3 text-xs text-ghost-500">
			Showing {Math.min(visible.length, filtered.length)} of {filtered.length.toLocaleString()} transactions
			{#if filtered.length > ROW_CAP}· refine filters to narrow{/if}
		</p>
	</section>

	<!-- Cards (mobile/tablet) -->
	<section class="space-y-2 lg:hidden">
		{#each visible as r, i (i)}
			<div class="rounded-xl border border-ghost-200/60 bg-white/85 p-3 dark:border-ink-600/60 dark:bg-ink-900/60">
				<div class="flex items-start justify-between gap-2">
					<div class="min-w-0">
						<a
							href="{base}/?sel={encodeURIComponent(r.project)}&tab=txns"
							class="block truncate font-medium text-ink-900 hover:text-neon-cyan dark:text-white dark:hover:text-neon-cyan"
							title="View full transaction history"
						>{r.project}</a>
						<div class="truncate text-xs text-ghost-500">{r.street} · D{r.district} · {r.region}</div>
					</div>
					<div class="shrink-0 text-right">
						<div class="font-semibold text-ink-900 dark:text-white">{fmtPriceFull(r.price)}</div>
						<div class="text-xs text-ghost-500">{fmtMonth(r.date)}</div>
					</div>
				</div>
				<div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ghost-600 dark:text-ghost-300">
					<span>{fmtPsf(r.psf)} psf</span>
					<span>{fmtArea(r.areaSqft)}</span>
					<span>Floor {r.floorRange || '—'}</span>
					<span>{SALE_LABELS[r.typeOfSale as SaleCode] ?? '—'}</span>
					<span>{r.tenureClass}</span>
				</div>
			</div>
		{/each}
		{#if visible.length === 0}
			<p class="rounded-xl border border-ghost-200/60 p-6 text-center text-sm text-ghost-500 dark:border-ink-600/60">No transactions match these filters.</p>
		{/if}
	</section>

	<!-- Table (desktop) -->
	<section class="hidden max-h-[64vh] overflow-auto rounded-2xl border border-ghost-200/60 bg-white/85 lg:block dark:border-ink-600/60 dark:bg-ink-900/60">
		<table class="w-full text-sm">
			<thead class="sticky top-0 z-10 border-b border-ghost-200/60 bg-white/95 text-left text-xs uppercase tracking-wide text-ghost-500 backdrop-blur dark:border-ink-600/60 dark:bg-ink-900/95">
				<tr>
					<th class="px-3 py-3 font-medium">Month</th>
					<th class="px-3 py-3 font-medium">Project</th>
					<th class="px-3 py-3 font-medium">Price</th>
					<th class="px-3 py-3 font-medium">PSF</th>
					<th class="px-3 py-3 font-medium">Size</th>
					<th class="px-3 py-3 font-medium">Floor</th>
					<th class="px-3 py-3 font-medium">Sale</th>
					<th class="px-3 py-3 font-medium">District</th>
					<th class="px-3 py-3 font-medium">Tenure</th>
				</tr>
			</thead>
			<tbody>
				{#each visible as r, i (i)}
					<tr class="border-b border-ghost-200/40 transition hover:bg-ghost-50/70 dark:border-ink-600/30 dark:hover:bg-ink-800/40">
						<td class="whitespace-nowrap px-3 py-2.5 text-ghost-500">{fmtMonth(r.date)}</td>
						<td class="px-3 py-2.5">
							<a
								href="{base}/?sel={encodeURIComponent(r.project)}&tab=txns"
								class="font-medium text-ink-900 hover:text-neon-cyan dark:text-white dark:hover:text-neon-cyan"
								title="View full transaction history"
							>{r.project}</a>
							<div class="text-xs text-ghost-500">{r.street}</div>
						</td>
						<td class="whitespace-nowrap px-3 py-2.5 font-medium text-ink-900 dark:text-ghost-100">{fmtPriceFull(r.price)}</td>
						<td class="whitespace-nowrap px-3 py-2.5 text-ink-700 dark:text-ghost-200">{fmtPsf(r.psf)}</td>
						<td class="whitespace-nowrap px-3 py-2.5 text-ghost-600 dark:text-ghost-300">{r.areaSqft.toLocaleString()} sqft</td>
						<td class="whitespace-nowrap px-3 py-2.5 text-ghost-600 dark:text-ghost-300">{r.floorRange || '—'}</td>
						<td class="whitespace-nowrap px-3 py-2.5 text-ghost-600 dark:text-ghost-300">{SALE_LABELS[r.typeOfSale as SaleCode] ?? '—'}</td>
						<td class="whitespace-nowrap px-3 py-2.5 text-ghost-500" title={REGION_LABELS[r.region] ?? ''}>D{r.district} · {r.region}</td>
						<td class="whitespace-nowrap px-3 py-2.5 text-ghost-500">{r.tenureClass}</td>
					</tr>
				{/each}
				{#if visible.length === 0}
					<tr><td colspan="9" class="px-3 py-8 text-center text-sm text-ghost-500">No transactions match these filters.</td></tr>
				{/if}
			</tbody>
		</table>
	</section>

	<p class="flex items-center gap-2 text-[11px] text-ghost-500">
		<span class="dot-live"></span>
		Most recent {meta?.recentCount?.toLocaleString() ?? rows.length.toLocaleString()} caveats across all projects · derived from URA data, never the raw feed
	</p>
{/if}
