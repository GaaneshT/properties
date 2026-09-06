<script lang="ts">
	import { page } from '$app/stores';
	import { identity, navLinks } from '$lib/identity';
	import { base, resolve } from '$app/paths';
</script>

<div class="bar">
	<!-- External portfolio URL is supplied by the shared identity module. -->
	<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
	<a href={identity.portfolio} class="me">{identity.name}</a>
	<nav class="nav" aria-label="Primary">
		{#each navLinks as link (link.url)}
			{#if link.external}
				<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
				<a href={link.url}>{link.label}</a>
			{:else}
				<a
					href={resolve(link.url as '/' | '/recent' | '/house')}
					class:here={$page.url.pathname === `${base}${link.url}`}
					aria-current={$page.url.pathname === `${base}${link.url}` ? 'page' : undefined}
					>{link.label}</a
				>
			{/if}
		{/each}
	</nav>
</div>
