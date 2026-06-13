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
				<p class="font-mono text-xs uppercase tracking-[0.25em] text-neon-cyan">// data &amp; credits</p>
				<p class="mt-3 max-w-xl text-pretty text-sm text-ink-700 dark:text-ghost-300">
					Data: URA, via the URA Data Service. Personal project — not affiliated with or endorsed by
					URA. Caveat data covers ~80–90% of resale/sub-sale volume; figures are derived (computed
					PSF, medians, distributions) over a 60-month rolling window, not a republished caveat
					table. Provided “as is”, no warranty.
				</p>
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
