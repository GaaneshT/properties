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

	const historyHref = (project: string) => `${base}/?sel=${encodeURIComponent(project)}&tab=txns`;

	// Shared control styles: the system's 3px field and 4px panel.
	const panel = 'rounded-[4px] border border-ghost-200 bg-ghost-50';
	const field = 'w-full rounded-[3px] border border-ghost-300 bg-ghost-50 px-3 py-2 text-sm text-ink-900';
	const fieldLabel = 'mb-1 block text-[12.5px] font-medium text-ghost-600';
	const th = 'border-b border-ghost-300 px-3 py-3 align-bottom font-display text-[13px] leading-tight font-semibold text-ink-700';
	const td = 'border-b border-ghost-200 px-3 py-2.5';
</script>

<svelte:head>
	<title>Recent transactions · properties.gaanesh.com</title>
</svelte:head>

<div class="phead">
	<h1>Recent transactions</h1>
	<p>
		The latest private-residential caveats lodged with URA, market-wide. URA dates caveats by month,
		so these are ordered by most recent month{meta?.recentLatest ? ` (latest: ${fmtMonth(meta.recentLatest)})` : ''}.
	</p>
</div>

<div class="caveat">
	<p>
		This is a market-wide snapshot of the most recent months only, so searching one project here shows
		just its latest sales. For a project's <b>full 60-month transaction history</b>, open
		<a href="{base}/" class="lnk">Overview</a>, search the project, tick it, and use the “All
		transactions” tab.
	</p>
</div>

