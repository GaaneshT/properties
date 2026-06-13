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
		<span class="text-xs font-semibold uppercase tracking-[0.15em] text-neon-cyan">{kicker}</span>
	{/if}
	<h2 class="text-xl font-semibold text-ink-900 dark:text-white">{title}</h2>
	{#if children}
		<p class="max-w-2xl text-sm text-ink-600 dark:text-ghost-300">{@render children()}</p>
	{/if}
</div>
