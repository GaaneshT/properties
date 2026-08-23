<script lang="ts">
	let {
		title,
		kicker = null,
		children
	}: {
		title: string;
		kicker?: string | null;
		children?: import('svelte').Snippet;
	} = $props();
</script>

<div class="flex flex-col gap-1">
	{#if kicker}
		<span class="text-[13px] font-semibold tracking-[0.02em] text-ghost-600 uppercase">{kicker}</span>
	{/if}
	<h2 class="text-xl font-semibold text-ink-900">{title}</h2>
	{#if children}
		<p class="max-w-2xl text-[15px] text-ink-700">{@render children()}</p>
	{/if}
</div>