{#if loading}
	<p class="{panel} mt-10 p-8 text-center text-[15px] text-ghost-600" role="status">Loading recent transactions…</p>
{:else if loadError}
	<div class="mt-10 rounded-[3px] border border-l-[3px] border-ghost-200 border-l-neon-rose bg-ghost-50 px-[22px] py-[18px]" role="alert">
		<p class="text-[15.5px] leading-relaxed text-ink-700">
			<b class="font-semibold text-neon-rose">Couldn't load recent transactions.</b>
			{loadError}. Reload the page to try again.
		</p>
	</div>
{:else}
	<!-- Filters -->
	<section class="{panel} mt-10 p-4 sm:p-5" aria-label="Filters">
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:flex lg:flex-wrap lg:items-end">
			<label class="col-span-2 sm:col-span-3 lg:min-w-[220px] lg:flex-1">
				<span class={fieldLabel}>Search project or street</span>
				<input type="search" bind:value={search} placeholder="e.g. Clematis, Bedok…" class={field} />
			</label>
			<label class="lg:shrink-0">
				<span class={fieldLabel}>Type</span>
				<select bind:value={category} class="{field} pr-9 lg:w-auto">
					<option value="all">All types</option>
					<option value="condo">Condo / Apartment</option>
					<option value="ec">Executive Condo</option>
					<option value="landed">Landed</option>
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
				<span class={fieldLabel}>District</span>
				<select bind:value={district} class="{field} pr-9 lg:w-auto">
					<option value="all">All</option>
					{#each districts as d}<option value={d}>D{d}</option>{/each}
				</select>
			</label>
			<label class="lg:shrink-0">
				<span class={fieldLabel}>Sale type</span>
				<select bind:value={saleType} class="{field} pr-9 lg:w-auto">
					<option value="all">All sales</option>
					<option value="3">Resale</option>
					<option value="1">New sale</option>
					<option value="2">Sub-sale</option>
				</select>
			</label>
			<label class="lg:shrink-0">
				<span class={fieldLabel}>Sort by</span>
				<select bind:value={sortBy} class="{field} pr-9 lg:w-auto">
					<option value="date">Most recent</option>
					<option value="price">Highest price</option>
					<option value="psf">Highest PSF</option>
				</select>
			</label>
		</div>
		<p class="tabular mt-4 text-[13px] text-ghost-600">
			Showing {Math.min(visible.length, filtered.length)} of {filtered.length.toLocaleString()} transactions
			{#if filtered.length > ROW_CAP}· refine filters to narrow{/if}
		</p>
	</section>

	<!-- Transaction list (mobile/tablet) -->
	<ul class="{panel} mt-5 lg:hidden" aria-label="Transactions">
		{#each visible as r, i (i)}
			<li class="border-b border-ghost-200 px-4 py-3.5 last:border-b-0">
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0">
						<a
							href={historyHref(r.project)}
							class="block truncate font-medium text-ink-900 transition hover:text-neon-cyan"
							title="View full transaction history">{r.project}</a
						>
						<div class="truncate text-[12.5px] text-ghost-600">{r.street} · D{r.district} · {r.region}</div>
					</div>
					<div class="tabular shrink-0 text-right">
						<div class="font-semibold text-ink-900">{fmtPriceFull(r.price)}</div>
						<div class="text-[12.5px] text-ghost-600">{fmtMonth(r.date)}</div>
					</div>
				</div>
				<div class="tabular mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] text-ink-700">
					<span>{fmtPsf(r.psf)} psf</span>
					<span>{fmtArea(r.areaSqft)}</span>
					<span>Floor {r.floorRange || '—'}</span>
					<span>{SALE_LABELS[r.typeOfSale as SaleCode] ?? '—'}</span>
					<span>{r.tenureClass}</span>
				</div>
			</li>
		{/each}
		{#if visible.length === 0}
			<li class="p-6 text-center text-[15px] text-ghost-600">No transactions match these filters.</li>
		{/if}
	</ul>

	<!-- Table (desktop) -->
	<section class="scroller {panel} mt-5 hidden max-h-[64vh] overflow-auto lg:block" aria-label="Transactions">
		<table class="w-full border-separate border-spacing-0 text-sm">
			<thead class="sticky top-0 z-10 bg-ghost-50 text-left">
				<tr>
					<th scope="col" class={th}>Month</th>
					<th scope="col" class={th}>Project</th>
					<th scope="col" class="{th} text-right">Price</th>
					<th scope="col" class="{th} text-right">PSF</th>
					<th scope="col" class="{th} text-right">Size</th>
					<th scope="col" class={th}>Floor</th>
					<th scope="col" class={th}>Sale</th>
					<th scope="col" class={th}>District</th>
					<th scope="col" class={th}>Tenure</th>
				</tr>
			</thead>
			<tbody>
				{#each visible as r, i (i)}
					<tr class="transition-colors hover:bg-neon-cyan/[0.045]">
						<td class="{td} whitespace-nowrap text-ghost-600">{fmtMonth(r.date)}</td>
						<td class={td}>
							<a
								href={historyHref(r.project)}
								class="font-medium text-ink-900 transition hover:text-neon-cyan"
								title="View full transaction history">{r.project}</a
							>
							<div class="text-[12.5px] text-ghost-600">{r.street}</div>
						</td>
						<td class="{td} text-right whitespace-nowrap font-medium text-ink-900">{fmtPriceFull(r.price)}</td>
						<td class="{td} text-right whitespace-nowrap text-ink-700">{fmtPsf(r.psf)}</td>
						<td class="{td} text-right whitespace-nowrap text-ghost-600">{r.areaSqft.toLocaleString()} sqft</td>
						<td class="{td} whitespace-nowrap text-ghost-600">{r.floorRange || '—'}</td>
						<td class="{td} whitespace-nowrap text-ghost-600">{SALE_LABELS[r.typeOfSale as SaleCode] ?? '—'}</td>
						<td class="{td} whitespace-nowrap text-ghost-600" title={REGION_LABELS[r.region] ?? ''}>D{r.district} · {r.region}</td>
						<td class="{td} whitespace-nowrap text-ghost-600">{r.tenureClass}</td>
					</tr>
				{/each}
				{#if visible.length === 0}
					<tr><td colspan="9" class="px-3 py-8 text-center text-[15px] text-ghost-600">No transactions match these filters.</td></tr>
				{/if}
			</tbody>
		</table>
	</section>

	<p class="tabular mt-4 text-[13px] text-ghost-600">
		Most recent {meta?.recentCount?.toLocaleString() ?? rows.length.toLocaleString()} caveats across all
		projects · derived from URA data, never the raw feed
	</p>
{/if}
