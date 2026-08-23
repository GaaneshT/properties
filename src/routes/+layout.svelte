<script lang="ts">
	import '../app.css';
	import Bar from '$lib/components/Bar.svelte';
	import Footer from '$lib/components/Footer.svelte';

	let { children } = $props();
</script>

<a href="#top" class="skip">Skip to content</a>

<div class="wrap">
	<Bar />
	<main id="top">
		{@render children?.()}
	</main>
</div>

<Footer />
