<script lang="ts">
  // Inline SVG icon set. Keeps the toolbelt dependency-free of icon libs.
  let { name, size = 16, class: className = '' }: { name: string; size?: number | string; class?: string } = $props();
</script>

<svg
  xmlns="http://www.w3.org/2000/svg"
  viewBox="0 0 24 24"
  width={size}
  height={size}
  fill="none"
  stroke="currentColor"
  stroke-width="1.8"
  stroke-linecap="round"
  stroke-linejoin="round"
  class={className}
  aria-hidden="true"
>
  {#if name === 'home'}
    <path d="M3 9.5 12 3l9 6.5V21a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1V9.5Z"/>
  {:else if name === 'search'}
    <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
  {:else if name === 'terminal'}
    <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
  {:else if name === 'menu'}
    <line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/>
  {:else if name === 'close'}
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  {:else if name === 'sun'}
    <circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/><line x1="4.93" y1="4.93" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.07" y2="19.07"/><line x1="4.93" y1="19.07" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.07" y2="4.93"/>
  {:else if name === 'moon'}
    <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z"/>
  {:else if name === 'copy'}
    <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
  {:else if name === 'check'}
    <polyline points="20 6 9 17 4 12"/>
  {:else if name === 'hash'}
    <line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>
  {:else if name === 'braces'}
    <path d="M8 3a4 4 0 0 0-4 4v3a2 2 0 0 1-2 2 2 2 0 0 1 2 2v3a4 4 0 0 0 4 4"/><path d="M16 21a4 4 0 0 0 4-4v-3a2 2 0 0 1 2-2 2 2 0 0 1-2-2V7a4 4 0 0 0-4-4"/>
  {:else if name === 'key'}
    <circle cx="8" cy="15" r="4"/><line x1="10.85" y1="12.15" x2="21" y2="2"/><line x1="18" y1="5" x2="20" y2="7"/><line x1="15" y1="8" x2="17" y2="10"/>
  {:else if name === 'shield'}
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>
  {:else if name === 'regex'}
    <path d="M3 21h6"/><path d="M6 21V9"/><line x1="3.5" y1="14" x2="8.5" y2="11"/><line x1="3.5" y1="11" x2="8.5" y2="14"/><circle cx="18" cy="19" r="2"/>
  {:else if name === 'chart'}
    <line x1="4" y1="20" x2="20" y2="20"/><polyline points="4 16 8 12 12 14 20 6"/><polyline points="14 6 20 6 20 12"/>
  {:else if name === 'image'}
    <rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><polyline points="21 15 16 10 5 21"/>
  {:else if name === 'file'}
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><polyline points="14 2 14 8 20 8"/>
  {:else if name === 'arrow-right'}
    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
  {:else if name === 'download'}
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
  {:else if name === 'upload'}
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  {:else if name === 'external'}
    <path d="M14 4h6v6"/><line x1="20" y1="4" x2="10" y2="14"/><path d="M20 14v6h-6m0-16H4v16h6"/>
  {/if}
</svg>
