<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { page } from '$app/stores';
	import { afterNavigate, replaceState } from '$app/navigation';
	import HouseViewer from '$lib/components/HouseViewer.svelte';
	import type { NavigationMode } from '$lib/house/navigation';
	import {
		themes,
		views,
		groups,
		asset,
		isTheme,
		isCamera,
		type ThemeId,
		type CameraId,
		type ViewMode
	} from '$lib/house/catalog';
	let theme = $state<ThemeId>('dark-luxe');
	let comparison = $state<ThemeId>('warm-japandi');
	let camera = $state<CameraId>('C01');
	let navigation = $state<NavigationMode>('orbit');
	let mode = $state<ViewMode>('render');
	let group = $state('All spaces');
	let split = $state(50);
	let ready = $state(false);
	let imageError = $state(false);
	let imageLoading = $state(true);
	let imageAttempt = $state(0);
	let message = $state('');
	let stage: HTMLDivElement;
	let fullscreen = $state(false);
	const selectedTheme = $derived(themes.find((item) => item.id === theme)!);
	const selectedView = $derived(views.find((item) => item.id === camera)!);
	const compareTheme = $derived(themes.find((item) => item.id === comparison)!);
	const filteredViews = $derived(
		views.filter((item) => group === 'All spaces' || item.group === group)
	);
	const imageUrl = $derived(asset(theme, camera, mode === 'compare' ? '-compare' : ''));
	const secondaryUrl = $derived(asset(comparison, camera, '-compare'));

	onMount(() => {
		const params = new URLSearchParams(window.location.search);
		const savedTheme = params.get('theme');
		const savedCamera = params.get('view');
		const savedComparison = params.get('with');
		const savedMode = params.get('mode');
		if (isTheme(savedTheme)) theme = savedTheme;
		if (isCamera(savedCamera)) camera = savedCamera;
		if (isTheme(savedComparison)) comparison = savedComparison;
		if (['render', 'compare', 'explore'].includes(savedMode ?? '')) mode = savedMode as ViewMode;
		navigation =
			params.get('navigation') === 'walk' ||
			(mode === 'explore' && !['C01', 'C02', 'C13', 'C14'].includes(camera))
				? 'walk'
				: 'orbit';
		if (comparison === theme) comparison = themes.find((item) => item.id !== theme)!.id;
		const changed = () => {
			fullscreen = document.fullscreenElement === stage;
		};
		document.addEventListener('fullscreenchange', changed);
		return () => document.removeEventListener('fullscreenchange', changed);
	});
	// replaceState needs the router. During hydration SvelteKit has not yet
	// assigned its root component, so syncing the URL from onMount threw
	// "Cannot read properties of undefined (reading '$set')". afterNavigate
	// first fires once the initial navigation has finished.
	afterNavigate(() => {
		ready = true;
	});
	$effect(() => {
		if (!ready) return;
		const next = { theme, camera, mode, navigation, comparison };
		// Shallow routing updates page.state but never page.url, so compare with
		// the real address bar. Reading $page here would re-run this effect after
		// every replaceState and loop (effect_update_depth_exceeded).
		untrack(() => {
			const url = new URL(window.location.href);
			url.searchParams.set('theme', next.theme);
			url.searchParams.set('view', next.camera);
			url.searchParams.set('mode', next.mode);
			if (next.mode === 'explore') url.searchParams.set('navigation', next.navigation);
			else url.searchParams.delete('navigation');
			if (next.mode === 'compare') url.searchParams.set('with', next.comparison);
			else url.searchParams.delete('with');
			// This URL already includes the deployed base path; resolving it again would duplicate it.
			// eslint-disable-next-line svelte/no-navigation-without-resolve
			if (url.href !== window.location.href) replaceState(url, $page.state);
		});
	});
	$effect(() => {
		void imageUrl;
		void secondaryUrl;
		void imageAttempt;
		imageError = false;
		imageLoading = true;
	});

	function chooseTheme(next: ThemeId) {
		if (comparison === next) comparison = theme;
		theme = next;
	}
	function chooseCamera(id: CameraId) {
		camera = id;
		navigation = ['C01', 'C02', 'C13', 'C14'].includes(id) ? 'orbit' : 'walk';
	}
	function goOverview() {
		camera = 'C01';
		navigation = 'orbit';
		mode = 'explore';
	}
	function goWalking() {
		if (['C01', 'C02', 'C13', 'C14'].includes(camera)) camera = 'C03';
		navigation = 'walk';
		mode = 'explore';
	}
	function openExplorer() {
		chooseCamera(camera);
		mode = 'explore';
	}
	function step(direction: number) {
		const index = views.findIndex((item) => item.id === camera);
		chooseCamera(views[(index + direction + views.length) % views.length].id);
		group = 'All spaces';
	}
	async function toggleFullscreen() {
		try {
			if (document.fullscreenElement) await document.exitFullscreen();
			else if (stage.requestFullscreen) await stage.requestFullscreen();
			else
				message =
					'Fullscreen is unavailable in this browser. Open the image below for a larger view.';
		} catch {
			message = 'Fullscreen could not be opened. You can open the image below instead.';
		}
	}
	async function copyLink() {
		try {
			await navigator.clipboard.writeText(window.location.href);
			message = 'Link copied with this theme, room and viewing mode.';
		} catch {
			message = 'Copy the address in your browser to share this view.';
		}
	}
