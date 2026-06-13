<script lang="ts">
	import { onMount } from 'svelte';
	import { identity, externalLinks } from '$lib/identity';
	import { loadMeta, type Meta } from '$lib/data';
	import { fmtDate } from '$lib/format';
	const year = new Date().getFullYear();

	let meta = $state<Meta | null>(null);
	onMount(async () => {
		try {
			meta = await loadMeta();
		} catch {
			/* footer meta is non-critical */
		}
	});
</script>

<footer class="mx-auto mt-16 w-full max-w-6xl px-6 pb-16">
	<div
		class="rounded-3xl border border-ghost-200/70 bg-white/85 p-6 shadow-xl backdrop-blur-xl dark:border-ink-600/60 dark:bg-ink-900/70 sm:p-7"
	>
		<div class="grid gap-6 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] md:items-center">
			<div>
				<p class="text-xs font-semibold uppercase tracking-[0.15em] text-neon-cyan">Data &amp; methodology</p>
				<p class="mt-3 max-w-xl text-pretty text-sm text-ink-700 dark:text-ghost-300">
					Data: URA, via the URA Data Service. Personal project — not affiliated with or endorsed by
					URA. Caveat data covers ~80–90% of resale/sub-sale volume; figures are derived (computed
					PSF, medians, distributions, approximate returns) over a 60-month rolling window, not a
					republished caveat table. Provided “as is”, no warranty.
				</p>
				<details class="mt-3 max-w-xl text-sm text-ink-600 dark:text-ghost-300">
					<summary class="cursor-pointer text-neon-cyan hover:underline">How the analytics are computed</summary>
					<ul class="mt-2 list-disc space-y-1 pl-5 text-[13px] text-ink-600 dark:text-ghost-300">
						<li><strong>Median PSF / trend:</strong> price ÷ (area × 10.7639), median by quarter/year; trend is the change in yearly-median PSF over the window (years with ≥3 sales).</li>
						<li><strong>Repeat-sale returns (approximate):</strong> the feed has <em>no unit number</em>, so “same unit” is proxied by identical floor area + floor band within a project, then sales paired chronologically. A documented approximation — pair counts are shown for context.</li>
						<li><strong>New→resale uplift:</strong> launch-vintage new-sale median PSF vs recent (≤24-month) resale median PSF.</li>
						<li><strong>Floor / size premium:</strong> median PSF per floor band and size bucket vs the project median.</li>
						<li><strong>Velocity:</strong> average transactions per year over the window.</li>
						<li>Figures default to <strong>resale</strong> (mixing in new launches distorts trends).</li>
					</ul>
				</details>
				<p class="mt-2 max-w-xl text-pretty text-[11px] leading-relaxed text-ghost-500 dark:text-ghost-400">
					Contains information from the URA Private Residential Property Transactions dataset
					accessed via the URA Data Service, made available under the terms of the
					<a
						href="https://data.gov.sg/open-data-licence"
						class="text-neon-cyan underline decoration-dotted underline-offset-2 hover:text-neon-teal"
						rel="noopener noreferrer"
						target="_blank">Singapore Open Data Licence v1.0</a
					>.
				</p>
				<div class="mt-4 flex flex-wrap items-center gap-2">
					{#each externalLinks as link}
						<a
							href={link.url}
							class="inline-flex h-9 items-center gap-1.5 rounded-full border border-ghost-200/70 bg-white/90 px-3 font-mono text-[11px] uppercase tracking-[0.15em] text-ghost-500 transition hover:-translate-y-0.5 hover:border-neon-cyan/50 hover:text-ink-900 dark:border-ink-600/60 dark:bg-ink-800/70 dark:hover:text-white"
						>
							{link.label} ↗
						</a>
					{/each}
				</div>
			</div>

			<div
				class="rounded-xl border border-ghost-200/60 bg-ghost-50/80 p-4 font-mono text-[11px] text-ghost-500 dark:border-ink-600/60 dark:bg-ink-950/70 dark:text-ghost-400"
			>
				{#if meta}
					<p>Last refreshed: {fmtDate(meta.refreshedAt)}</p>
					<p>{meta.projectCount.toLocaleString()} projects · {meta.transactionCount.toLocaleString()} transactions</p>
					{#if meta.mock}<p class="mt-1 text-neon-amber">⚠ showing sample data</p>{/if}
				{/if}
				<p class="mt-2">© {year} {identity.name}</p>
			</div>
		</div>
	</div>
</footer>
