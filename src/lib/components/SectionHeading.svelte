<script lang="ts">
	import type { Snippet } from 'svelte';

	// Title, an optional count in the margin, and a hairline to the edge. The
	// count carries state (e.g. "3 of 6 selected"), so it sits beside the
	// heading rather than above it.
	let {
		title,
		count = null,
		id = undefined,
		actions,
		children
	}: {
		title: string;
		count?: string | null;
		id?: string;
		actions?: Snippet;
		children?: Snippet;
	} = $props();
</script>

<div>
	<div class="grouphead">
		<h2 class="y" {id}>{title}</h2>
		{#if count}<span class="n" aria-live="polite">{count}</span>{/if}
		<span class="ln" aria-hidden="true"></span>
		{#if actions}{@render actions()}{/if}
	</div>
	{#if children}
		<p class="mt-2 max-w-[38em] text-[15px] text-ink-700">{@render children()}</p>
	{/if}
</div>
