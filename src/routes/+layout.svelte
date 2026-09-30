<script lang="ts">
	import '../app.css';
	import Bar from '$lib/components/Bar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import DataNote from '$lib/components/DataNote.svelte';
	import { page } from '$app/stores';

	let { children } = $props();

	// The URA attribution and methodology belong to the analytics pages, not
	// the house studio.
	const isHouse = $derived($page.url.pathname.endsWith('/house'));
</script>

<a href="#top" class="skip">Skip to content</a>

<div class="wrap" class:house-wrap={isHouse}>
	<Bar />
	<main id="top">
		{@render children?.()}
	</main>
	{#if !isHouse}<DataNote />{/if}
</div>

<Footer />
