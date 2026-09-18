<script lang="ts">
	import { page } from "$app/state";
	import { WifiOff, AlertCircle, RotateCw, Home } from "lucide-svelte";
	import { onMount } from "svelte";
	import {
		ROUTE_MODULE_ERROR_MESSAGE,
		createModuleLoadReloader,
	} from "$lib/offline/routeModuleError";

	const moduleLoadFailed = $derived(page.error?.message === ROUTE_MODULE_ERROR_MESSAGE);
	const moduleReloader = createModuleLoadReloader(() => moduleLoadFailed);

	// Root error page — the fallback SvelteKit's client router renders when a
	// `__data.json` fetch fails (e.g. client-side navigation to a route that
	// was never cached; see the spike notes in `service-worker.ts`). Rendered
	// WITHOUT the (main) layout (no header/footer) so the page is
	// self-contained offline and online.
	let isOffline = $state(
		typeof navigator !== "undefined" && !navigator.onLine,
	);

	onMount(() => {
		const update = () => {
			isOffline = !navigator.onLine;
		};
		const handleOnline = () => {
			update();
			moduleReloader.onOnline();
		};
		window.addEventListener("online", handleOnline);
		window.addEventListener("offline", update);
		moduleReloader.onMount();
		return () => {
			window.removeEventListener("online", handleOnline);
			window.removeEventListener("offline", update);
		};
	});

	const offlineish = $derived(
		isOffline || (page.error?.message ?? "").toLowerCase().includes("offline"),
	);
</script>

<svelte:head>
	<title>Error | Kissaten</title>
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<div
	class="flex justify-center items-center bg-background text-foreground min-h-screen p-4"
	style="font-family: system-ui, -apple-system, sans-serif;"
>
	<div class="text-center max-w-xl">
		{#if offlineish}
			<WifiOff class="mx-auto mb-4 w-16 h-16 text-amber-500" />
			<h1 class="mb-3 font-bold text-3xl">You're offline</h1>
			<p class="mb-6 text-muted-foreground">
				This route isn't cached yet. Reconnect or go back to a page you
				visited.
			</p>
			<div class="flex justify-center gap-3">
				<button
					type="button"
					onclick={() => location.reload()}
					class="inline-flex items-center gap-2 bg-foreground text-background px-4 py-2 rounded-md text-sm font-medium"
					><RotateCw class="w-4 h-4" /> Try Again</button
				>
				<button
					type="button"
					onclick={() => (window.location.href = "/")}
					class="inline-flex items-center gap-2 border border-foreground/20 px-4 py-2 rounded-md text-sm font-medium"
					><Home class="w-4 h-4" /> Go Home</button
				>
			</div>
		{:else}
			<AlertCircle class="mx-auto mb-4 w-16 h-16 text-destructive" />
			<h1 class="mb-3 font-bold text-3xl">
				{moduleLoadFailed ? "Page could not load" : page.status === 404 ? "Page Not Found" : "Something Went Wrong"}
			</h1>
			<p class="mb-6 text-muted-foreground">
				{page.error?.message || "An unexpected error occurred"}
			</p>
			<div class="flex justify-center gap-3">
				{#if moduleLoadFailed}
					<button
						type="button"
						onclick={() => location.reload()}
						class="inline-flex items-center gap-2 border border-foreground/20 px-4 py-2 rounded-md text-sm font-medium"
					><RotateCw class="w-4 h-4" /> Reload page</button>
				{/if}
				<button
					type="button"
					onclick={() => history.back()}
					class="inline-flex items-center gap-2 border border-foreground/20 px-4 py-2 rounded-md text-sm font-medium"
					>Go Back</button
				>
				<button
					type="button"
					onclick={() => (window.location.href = "/")}
					class="inline-flex items-center gap-2 bg-foreground text-background px-4 py-2 rounded-md text-sm font-medium"
					><Home class="w-4 h-4" /> Go Home</button
				>
			</div>
		{/if}
	</div>
</div>