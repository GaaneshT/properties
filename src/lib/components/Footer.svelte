<script lang="ts">
	import { footerLinks, copy } from '$lib/identity';
</script>

<footer>
	<div class="wrap">
		<span>{copy.footer}</span>
		<div class="fl">
			{#each footerLinks as link}
				<a href={link.url} target="_blank" rel="noopener noreferrer">{link.label}</a>
			{/each}
		</div>
	</div>
</footer>
