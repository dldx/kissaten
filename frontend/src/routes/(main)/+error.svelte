<script lang="ts">
	import { page } from "$app/state";
	import { Button } from "$lib/components/ui/button/index.js";
	import { AlertCircle, Home, ArrowLeft } from "lucide-svelte";

	console.error("[Error Boundary]", {
		status: $page.status,
		error: $page.error,
		url: $page.url.pathname,
	});
</script>

<svelte:head>
	<title>Error - Kissaten</title>
</svelte:head>

<div class="mx-auto px-4 py-16 container">
	<div class="space-y-6 mx-auto max-w-2xl text-center">
		<div class="flex justify-center">
			<AlertCircle class="w-20 h-20 text-destructive" />
		</div>

		<h1 class="font-bold text-4xl">
			{$page.status === 404 ? "Page Not Found" : "Something Went Wrong"}
		</h1>

		<p class="text-muted-foreground text-xl">
			{$page.error?.message || "An unexpected error occurred"}
		</p>

		{#if $page.status === 404}
			<p class="text-muted-foreground">
				The coffee bean or page you're looking for doesn't exist. It may
				have been removed or the URL might be incorrect.
			</p>
		{:else}
			<p class="text-muted-foreground">
				We've logged the error and will investigate. Please try again or
				return to the home page.
			</p>
		{/if}

		<div class="flex justify-center gap-4 pt-4">
			<Button onclick={() => history.back()} variant="outline">
				<ArrowLeft class="mr-2 w-4 h-4" />
				Go Back
			</Button>
			<Button href="/">
				<Home class="mr-2 w-4 h-4" />
				Go Home
			</Button>
		</div>

		{#if $page.status !== 404}
			<details class="bg-muted mt-8 p-4 rounded-lg text-left">
				<summary class="font-semibold cursor-pointer"
					>Technical Details</summary
				>
				<pre
					class="mt-2 overflow-x-auto text-sm">{JSON.stringify(
						{
							status: $page.status,
							message: $page.error?.message,
							url: $page.url.pathname,
						},
						null,
						2,
					)}</pre>
			</details>
		{/if}
	</div>
</div>
