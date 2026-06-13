<script lang="ts">
	import { onMount } from 'svelte';
	import { identity, externalLinks } from '$lib/identity';
	import Icon from './Icon.svelte';

	let isOpen = $state(false);
	let theme: 'dark' | 'light' = $state('dark');
	let mounted = $state(false);

	const applyTheme = (t: 'dark' | 'light') => {
		if (typeof document === 'undefined') return;
		document.documentElement.classList.toggle('dark', t === 'dark');
	};

	const toggle = () => {
		theme = theme === 'dark' ? 'light' : 'dark';
		applyTheme(theme);
		try {
			localStorage.setItem('theme', theme);
		} catch {}
	};

	onMount(() => {
		try {
			const saved = localStorage.getItem('theme');
			if (saved === 'dark' || saved === 'light') theme = saved;
			else
				theme =
					(window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? true) ? 'dark' : 'light';
		} catch {}
		applyTheme(theme);
		mounted = true;
	});
</script>

<nav
	class="fixed left-1/2 top-4 z-40 w-[min(96%,1180px)] -translate-x-1/2 border border-ghost-200/60 bg-white/85 px-4 py-2 shadow-lg backdrop-blur-md transition-colors dark:border-ink-600/60 dark:bg-ink-900/70 sm:px-5 {isOpen
		? 'rounded-2xl'
		: 'rounded-full'}"
	aria-label="Primary"
>
	<div class="flex items-center justify-between gap-3">
		<a
			href="/"
			class="group flex items-center gap-2 font-mono text-xs font-semibold tracking-wider text-ghost-500 transition-colors hover:text-ink-900 dark:hover:text-white"
		>
			<span
				class="inline-flex h-6 w-6 items-center justify-center rounded-md bg-ink-900 font-bold leading-none text-neon-cyan ring-1 ring-neon-cyan/30 dark:bg-ink-700"
				>~</span
			>
			<span class="hidden sm:inline">{identity.handle}@{identity.host}</span>
			<span class="hidden text-neon-cyan sm:inline" style="animation: var(--animate-blink);">▌</span>
		</a>

		<div class="hidden items-center gap-1 md:flex">
			{#each externalLinks as link}
				<a
					href={link.url}
					class="rounded-full px-3 py-1.5 font-mono text-xs uppercase tracking-[0.18em] text-ghost-500 transition-colors hover:bg-ghost-100/60 hover:text-ink-900 dark:hover:bg-ink-700/60 dark:hover:text-white"
				>
					{link.label} ↗
				</a>
			{/each}
		</div>

		<div class="flex items-center gap-1.5">
			<button
				onclick={toggle}
				type="button"
				class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-ghost-200/70 bg-white/80 text-ghost-500 transition hover:text-ink-900 dark:border-ink-600/70 dark:bg-ink-800/70 dark:hover:text-white"
				aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
			>
				{#if mounted}<Icon name={theme === 'dark' ? 'moon' : 'sun'} />{/if}
			</button>

			<button
				onclick={() => (isOpen = !isOpen)}
				type="button"
				class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-ghost-200/70 bg-white/80 text-ghost-500 transition hover:text-ink-900 dark:border-ink-600/70 dark:bg-ink-800/70 dark:hover:text-white md:hidden"
				aria-label="Toggle navigation"
				aria-expanded={isOpen}
			>
				<Icon name={isOpen ? 'close' : 'menu'} />
			</button>
		</div>
	</div>

	{#if isOpen}
		<div class="mt-3 flex flex-col gap-1 md:hidden">
			{#each externalLinks as link}
				<a
					href={link.url}
					class="rounded-lg px-3 py-2 font-mono text-sm text-ghost-500 transition hover:bg-ghost-100/60 hover:text-ink-900 dark:hover:bg-ink-700/60 dark:hover:text-white"
					>~/<span class="text-neon-cyan">{link.label.toLowerCase()}</span> ↗</a
				>
			{/each}
		</div>
	{/if}
</nav>
