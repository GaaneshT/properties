<script lang="ts">
	import { onMount } from 'svelte';
	import { loadMeta, type Meta } from '$lib/data';
	import { fmtDate } from '$lib/format';

	// Attribution, method and freshness. The Singapore Open Data Licence
	// requires the attribution line; the rest keeps the derived figures honest
	// about what they are.
	let meta = $state<Meta | null>(null);
	onMount(async () => {
		try {
			meta = await loadMeta();
		} catch {
			/* freshness line is non-critical */
		}
	});
</script>

<section id="method" class="method scroll-mt-8" aria-labelledby="method-h">
	<h2 id="method-h">Data &amp; methodology</h2>
	<p>
		<b>Data: URA, via the URA Data Service.</b> Personal project, not affiliated with or endorsed by
		URA. Caveat data covers ~80–90% of resale/sub-sale volume; figures are derived (computed PSF,
		medians, distributions, approximate returns) over a 60-month rolling window, not a republished
		caveat table. Provided “as is”, no warranty.
	</p>

	<details>
		<summary>How the analytics are computed</summary>
		<ul>
			<li>
				<b>Median PSF / trend:</b> price ÷ (area × 10.7639), median by quarter/year; trend is the change
				in yearly-median PSF over the window (years with ≥3 sales).
			</li>
			<li>
				<b>Repeat-sale returns (approximate):</b> the feed has <em>no unit number</em>, so “same unit”
				is proxied by identical floor area + floor band within a project, then sales paired
				chronologically. A documented approximation; pair counts are shown for context.
			</li>
			<li>
				<b>New→resale uplift:</b> launch-vintage new-sale median PSF vs recent (≤24-month) resale median
				PSF.
			</li>
			<li>
				<b>Gross rental yield:</b> latest median rent PSF (URA PMI_Resi_Rental_Median) × 12 ÷ sale median
				PSF. Available where URA publishes rental medians.
			</li>
			<li><b>Floor / size premium:</b> median PSF per floor band and size bucket vs the project median.</li>
			<li><b>Velocity:</b> average transactions per year over the window.</li>
			<li>Figures default to <b>resale</b> (mixing in new launches distorts trends).</li>
		</ul>
	</details>

	<p class="fine">
		Contains information from the URA Private Residential Property Transactions dataset accessed via the
		URA Data Service, made available under the terms of the
		<a
			href="https://data.gov.sg/open-data-licence"
			class="lnk"
			rel="noopener noreferrer"
			target="_blank">Singapore Open Data Licence v1.0</a
		>.
	</p>

	{#if meta}
		<p class="fine tabular">
			Last refreshed {fmtDate(meta.refreshedAt)} · {meta.projectCount.toLocaleString()} projects ·
			{meta.transactionCount.toLocaleString()} transactions
			{#if meta.mock}<span class="warn"> · showing sample data</span>{/if}
		</p>
	{/if}
</section>
