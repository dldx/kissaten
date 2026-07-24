<script lang="ts">
	import { onMount, onDestroy, type Snippet } from "svelte";
	import { STATUS, LoaderState } from "./loaderState.svelte";
	import { debugLog, debugWarn } from "$lib/utils/debugLog";

	type InfiniteLoaderProps = {
		triggerLoad: () => Promise<void>;
		loopTimeout?: number;
		loopDetectionTimeout?: number;
		loopMaxCalls?: number;
		intersectionOptions?: Partial<IntersectionObserverInit>;
		loaderState: LoaderState;
		children: Snippet;
		loading?: Snippet;
		noResults?: Snippet;
		noData?: Snippet;
		coolingOff?: Snippet;
		error?: Snippet<[typeof attemptLoad]>;
	};

	const {
		triggerLoad,
		loopTimeout = 3000,
		loopDetectionTimeout = 2000,
		loopMaxCalls = 5,
		intersectionOptions = {},
		loaderState,
		children,
		loading: loadingSnippet,
		noResults: noResultsSnippet,
		noData: noDataSnippet,
		coolingOff: coolingOffSnippet,
		error: errorSnippet,
		...rest
	}: InfiniteLoaderProps = $props();

	const ERROR_INFINITE_LOOP = `Attempted to execute load function ${loopMaxCalls} or more times within a short period. Please wait before trying again..`;

	// Track load counts to avoid infinite loops
	class LoopTracker {
		coolingOff = $state(false);
		#coolingOffTimer: number | null = null;
		#timer: number | null = null;
		#count = 0;

		// On each call, increment the count and reset the timer
		track() {
			this.#count += 1;
			debugLog("InfiniteLoader", "LoopTracker.track count=", this.#count);

			clearTimeout(this.#timer!);
			// Cooldown, after 2s, reset count to 0
			this.#timer = setTimeout(() => {
				debugLog("InfiniteLoader", "LoopTracker idle-resets count to 0");
				this.#count = 0;
			}, loopDetectionTimeout);

			// If count > loopMaxCalls, begin cool-down period
			// and start timer to reset loop count tracker
			if (this.#count >= loopMaxCalls) {
				console.error(ERROR_INFINITE_LOOP);
				this.coolingOff = true;
				debugWarn("InfiniteLoader", "LoopTracker cooling-off STARTED for", loopTimeout, "ms");
				this.#coolingOffTimer = setTimeout(() => {
					this.coolingOff = false;
					this.#count = 0;
					debugLog("InfiniteLoader", "LoopTracker cooling-off ENDED");
				}, loopTimeout);
			}
		}

		destroy() {
			if (this.#timer) {
				clearTimeout(this.#timer);
			}
			if (this.#coolingOffTimer) {
				clearTimeout(this.#coolingOffTimer);
			}
		}
	}

	const loopTracker = new LoopTracker();

	let intersectionTarget = $state<HTMLElement>();
	let observer = $state<IntersectionObserver>();

	let showLoading = $derived(loaderState.status === STATUS.LOADING);
	let showError = $derived(loaderState.status === STATUS.ERROR);
	let showNoResults = $derived(loaderState.status === STATUS.COMPLETE && loaderState.isFirstLoad);
	let showNoData = $derived(loaderState.status === STATUS.COMPLETE && !loaderState.isFirstLoad);
	let showCoolingOff = $derived(loaderState.status !== STATUS.COMPLETE && loopTracker.coolingOff);

	// Plain (non-reactive) closure var for tracking the previous status value
	// across `$effect` runs so we can log transitions without re-triggering it.
	let prevStatus: string | null = null;

	async function attemptLoad() {
		// If we're complete, don't attempt to load again
		// If we're not ready (i.e. in the middle of a fetch) don't attempt to load again
		// However, if we're in an error state, allow the user to retry via btn click
		if (
			loaderState.status === STATUS.COMPLETE ||
			(loaderState.status !== STATUS.READY && loaderState.status !== STATUS.ERROR)
		) {
			debugLog("InfiniteLoader", "attemptLoad early-return: status=", loaderState.status, "mounted=", loaderState.mounted);
			return;
		}

		debugLog("InfiniteLoader", "attemptLoad: status=", loaderState.status, "-> LOADING");
		loaderState.status = STATUS.LOADING;

		// Skip loading if we're in infinite loop cool-off
		if (!loopTracker.coolingOff) {
			try {
				await triggerLoad();
			} catch (err) {
				debugWarn("InfiniteLoader", "triggerLoad threw:", err, "current status=", loaderState.status);
				throw err;
			}
			loopTracker.track();
		} else {
			debugLog("InfiniteLoader", "attemptLoad: skipping triggerLoad (cooling-off active)");
		}

		// @ts-expect-error - client can set status to 'COMPLETE' inside the
		// `triggerLoad` fn above via `loaderState.complete()`, TS obviously doesn't know this.
		if (loaderState.status !== STATUS.ERROR && loaderState.status !== STATUS.COMPLETE) {
			if (loaderState.status === STATUS.LOADING) {
				loaderState.isFirstLoad = false;
				loaderState.status = STATUS.READY;
				debugLog("InfiniteLoader", "attemptLoad: settled status -> READY");
			}
		} else {
			debugLog("InfiniteLoader", "attemptLoad: post-triggerLoad status=", loaderState.status);
		}
	}

	onMount(() => {
		if (observer || !intersectionTarget) {
			debugWarn("InfiniteLoader", "onMount: skipping observer setup", "observer=", !!observer, "target=", !!intersectionTarget);
			return;
		}

		const appliedIntersectionOptions = {
			rootMargin: "0px 0px 200px 0px",
			...intersectionOptions
		};
		debugLog("InfiniteLoader", "onMount: creating IntersectionObserver with", appliedIntersectionOptions);
		observer = new IntersectionObserver(async (entries) => {
			const entry = entries[0];
			if (entry?.isIntersecting && loaderState.mounted) {
				debugLog("InfiniteLoader", "observer: intersecting + mounted -> attemptLoad", "status=", loaderState.status);
				await attemptLoad();
			} else {
				debugLog("InfiniteLoader", "observer: skip", "isIntersecting=", entry?.isIntersecting, "mounted=", loaderState.mounted);
			}
		}, appliedIntersectionOptions);
		observer.observe(intersectionTarget);

		loaderState.mounted = true;
		debugLog("InfiniteLoader", "onMount: observer attached, mounted=true");
	});

	$effect(() => {
		const status = loaderState.status;
		if (prevStatus !== null && prevStatus !== status) {
			debugLog("InfiniteLoader", "status transition:", prevStatus, "->", status);
		}
		prevStatus = status;
	});

	onDestroy(() => {
		debugLog("InfiniteLoader", "onDestroy: mounted=", loaderState.mounted);
		if (loaderState.mounted) {
			if (observer) {
				observer.disconnect();
				debugLog("InfiniteLoader", "onDestroy: observer disconnected");
			}
			if (loopTracker) {
				loopTracker.destroy();
				debugLog("InfiniteLoader", "onDestroy: loopTracker destroyed");
			}
		}
	});
</script>

<div class="infinite-loader-wrapper">
	<!-- Render the users list items -->
	{@render children()}

	<div class="infinite-intersection-target" bind:this={intersectionTarget}>
		{#if showLoading}
			{#if loadingSnippet}
				{@render loadingSnippet()}
			{:else}
				<div class="infinite-loading">Loading...</div>
			{/if}
		{/if}

		{#if showNoResults}
			{#if noResultsSnippet}
				{@render noResultsSnippet()}
			{:else}
				<div class="infinite-no-results">No results</div>
			{/if}
		{/if}

		{#if showNoData}
			{#if noDataSnippet}
				{@render noDataSnippet()}
			{:else}
				<div class="infinite-no-data">No more data</div>
			{/if}
		{/if}

		{#if showCoolingOff}
			{#if coolingOffSnippet}
				{@render coolingOffSnippet()}
			{:else}
				<div class="infinite-cooling-off">Potential loop detected, please wait and try again..</div>
			{/if}
		{/if}

		{#if showError}
			{#if errorSnippet}
				{@render errorSnippet(attemptLoad)}
			{:else}
				<div class="infinite-error">
					<div class="infinite-error__label">Oops, something went wrong</div>
					<button
						class="infinite-error__btn"
						disabled={loaderState.status === STATUS.COMPLETE}
						onclick={attemptLoad}
					>
						Retry
					</button>
				</div>
			{/if}
		{/if}
	</div>
</div>

<style>
	.infinite-loader-wrapper {
		width: 100%;
	}

	.infinite-loading {
		font-size: 1rem;
		color: hsl(var(--muted-foreground));
	}

	.infinite-no-results {
		font-size: 1rem;
		color: hsl(var(--muted-foreground));
	}

	.infinite-no-data {
		font-size: 1rem;
		color: hsl(var(--muted-foreground));
	}

	.infinite-cooling-off {
		font-size: 0.875rem;
		color: hsl(var(--muted-foreground));
	}

	.infinite-error {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		font-size: 1rem;
		margin-block: 1rem;
	}

	.infinite-error__label {
		color: hsl(var(--destructive));
	}

	.infinite-error__btn {
		color: hsl(var(--primary-foreground));
		background-color: hsl(var(--primary));
		padding-inline: 1.5rem;
		padding-block: 0.75rem;
		border-radius: calc(var(--radius) - 2px);
		border: none;
		transition: background-color 0.3s;
		line-height: normal;
		cursor: pointer;
	}

	.infinite-error__btn:hover {
		background-color: hsl(var(--primary) / 0.9);
	}

	.infinite-error__btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.infinite-intersection-target {
		width: 100%;
		min-height: 1px;
		display: flex;
		padding-block: 2rem;
		flex-direction: column;
		align-items: center;
		justify-content: center;
	}
</style>