</script>

<svelte:head>
	<title>House Studio | Gaanesh</title>
	<meta
		name="description"
		content="Four furnished Blender concepts for one home. Compare room renders and explore the native house geometry in an interactive 3D viewer."
	/>
	<meta name="robots" content="noindex, nofollow" />
	<meta name="theme-color" content="#101411" />
</svelte:head>

{#snippet icon(name: 'cube' | 'expand' | 'check' | 'close' | 'split')}
	<svg class="icon" viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
		{#if name === 'cube'}<path d="M8 1.8 13.5 5v6L8 14.2 2.5 11V5z M2.5 5 8 8.2 13.5 5 M8 8.2v6" />
		{:else if name === 'expand'}<path d="M2.5 6V2.5H6 M10 2.5h3.5V6 M13.5 10v3.5H10 M6 13.5H2.5V10" />
		{:else if name === 'check'}<path d="m3 8.5 3.2 3L13 4.5" />
		{:else if name === 'close'}<path d="m4 4 8 8 M12 4l-8 8" />
		{:else}<path d="M6 4 2 8l4 4 M10 4l4 4-4 4" />{/if}
	</svg>
{/snippet}

<section class="house-studio" aria-labelledby="studio-title">
	<header class="studio-heading">
		<div>
			<h1 id="studio-title">One floor plan. <em>Four ways.</em></h1>
			<p class="intro">
				Interior design references for a three-bedroom renovation, rendered in Blender and walkable
				in 3D.
			</p>
		</div>
		<div class="property-meta">
			<strong>1,647 <small>sq ft</small></strong>
			<p>Three bedrooms · owner-reported area</p>
		</div>
	</header>

	<div class="studio-grid">
		<div class="view-column">
			<div class="view-toolbar">
				<div class="mode-switch" aria-label="Viewing mode">
					<button
						class:active={mode === 'render'}
						aria-pressed={mode === 'render'}
						onclick={() => (mode = 'render')}><span class="label-long">Blender renders</span><span class="label-short">Renders</span></button
					>
					<button
						class:active={mode === 'compare'}
						aria-pressed={mode === 'compare'}
						onclick={() => (mode = 'compare')}><span class="label-long">Compare themes</span><span class="label-short">Compare</span></button
					>
					<button
						class:active={mode === 'explore'}
						aria-pressed={mode === 'explore'}
						onclick={openExplorer}>{@render icon('cube')} Explore 3D</button
					>
				</div>
				<button class="expand-button" onclick={toggleFullscreen} aria-label="Enter fullscreen"
					>{@render icon('expand')} <span>Expand</span></button
				>
			</div>
			<div class="stage" class:in-fullscreen={fullscreen} bind:this={stage}>
				{#if mode === 'explore'}
					<HouseViewer
						{theme}
						{camera}
						{navigation}
						onfallback={() => (mode = 'render')}
						onoverview={goOverview}
						onwalk={goWalking}
					/>
				{:else}
					{#key imageUrl + secondaryUrl + imageAttempt}
						<div class="render-frame" class:portrait={camera === 'C02'} aria-busy={imageLoading}>
							<img
								class="main-render"
								src={imageUrl}
								alt={`${selectedView.name}, ${selectedView.detail}, in ${selectedTheme.name}. Rendered from the native Blender concept.`}
								fetchpriority="high"
								onload={() => (imageLoading = false)}
								onerror={() => {
									imageError = true;
									imageLoading = false;
								}}
							/>
							{#if mode === 'compare'}
								<div class="compare-overlay" style:clip-path={`inset(0 ${100 - split}% 0 0)`}>
									<img
										src={secondaryUrl}
										alt={`Same ${selectedView.name.toLowerCase()} camera in ${compareTheme.name}`}
										onerror={() => (imageError = true)}
									/>
								</div>
								<input
									class="image-split-control"
									aria-label="Slide across image to compare themes"
									type="range"
									min="0"
									max="100"
									bind:value={split}
									aria-valuetext={`${split}% ${compareTheme.name}`}
								/>
								<div class="split-line" style:left={`${split}%`}><span>{@render icon('split')}</span></div>
								<div class="compare-label left">{compareTheme.name}</div>
								<div class="compare-label right">{selectedTheme.name}</div>
							{:else}
								<div class="image-caption">
									<span>{selectedView.group}</span>
									<h2>{selectedView.name}</h2>
									<p>{selectedView.detail} <b>·</b> {selectedTheme.name}</p>
								</div>
							{/if}
							{#if imageError}<div class="image-error" role="alert">
									<p>This view could not be loaded.</p>
									<button onclick={() => imageAttempt++}>Try again</button>
								</div>{/if}
						</div>
					{/key}
					{#if mode === 'render'}<button class="enter-house" onclick={goWalking}
							>Walk inside ↗</button
						>{/if}
				{/if}
				{#if fullscreen}<button class="exit-fullscreen" onclick={toggleFullscreen}
						>Close fullscreen</button
					>{/if}
			</div>
			<div class="view-info">
				{#if mode === 'compare'}
					<label class="compare-with" for="compare-theme"
						>Compare with <select id="compare-theme" bind:value={comparison}
							>{#each themes.filter((item) => item.id !== theme) as item (item.id)}<option
									value={item.id}>{item.name}</option
								>{/each}</select
						></label
					>
				{/if}
				<div class="pager">
					<button onclick={() => step(-1)} aria-label="Previous room view">←</button><span
						>{String(views.findIndex((item) => item.id === camera) + 1).padStart(2, '0')} / 20</span
					><button onclick={() => step(1)} aria-label="Next room view">→</button>
				</div>
			</div>
		</div>

		<aside class="design-panel" aria-label="Design themes">
			<div class="panel-top">
				<h2>Four material <br />directions.</h2>
				<p>Each is a complete scheme over the same architectural shell.</p>
			</div>
			<div class="theme-list">
				{#each themes as item (item.id)}<button
						class="theme-card"
						class:selected={theme === item.id}
						aria-pressed={theme === item.id}
						onclick={() => chooseTheme(item.id)}
						><span class="theme-content"
							><span class="theme-title"
								>{item.name}{#if theme === item.id}<span class="theme-check">{@render icon('check')}</span>{/if}</span
							><span class="theme-note">{item.note}</span><span class="swatches" aria-hidden="true"
								>{#each item.colors as color (color)}<i style:background={color}></i>{/each}</span
							></span
						></button
					>{/each}
			</div>
			<div class="panel-bottom">
				<button onclick={copyLink}>Copy link to this view <span aria-hidden="true">↗</span></button>
			</div>
		</aside>
	</div>

	<section class="space-section" aria-labelledby="spaces-title">
		<div class="space-heading">
			<h2 id="spaces-title">Room by room.</h2>
			<p>20 viewpoints <span>·</span> 4 concepts</p>
		</div>
		<div class="space-filters" aria-label="Filter spaces">
			{#each groups as item (item)}<button
					class:active={group === item}
					aria-pressed={group === item}
					onclick={() => (group = item)}>{item}</button
				>{/each}
		</div>
		<div class="room-rail">
			{#each filteredViews as item (item.id)}<button
					class="room-card"
					class:selected={camera === item.id}
					aria-pressed={camera === item.id}
					onclick={() => chooseCamera(item.id)}
					><div class="room-image">
						<img src={asset(theme, item.id, '-thumb')} alt="" loading="lazy" /><span
							>{item.kind === 'evening'
								? 'DUSK'
								: item.kind === 'cutaway'
									? 'CUTAWAY'
									: item.kind === 'plan'
										? 'PLAN'
										: 'DAYLIGHT'}</span
						>{#if camera === item.id}<i>VIEWING</i>{/if}
					</div>
					<strong>{item.name}</strong><span class="room-detail">{item.detail}</span></button
				>{/each}
		</div>
	</section>

	<div class="studio-footnote">
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
		<a href={asset(theme, camera)} target="_blank" rel="noreferrer">Open full render ↗</a>
	</div>
	{#if message}<div class="toast" role="status">
			<p>{message}</p>
			<button onclick={() => (message = '')} aria-label="Dismiss message">{@render icon('close')}</button>
		</div>{/if}
</section>

<style>
	.house-studio {
		--gold: #c5ab7c;
		--muted: #aaa99c;
		--line: #ffffff16;
		color: #eceade;
		padding-bottom: 12px;
	}
	.studio-heading {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 24px;
		padding: 30px 0 38px;
	}
	h1 {
		font-family: Georgia, 'Times New Roman', serif;
		font-size: clamp(31px, 3.7vw, 54px);
		line-height: 1.15;
		letter-spacing: -0.045em;
		font-weight: 400;
		margin: 16px 0 13px;
	}
	h1 em {
		font-weight: 400;
		color: #bfc2ad;
	}
	.intro {
		font-size: 15px;
		color: var(--muted);
	}
	.property-meta {
		text-align: right;
		padding-left: 30px;
		border-left: 1px solid var(--line);
		min-width: 156px;
	}
	.property-meta strong {
		display: block;
		font-size: 28px;
		font-weight: 400;
		letter-spacing: -0.04em;
		line-height: 1.5;
	}
	.property-meta small {
		font-size: 14px;
		color: #b8bbab;
		letter-spacing: 0;
	}
	.property-meta p {
		font-size: 12.5px;
		color: #a9ad9d;
	}
	.studio-grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 284px;
		border: 1px solid var(--line);
		background: #151a16;
	}
	.view-column {
		min-width: 0;
		display: flex;
		flex-direction: column;
	}
	.view-toolbar {
		display: flex;
		justify-content: space-between;
		gap: 10px;
		padding: 13px 17px;
		border-bottom: 1px solid var(--line);
	}
	.mode-switch {
		display: flex;
		gap: 3px;
	}
	button {
		cursor: pointer;
		font-family: var(--body);
		transition:
			background 0.2s,
			color 0.2s,
			border-color 0.2s;
	}
	.mode-switch button {
		padding: 9px 12px;
		font-size: 13px;
		display: inline-flex;
		align-items: center;
		gap: 6px;
		color: #b4b7a8;
		white-space: nowrap;
		border: 1px solid transparent;
		border-radius: 3px;
	}
	.mode-switch button:hover {
		color: #f3efdf;
		background: #ffffff06;
	}
	.mode-switch button.active {
		background: #c5ab7c13;
		border-color: #c5ab7c34;
		color: #d4bd96;
	}
	.expand-button {
		color: #c2c6b6;
		font-size: 12.5px;
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 8px;
		border-radius: 3px;
	}
	.stage {
		position: relative;
		background: #0c100d;
		width: 100%;
		flex: 1;
		min-height: 480px;
	}
	.render-frame {
		position: absolute;
		inset: 0;
		overflow: hidden;
	}
	.render-frame::after {
		content: '';
		position: absolute;
		inset: 45% 0 0;
		background: linear-gradient(transparent, #080d08ac);
		pointer-events: none;
	}
	.render-frame:has(.compare-overlay)::after {
		display: none;
	}
	.render-frame img {
		width: 100%;
		height: 100%;
		object-fit: contain;
	}
	.image-caption {
		position: absolute;
		left: 28px;
		bottom: 23px;
		z-index: 2;
		pointer-events: none;
	}
	.image-caption > span {
		font-size: 11px;
		text-transform: uppercase;
		letter-spacing: 0.18em;
		color: #dbd5c4;
	}
	.image-caption h2 {
		font-family: Georgia, serif;
		font-size: 33px;
		line-height: 1.3;
		margin-top: 5px;
		font-weight: 400;
	}
	.image-caption p {
		font-size: 13px;
		color: #ddd7c7;
		margin-top: 4px;
	}
	.image-caption b {
		margin: 0 7px;
		font-weight: 400;
	}
	.view-info {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		padding: 13px 20px;
		gap: 14px;
		border-top: 1px solid var(--line);
	}
	.view-info > div {
		display: flex;
		align-items: center;
		gap: 10px;
		white-space: nowrap;
		margin-left: auto;
	}
	.view-info > div span {
		font-family: var(--font-mono);
		font-size: 12px;
		color: #b9bdab;
	}
	.view-info button {
		font-size: 18px;
		color: #d6cfbb;
		min-width: 36px;
		min-height: 36px;
		border-radius: 3px;
	}
	.design-panel {
		border-left: 1px solid var(--line);
		display: flex;
		flex-direction: column;
		padding: 28px 21px 20px;
		background: linear-gradient(155deg, #1b201a, #141913);
	}
	.panel-top h2 {
		font-family: Georgia, serif;
		font-weight: 400;
		font-size: 27px;
		line-height: 1.15;
		margin: 13px 0;
		letter-spacing: -0.025em;
	}
	.panel-top > p:last-child {
		font-size: 13px;
		color: var(--muted);
		line-height: 1.7;
		max-width: 230px;
	}
	.theme-list {
		display: grid;
		gap: 8px;
		margin: 22px -5px 0;
	}
	.theme-card {
		display: flex;
		text-align: left;
		gap: 0;
		padding: 14px 13px;
		border: 1px solid #ffffff10;
		border-radius: 3px;
		background: #ffffff02;
	}
	.theme-card:hover {
		background: #c5ab7c0a;
		border-color: #c5ab7c50;
	}
	.theme-card.selected {
		border-color: #b89c636e;
		background: #bc9c5c0b;
	}
	.theme-content {
		flex: 1;
	}
	.theme-title {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 14px;
		color: #e0e2d2;
	}
	.theme-check {
		display: inline-flex;
		color: var(--gold);
	}
	.theme-note {
		display: block;
		font-size: 12px;
		line-height: 1.6;
		color: #aeb3a1;
		margin-top: 4px;
	}
	.swatches {
		display: flex;
		gap: 4px;
		margin-top: 11px;
	}
	.swatches i {
		width: 25px;
		height: 13px;
		border: 1px solid #ffffff0c;
		border-radius: 1px;
	}
	.panel-bottom {
		margin-top: auto;
		padding-top: 24px;
	}
	.panel-bottom button {
		border-top: 1px solid var(--line);
		padding-top: 13px;
		width: 100%;
		display: flex;
		justify-content: space-between;
		font-size: 13px;
		color: #cdb58a;
	}
	.space-section {
		padding: 35px 0 0;
	}
	.space-heading {
		display: flex;
		justify-content: space-between;
		align-items: end;
		gap: 15px;
	}
	.space-heading h2 {
		font-family: Georgia, serif;
		font-weight: 400;
		font-size: 29px;
		margin-top: 0;
		letter-spacing: -0.03em;
	}
	.space-heading > p {
		font-size: 12.5px;
		color: #a6af99;
		margin-bottom: 3px;
		white-space: nowrap;
	}
	.space-heading > p span {
		padding: 0 7px;
	}
	.space-filters {
		display: flex;
		gap: 22px;
		margin: 22px 0 19px;
		border-bottom: 1px solid var(--line);
		overflow-x: auto;
	}
	.space-filters button {
		color: #a7af9b;
		font-size: 13px;
		white-space: nowrap;
		padding-bottom: 12px;
		border-bottom: 1px solid transparent;
	}
	.space-filters button.active {
		color: #d6bd91;
		border-color: #c5ab7c;
	}
	.room-rail {
		display: flex;
		gap: 15px;
		overflow-x: auto;
		padding: 0 0 20px;
		scroll-snap-type: x proximity;
		scrollbar-width: thin;
		scrollbar-color: #5b604d #171c15;
	}
	.room-card {
		text-align: left;
		flex: 0 0 196px;
		scroll-snap-align: start;
	}
	.room-image {
		height: 118px;
		overflow: hidden;
		position: relative;
		border: 1px solid #ffffff0c;
		border-radius: 2px;
	}
	.room-image img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		opacity: 0.77;
		transition: opacity 0.2s;
	}
	.room-card:hover img,
	.room-card.selected img {
		opacity: 1;
	}
	.room-card.selected .room-image {
		border-color: #c5ab7c;
	}
	.room-image > span {
		position: absolute;
		bottom: 8px;
		left: 9px;
		font-size: 10.5px;
		letter-spacing: 0.08em;
		color: #eee8d7;
		background: #12160ee0;
		padding: 3px 5px;
	}
	.room-image > i {
		position: absolute;
		top: 8px;
		right: 8px;
		font-style: normal;
		font-size: 10.5px;
		letter-spacing: 0.08em;
		color: #13190d;
		background: #c5ab7c;
		padding: 3px 5px;
	}
	.room-card strong {
		display: block;
		color: #dce0cd;
		font-weight: 400;
		font-size: 14px;
		margin-top: 11px;
	}
	.room-card.selected strong {
		color: #dbc29b;
	}
	.room-detail {
		display: block;
		color: #9ca48e;
		font-size: 12px;
		margin-top: 2px;
	}
	.studio-footnote {
		display: flex;
		gap: 26px;
		justify-content: flex-end;
		align-items: center;
		padding: 22px 0;
		margin-top: 12px;
		border-top: 1px solid var(--line);
	}
	.studio-footnote a {
		color: #c6ad80;
		font-size: 13px;
		white-space: nowrap;
	}
	.compare-with {
		white-space: nowrap;
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 12.5px;
		color: #b7bdaa;
	}
	.compare-with select {
		background: #1c2417;
		color: #e2ddca;
		border: 1px solid #a5ad9040;
		padding: 6px 30px 6px 10px;
		font-family: var(--body);
		font-size: 13px;
		border-radius: 3px;
	}
	.label-short {
		display: none;
	}
	.icon {
		flex-shrink: 0;
		display: block;
	}
	.compare-overlay {
		position: absolute;
		inset: 0;
	}
	.image-split-control {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		margin: 0;
		opacity: 0;
		z-index: 4;
		cursor: ew-resize;
		touch-action: pan-y;
	}
	.image-split-control:focus-visible + .split-line > span {
		outline: 3px solid #fff;
		outline-offset: 4px;
	}
	.split-line {
		position: absolute;
		top: 0;
		bottom: 0;
		width: 1px;
		background: #e9dfc2;
		pointer-events: none;
		z-index: 3;
	}
	.split-line > span {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		display: grid;
		place-items: center;
		width: 40px;
		height: 40px;
		border-radius: 50%;
		background: #151b13e8;
		border: 1px solid #d9cba7;
		font-size: 17px;
		color: #f4e8c6;
	}
	.compare-label {
		position: absolute;
		bottom: 20px;
		z-index: 3;
		background: #141910e8;
		color: #e6d6b6;
		font-size: 12.5px;
		padding: 8px 12px;
	}
	.compare-label.left {
		left: 20px;
	}
	.compare-label.right {
		right: 20px;
	}
	.image-error {
		position: absolute;
		inset: 0;
		z-index: 5;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		background: #141912;
	}
	.image-error button {
		color: #dcc499;
		margin-top: 10px;
		border: 1px solid #c5ab7c60;
		padding: 6px 18px;
	}
	.stage.in-fullscreen {
		width: 100vw;
		height: 100vh;
	}
	.stage.in-fullscreen :global(.travel-switch) {
		top: 66px;
	}
	.enter-house {
		position: absolute;
		right: 24px;
		bottom: 28px;
		z-index: 4;
		padding: 10px 16px;
		background: #1b2319ed;
		border: 1px solid #c5ab7c85;
		color: #e8d1a4;
		font-size: 12px;
	}
	.enter-house:hover {
		background: #3b402e;
	}
	.exit-fullscreen {
		position: absolute;
		top: 20px;
		right: 20px;
		z-index: 10;
		background: #101610e6;
		border: 1px solid #c5ab7c70;
		color: #e5d1ad;
		padding: 8px 16px;
		font-size: 12px;
	}
	.toast {
		position: fixed;
		bottom: 24px;
		left: 50%;
		transform: translateX(-50%);
		width: max-content;
		max-width: calc(100vw - 32px);
		display: flex;
		align-items: center;
		gap: 18px;
		z-index: 50;
		background: #242e1f;
		border: 1px solid #b9a27766;
		color: #e9dfc8;
		padding: 13px 20px;
		font-size: 12px;
		box-shadow: 0 8px 50px #0008;
	}
	.toast button {
		display: grid;
		place-items: center;
		min-width: 32px;
		min-height: 32px;
	}
	@media (min-width: 1450px) {
		.stage {
			min-height: 600px;
		}
	}
	@media (max-width: 1100px) {
		.expand-button span {
			display: none;
		}
		.studio-grid {
			grid-template-columns: minmax(0, 1fr) 248px;
		}
		.design-panel {
			padding: 22px 17px 18px;
		}
		.stage {
			min-height: 430px;
		}
		.view-toolbar {
			padding: 12px;
		}
		.mode-switch button {
			padding: 8px;
		}
	}
	@media (max-width: 850px) {
		.studio-grid {
			grid-template-columns: 1fr;
		}
		.stage {
			min-height: 0;
			aspect-ratio: 16 / 10;
		}
		.stage:has(:global(.explorer)) {
			min-height: 450px;
		}
		.design-panel {
			border-left: 0;
			border-top: 1px solid var(--line);
			padding: 20px;
		}
		.panel-top h2 {
			font-size: 23px;
		}
		.panel-top h2 br {
			display: none;
		}
		.panel-top > p:last-child {
			max-width: none;
		}
		.theme-list {
			grid-template-columns: 1fr 1fr;
			margin: 16px 0 0;
		}
		.panel-bottom {
			display: none;
		}
		.property-meta {
			min-width: 130px;
		}
		.studio-heading {
			padding-top: 24px;
		}
	}
	@media (max-width: 560px) {
		.label-long {
			display: none;
		}
		.label-short {
			display: inline;
		}
		.studio-heading {
			padding: 23px 0 28px;
		}
		.property-meta {
			display: none;
		}
		h1 {
			font-size: 33px;
			max-width: 320px;
		}
		h1 em {
			display: block;
		}
		.intro {
			max-width: 280px;
			font-size: 14px;
		}
		.view-toolbar {
			padding: 10px 7px;
			gap: 3px;
		}
		.mode-switch {
			gap: 2px;
			min-width: 0;
			overflow-x: auto;
			scrollbar-width: none;
		}
		.mode-switch button {
			font-size: 12px;
			padding: 8px 5px;
			gap: 4px;
		}
		.expand-button {
			padding: 0 2px;
		}
		.stage {
			aspect-ratio: 4 / 3;
		}
		.image-caption {
			left: 15px;
			bottom: 13px;
		}
		.image-caption > span {
			font-size: 10.5px;
		}
		.image-caption h2 {
			font-size: 24px;
		}
		.image-caption p {
			font-size: 12px;
		}
		.view-info {
			padding: 10px 12px;
		}
		.view-info > div {
			gap: 6px;
		}
		.theme-card {
			gap: 7px;
			padding: 12px 8px;
		}
		.theme-title {
			font-size: 13px;
		}
		.theme-note {
			font-size: 11.5px;
		}
		.swatches i {
			width: 20px;
		}
		.design-panel {
			padding: 17px 13px;
		}
		.space-heading {
			align-items: start;
		}
		.space-heading h2 {
			font-size: 24px;
			max-width: 220px;
		}
		.space-heading > p {
			font-size: 12px;
			margin-top: 4px;
		}
		.space-filters {
			gap: 18px;
		}
		.space-filters button {
			font-size: 12.5px;
		}
		.room-card {
			flex-basis: 163px;
		}
		.room-image {
			height: 102px;
		}
		.studio-footnote {
			flex-direction: column;
			align-items: start;
			gap: 13px;
		}
		.compare-label {
			font-size: 11.5px;
			padding: 5px 8px;
			bottom: 14px;
		}
		.compare-label.left {
			left: 12px;
		}
		.compare-label.right {
			right: 12px;
		}
	}
</style>
