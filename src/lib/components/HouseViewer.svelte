<script lang="ts">
	import { onMount } from 'svelte';
	import type { CameraId, ThemeId } from '$lib/house/catalog';
	import type { createViewer } from '$lib/house/viewer';
	import type { NavigationMode, MoveDirection } from '$lib/house/navigation';
	let {
		theme,
		camera,
		navigation,
		onfallback,
		onoverview,
		onwalk
	}: {
		theme: ThemeId;
		camera: CameraId;
		navigation: NavigationMode;
		onfallback: () => void;
		onoverview: () => void;
		onwalk: () => void;
	} = $props();
	let host: HTMLDivElement;
	let viewer = $state<ReturnType<typeof createViewer> | null>(null);
	let loading = $state(true);
	let progress = $state(0);
	let error = $state('');
	let exposure = $state(1.1);
	let detailed = $state(true);
	let phase = $state('Loading the house');
	const pad: { direction: MoveDirection; symbol: string; label: string }[] = [
		{ direction: 'forward', symbol: '↑', label: 'Move forward' },
		{ direction: 'left', symbol: '←', label: 'Step left' },
		{ direction: 'back', symbol: '↓', label: 'Move backward' },
		{ direction: 'right', symbol: '→', label: 'Step right' }
	];
	onMount(() => {
		detailed = window.innerWidth > 700;
		let cancelled = false;
		void import('$lib/house/viewer')
			.then(({ createViewer }) => {
				if (cancelled) return;
				try {
					viewer = createViewer(host, (state) => {
						loading = state.loading;
						progress = state.progress;
						error = state.error;
						phase = state.phase ?? 'Preparing the view';
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
	$effect(() => {
		viewer?.setNavigation(navigation);
	});
	$effect(() => {
		viewer?.setDetail(detailed);
	});
	function press(event: PointerEvent, direction: MoveDirection) {
		event.preventDefault();
		(event.currentTarget as HTMLButtonElement).setPointerCapture(event.pointerId);
		viewer?.focus();
		viewer?.hold(direction, true);
	}
	function keyboard(event: KeyboardEvent, direction: MoveDirection, value: boolean) {
		if (event.code === 'Space' || event.code === 'Enter') {
			event.preventDefault();
			viewer?.hold(direction, value);
		}
	}
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
				<p>{phase} · {theme.replaceAll('-', ' ')}</p>
				<progress max="100" value={progress} aria-label="Model download"></progress>
				<span class="progress-label">{progress < 95 ? `${progress}%` : 'Preparing materials…'}</span
				>
			{/if}
		</div>
	{:else}
		<div class="live-label"><i></i> TEXTURED 3D</div>
		<div class="travel-switch" aria-label="Move around the house">
			<button
				class:active={navigation === 'orbit'}
				aria-pressed={navigation === 'orbit'}
				onclick={onoverview}>◇ Whole house</button
			>
			<button
				class:active={navigation === 'walk'}
				aria-pressed={navigation === 'walk'}
				onclick={onwalk}>↗ Walk inside</button
			>
		</div>
		<div class="viewer-help">
			{navigation === 'walk'
				? 'WASD / arrows to walk · drag to look · Shift for faster movement'
				: 'Drag to orbit · scroll to zoom · right-drag or two fingers to pan'}
		</div>
		{#if navigation === 'walk'}
			<div class="walk-pad" aria-label="Hold a direction to walk">
				{#each pad as item (item.direction)}<button
						class={item.direction}
						aria-label={item.label}
						onpointerdown={(event) => press(event, item.direction)}
						onpointerup={() => viewer?.hold(item.direction, false)}
						onpointercancel={() => viewer?.hold(item.direction, false)}
						onlostpointercapture={() => viewer?.hold(item.direction, false)}
						onkeydown={(event) => keyboard(event, item.direction, true)}
						onkeyup={(event) => keyboard(event, item.direction, false)}
						onblur={() => viewer?.hold(item.direction, false)}>{item.symbol}</button
					>{/each}
				<span>HOLD TO WALK</span>
			</div>
		{/if}
		<div class="viewer-controls" aria-label="3D camera controls">
			<button onclick={() => viewer?.rotate(-1)} aria-label="Rotate view left">↶</button>
			<button onclick={() => viewer?.rotate(1)} aria-label="Rotate view right">↷</button>
			{#if navigation === 'orbit'}
				<button onclick={() => viewer?.zoom(0.8)} aria-label="Zoom in">+</button>
				<button onclick={() => viewer?.zoom(1.25)} aria-label="Zoom out">−</button>
			{:else}<button onclick={() => viewer?.focus()}>Use keyboard</button>{/if}
			<button onclick={() => viewer?.setCamera(camera)}>Reset view</button>
			<label
				>Exposure <input type="range" min="0.5" max="2" step="0.05" bind:value={exposure} /></label
			>
			<label class="detail-toggle"
				><input type="checkbox" bind:checked={detailed} /> Contact shadows</label
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
	.travel-switch {
		position: absolute;
		top: 16px;
		right: 16px;
		display: flex;
		gap: 4px;
	}
	.travel-switch button {
		font-size: 11px;
		background: #101610e8;
	}
	.travel-switch button.active {
		background: #3b3e2a;
		color: #e6cb97;
		border-color: #c3a771;
	}
	.walk-pad {
		position: absolute;
		bottom: 78px;
		right: 20px;
		display: grid;
		grid-template-columns: repeat(3, 38px);
		grid-template-rows: 38px 38px auto;
		gap: 3px;
	}
	.walk-pad button {
		padding: 0;
		font-size: 21px;
		background: #101610e8;
		touch-action: none;
		user-select: none;
	}
	.walk-pad button:active {
		color: #fff1ce;
		background: #5b5136;
	}
	.walk-pad .forward {
		grid-column: 2;
	}
	.walk-pad .left {
		grid-column: 1;
		grid-row: 2;
	}
	.walk-pad .back {
		grid-column: 2;
		grid-row: 2;
	}
	.walk-pad .right {
		grid-column: 3;
		grid-row: 2;
	}
	.walk-pad span {
		grid-column: 1 / 4;
		text-align: center;
		font-size: 7px;
		letter-spacing: 0.12em;
		color: #d7ceb9;
		background: #101610d9;
		padding: 3px 0;
	}
	.detail-toggle {
		margin-left: 0;
	}
	.detail-toggle input {
		width: auto;
	}
	.viewer-help {
		position: absolute;
		left: 20px;
		bottom: 68px;
		right: 160px;
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
			bottom: 132px;
			right: 154px;
			font-size: 9px;
		}
		.live-label {
			display: none;
		}
		.walk-pad {
			bottom: 128px;
			right: 16px;
		}
		.travel-switch {
			left: 16px;
			justify-content: center;
		}
		.viewer-controls {
			right: 12px;
			gap: 4px;
		}
		.viewer-controls button {
			font-size: 11px;
			padding: 8px;
		}
		label {
			margin-left: 0;
		}
	}
</style>
