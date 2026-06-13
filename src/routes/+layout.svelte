<script lang="ts">
	import '../app.css';
	import Backdrop from '$lib/components/Backdrop.svelte';
	import Nav from '$lib/components/Nav.svelte';
	import Footer from '$lib/components/Footer.svelte';

	let { children } = $props();
</script>

<Backdrop />

<Nav />

<a
	href="#top"
	class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-ink-900 focus:px-3 focus:py-1.5 focus:text-sm focus:text-white"
>
	Skip to content
</a>

<main
	id="top"
	class="relative mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 pb-12 pt-28 sm:px-6 md:pt-32"
>
	{@render children?.()}
</main>

<Footer />
