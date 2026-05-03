<script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/state";
	import * as Breadcrumb from "$lib/components/ui/breadcrumb";
	import { ChevronLeft } from "lucide-svelte";
	import { getTastingHistory, type TastingSession } from "$lib/db/localdb";
	import { KissatenAPI } from "$lib/api";

	let { children } = $props();

	let tastingHistory = $state<TastingSession[]>([]);
	let roasterName = $state<string>("");

	const api = new KissatenAPI();

	const filterBeanPath = $derived(page.url.searchParams.get("bean"));

	onMount(async () => {
		try {
			const [history, response] = await Promise.all([
				getTastingHistory(),
				api.getRoasters()
			]);
			tastingHistory = history;

			const roasterSlug = page.params.roaster_slug;
			if (roasterSlug) {
				const roasters = response.data || [];
				const roaster = roasters.find(r => r.slug === roasterSlug);
				if (roaster) {
					roasterName = roaster.name;
				}
			}
		} catch (error) {
			console.error("Failed to load tasting history or roasters in breadcrumbs:", error);
		}
	});

	const crumbs = $derived.by(() => {
		const roasterSlug = page.params.roaster_slug;
		const beanSlug = page.params.bean_slug;
		const tastingId = page.params.tasting_id;

		const list = [
			{ name: "History", href: "/tasting/history" }
		];

		if (roasterSlug) {
			const session = tastingHistory.find(t => t.beanUrlPath?.startsWith(`/${roasterSlug}/`));
			const displayRoasterName = roasterName || session?.roasterName || roasterSlug.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
			list.push({ name: displayRoasterName, href: `/tasting/history/${roasterSlug}` });
		}

		if (beanSlug) {
			const currentBeanUrlPath = `/${roasterSlug}/${beanSlug}`;
			const session = tastingHistory.find(t => t.beanUrlPath === currentBeanUrlPath);
			const displayBeanName = session?.beanName || session?.beanLabel || beanSlug.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
			list.push({ name: displayBeanName, href: `/tasting/history/${roasterSlug}/${beanSlug}` });
		}

		if (tastingId) {
			list.push({ name: "Session Detail", href: "" });
		}

		return list;
	});
</script>

<div class="mx-auto px-4 pt-8 max-w-4xl container">
	{#if page.url.pathname === "/tasting/history"}
		<a
			href={filterBeanPath ? `/roasters${filterBeanPath}` : "/tasting"}
			class="flex items-center gap-1 mb-6 text-muted-foreground hover:text-primary text-sm transition-colors"
		>
			<ChevronLeft size={14} />
			{filterBeanPath ? "Back to Coffee Bean" : "Back to Tasting Guide"}
		</a>
	{:else}
		<Breadcrumb.Root class="mb-6">
			<Breadcrumb.List>
				{#each crumbs as crumb, i}
					<Breadcrumb.Item>
						{#if i === crumbs.length - 1 || !crumb.href}
							<Breadcrumb.Page>{crumb.name}</Breadcrumb.Page>
						{:else}
							<Breadcrumb.Link href={crumb.href}>{crumb.name}</Breadcrumb.Link>
						{/if}
					</Breadcrumb.Item>
					{#if i < crumbs.length - 1}
						<Breadcrumb.Separator />
					{/if}
				{/each}
			</Breadcrumb.List>
		</Breadcrumb.Root>
	{/if}
	<div class="mb-12">
		<h1 class="flex items-center gap-4 font-black text-4xl tracking-tighter">
			Tasting history
		</h1>
	</div>
</div>

{@render children()}
