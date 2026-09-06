<script lang="ts">
	import '../app.css';
	import Bar from '$lib/components/Bar.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { page } from '$app/stores';

	let { children } = $props();
</script>

<a href="#top" class="skip">Skip to content</a>

<div class="wrap" class:house-wrap={$page.url.pathname.endsWith('/house')}>
	<Bar />
	<main id="top">
		{@render children?.()}
	</main>
</div>

<Footer />
