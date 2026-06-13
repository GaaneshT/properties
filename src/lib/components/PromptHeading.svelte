<script lang="ts">
  let {
    path,
    command = null,
    user = 'gaanesh',
    host = 'tools',
    children
  }: {
    path: string;
    command?: string | null;
    user?: string;
    host?: string;
    children?: import('svelte').Snippet;
  } = $props();
</script>

<div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
  <h2 class="prompt-heading">
    <span class="user">{user}</span><span class="at">@</span><span class="host">{host}</span>
    <span class="text-ghost-400 dark:text-ghost-500"> ~/</span><span class="path">{path}</span>
    <span class="sign"> $</span>
    {#if command}<span class="cmd"> {command}</span>{/if}
  </h2>
  {#if children}
    <div class="font-mono text-xs text-ghost-400 dark:text-ghost-500">{@render children()}</div>
  {/if}
</div>
