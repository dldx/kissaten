<script lang="ts">
	import { page } from "$app/state";
	import { Button } from "$lib/components/ui/button/index.js";
	import {
		AlertCircle,
		Home,
		ArrowLeft,
		RotateCw,
		WifiOff,
	} from "lucide-svelte";
	import { onMount } from "svelte";
	import {
		ROUTE_MODULE_ERROR_MESSAGE,
		createModuleLoadReloader,
	} from "$lib/offline/routeModuleError";

	const moduleLoadFailed = $derived(page.error?.message === ROUTE_MODULE_ERROR_MESSAGE);
	const moduleReloader = createModuleLoadReloader(() => moduleLoadFailed);

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

	// "Offline" when the browser says so, or when the error itself mentions
	// offline (e.g. a stream reject from a toppled connection).
	const offlineish = $derived(
		isOffline || (page.error?.message ?? "").toLowerCase().includes("offline"),
	);
</script>

<svelte:head>
	<title>Error | Kissaten</title>
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<div class="mx-auto px-4 py-16 container">
	{#if offlineish}
		<div class="space-y-6 mx-auto max-w-2xl text-center">
			<div class="flex justify-center">
				<WifiOff class="w-20 h-20 text-amber-500" />
			</div>
			<h1 class="font-bold text-4xl">You're offline</h1>
			<p class="text-muted-foreground text-xl">
				This route isn't cached yet. Reconnect or go back to a page you
				visited.
			</p>
			<p class="text-muted-foreground">
				Previously visited pages are available offline with your cached
				data.
			</p>
			<div class="flex justify-center gap-4 pt-4">
				<Button onclick={() => location.reload()} variant="outline">
					<RotateCw class="mr-2 w-4 h-4" />
					Try Again
				</Button>
				<Button href="/">
					<Home class="mr-2 w-4 h-4" />
					Go Home
				</Button>
			</div>
		</div>
	{:else}
		<div class="space-y-6 mx-auto max-w-2xl text-center">
			<div class="flex justify-center">
				<AlertCircle class="w-20 h-20 text-destructive" />
			</div>
			<h1 class="font-bold text-4xl">
				{moduleLoadFailed ? "Page could not load" : page.status === 404 ? "Page Not Found" : "Something Went Wrong"}
			</h1>
			<p class="text-muted-foreground text-xl">
				{page.error?.message || "An unexpected error occurred"}
			</p>
			<div class="flex justify-center gap-4 pt-4">
				{#if moduleLoadFailed}
					<Button onclick={() => location.reload()} variant="outline">
						<RotateCw class="mr-2 w-4 h-4" />
						Reload page
					</Button>
				{/if}
				<Button onclick={() => history.back()} variant="outline">
					<ArrowLeft class="mr-2 w-4 h-4" />
					Go Back
				</Button>
				<Button href="/">
					<Home class="mr-2 w-4 h-4" />
					Go Home
				</Button>
			</div>
		</div>
	{/if}
</div>