<script lang="ts">
	import { onMount } from 'svelte';
	import type { CameraId, ThemeId } from '$lib/house/catalog';
	import type { createViewer } from '$lib/house/viewer';
	let { theme, camera, onfallback }: { theme: ThemeId; camera: CameraId; onfallback: () => void } =
		$props();
	let host: HTMLDivElement;
	let viewer = $state<ReturnType<typeof createViewer> | null>(null);
	let loading = $state(true);
	let progress = $state(0);
	let error = $state('');
	let exposure = $state(1.1);
	onMount(() => {
		let cancelled = false;
		void import('$lib/house/viewer')
			.then(({ createViewer }) => {
				if (cancelled) return;
				try {
					viewer = createViewer(host, (state) => {
						loading = state.loading;
						progress = state.progress;
						error = state.error;
					});
				} catch {
					loading = false;
					error =
						'3D needs a browser with WebGL 2 graphics enabled. You can still explore every Blender render.';
				}
			})
			.catch(() => {
				loading = false;
				error = 'The 3D viewer could not be loaded. Please check your connection.';
			});
		return () => {
			cancelled = true;
			viewer?.dispose();
		};
	});
	$effect(() => {
		if (viewer) void viewer.load(theme);
	});
	$effect(() => {
		viewer?.setCamera(camera);
	});
	$effect(() => {
		viewer?.setExposure(exposure);
	});
</script>

<div class="explorer">
	<div class="canvas-host" bind:this={host}></div>
	{#if loading || error}
		<div class="viewer-status" role="status" aria-live="polite">
			{#if error}
				<span class="status-symbol">◇</span>
				<h3>Keep exploring in renders</h3>
				<p>{error}</p>
				<button onclick={onfallback}>View Blender renders ↗</button>
			{:else}
				<span class="loading-ring"></span>
				<h3>Opening your house</h3>
				<p>Loading the {theme.replaceAll('-', ' ')} model · about 16 MB</p>
				<progress max="100" value={progress} aria-label="Model download"></progress>
				<span class="progress-label">{progress < 95 ? `${progress}%` : 'Preparing materials…'}</span
				>
			{/if}
		</div>
	{:else}
		<div class="live-label"><i></i> INTERACTIVE 3D <span>Browser lighting</span></div>
		<div class="viewer-help">Drag to look · scroll to move closer · select a space below</div>
		<div class="viewer-controls" aria-label="3D camera controls">
			<button onclick={() => viewer?.rotate(-1)} aria-label="Rotate view left">↶</button>
			<button onclick={() => viewer?.rotate(1)} aria-label="Rotate view right">↷</button>
			<button onclick={() => viewer?.zoom(0.8)} aria-label="Zoom in">+</button>
			<button onclick={() => viewer?.zoom(1.25)} aria-label="Zoom out">−</button>
			<button onclick={() => viewer?.setCamera(camera)}>Reset view</button>
			<label
				>Exposure <input type="range" min="0.5" max="2" step="0.05" bind:value={exposure} /></label
			>
		</div>
	{/if}
</div>

<style>
	.explorer {
		position: relative;
		width: 100%;
		height: 100%;
		min-height: 420px;
		background: #141816;
	}
	.canvas-host {
		position: absolute;
		inset: 0;
		overflow: hidden;
	}
	.canvas-host :global(canvas) {
		display: block;
		width: 100%;
		height: 100%;
		touch-action: none;
	}
	.viewer-status {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: 28px;
		background: #141816e8;
	}
	h3 {
		font-size: 25px;
		font-weight: 400;
		color: #f5efe4;
		margin: 18px 0 8px;
	}
	p {
		max-width: 440px;
		font-size: 14px;
		color: #b8b3a7;
	}
	button {
		cursor: pointer;
		color: #eee6d8;
		border: 1px solid #ffffff25;
		background: #1f2420;
		padding: 8px 12px;
		font-size: 13px;
	}
	button:hover {
		background: #34382d;
	}
	.viewer-status button {
		margin-top: 18px;
	}
	.status-symbol {
		color: #c3a771;
		font-size: 38px;
	}
	.loading-ring {
		width: 32px;
		height: 32px;
		border: 1px solid #c3a77140;
		border-top-color: #c3a771;
		border-radius: 50%;
		animation: spin 1.2s linear infinite;
	}
	progress {
		width: min(260px, 90%);
		height: 3px;
		margin-top: 22px;
		accent-color: #c3a771;
	}
	.progress-label {
		font-size: 12px;
		color: #b8b3a7;
		margin-top: 8px;
	}
	.live-label {
		position: absolute;
		top: 20px;
		left: 20px;
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 10px;
		letter-spacing: 0.1em;
		padding: 8px 10px;
		background: #101410e6;
	}
	.live-label i {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: #c6ba8e;
	}
	.live-label span {
		color: #c0bbae;
		letter-spacing: 0;
		margin-left: 7px;
	}
	.viewer-help {
		position: absolute;
		left: 20px;
		bottom: 68px;
		font-size: 11px;
		color: #eee6d8;
		padding: 5px 8px;
		background: #101410d9;
	}
	.viewer-controls {
		position: absolute;
		bottom: 16px;
		left: 16px;
		right: 16px;
		display: flex;
		gap: 4px;
		flex-wrap: wrap;
		align-items: center;
	}
	label {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 10px;
		background: #101410e6;
		font-size: 11px;
		margin-left: auto;
	}
	input {
		width: 85px;
		accent-color: #c3a771;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (max-width: 600px) {
		.explorer {
			min-height: 450px;
		}
		.viewer-help {
			bottom: 108px;
			right: 16px;
		}
		label {
			margin-left: 0;
		}
	}
</style>
