<script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/state";
	import * as Breadcrumb from "$lib/components/ui/breadcrumb";
	import { getTastingHistory, type TastingSession } from "$lib/db/localdb";
	import { KissatenAPI } from "$lib/api";
	import { slugifyCustomRoaster, getCustomRoasterName } from "$lib/utils/tasting_utils";

	let { children } = $props();

	let tastingHistory = $state<TastingSession[]>([]);
	let roastersByName = $state<Record<string, string>>({});

	const api = new KissatenAPI();

	onMount(async () => {
		try {
			const [history, response] = await Promise.all([
				getTastingHistory(),
				api.getRoasters(),
			]);
			tastingHistory = history;

			const roasters = response.data || [];
			const map: Record<string, string> = {};
			for (const r of roasters) {
				if (r.slug) map[r.slug] = r.name;
			}
			roastersByName = map;
		} catch (error) {
			console.error("Failed to load tasting history or roasters in breadcrumbs:", error);
		}
	});

	const prettySlug = (slug: string) =>
		slug
			.split(/[_-]+/)
			.map((w) => w.charAt(0).toUpperCase() + w.slice(1))
			.join(" ");

	const route = $derived.by(() => {
		const roasterSlug = page.params.roaster_slug as string | undefined;
		const beanSlug = page.params.bean_slug as string | undefined;
		const tastingId = page.params.tasting_id as string | undefined;

		const roasterName = roasterSlug
			? roasterSlug === "custom"
				? "Custom Beans"
				: roastersByName[roasterSlug] ||
					tastingHistory.find((t) => t.beanUrlPath?.startsWith(`/${roasterSlug}/`))
						?.roasterName ||
					prettySlug(roasterSlug)
			: undefined;

		const beanName =
			roasterSlug && beanSlug
				? tastingHistory.find(
						(t) => t.beanUrlPath === `/${roasterSlug}/${beanSlug}`,
				  )?.beanName ||
					(roasterSlug === "custom"
						? tastingHistory.find(
								(t) =>
									t.beanUrlPath?.startsWith("/custom/") &&
									slugifyCustomRoaster(getCustomRoasterName(t)) === beanSlug,
						  )?.roasterName || prettySlug(beanSlug)
						: prettySlug(beanSlug))
				: undefined;

		// When viewing a single custom bean's history, expose its roaster group
		// (a /custom/<roaster-slug> page) so the breadcrumbs can link to it.
		let customRoaster: { slug: string; name: string } | undefined;
		if (roasterSlug === "custom" && beanSlug) {
			const beanSession = tastingHistory.find(
				(t) => t.beanUrlPath === `/${roasterSlug}/${beanSlug}`,
			);
			if (beanSession) {
				const name = getCustomRoasterName(beanSession);
				const slug = slugifyCustomRoaster(name);
				if (slug) customRoaster = { slug, name: name || prettySlug(slug) };
			}
		}

		return { roasterSlug, beanSlug, tastingId, roasterName, beanName, customRoaster };
	});

	const title = $derived.by(() => {
		if (route.tastingId) return "";
		if (route.beanName) return route.beanName;
		if (route.roasterName) return route.roasterName;
		return "Tasting History";
	});

	const crumbs = $derived.by(() => {
		const list = [
			{ name: "Tasting", href: "/tasting" },
			{ name: "History", href: "/tasting/history" },
		];

		if (route.roasterSlug && route.roasterName) {
			list.push({
				name: route.roasterName,
				href: `/tasting/history/${route.roasterSlug}`,
			});
		}

		if (route.customRoaster) {
			list.push({
				name: route.customRoaster.name,
				href: `/tasting/history/custom/${route.customRoaster.slug}`,
			});
		}

		if (route.roasterSlug && route.beanSlug && route.beanName) {
			list.push({
				name: route.beanName,
				href: `/tasting/history/${route.roasterSlug}/${route.beanSlug}`,
			});
		}

		if (route.tastingId) {
			list.push({ name: "Session Detail", href: "" });
		}

		return list;
	});
</script>

<svelte:head>
	<meta name="robots" content="noindex,follow" />
	<link rel="canonical" href="https://kissaten.app/tasting/history" />
</svelte:head>

<div class="container mx-auto px-4 pt-8 max-w-4xl">
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

	{#if title}
		<div class="mb-8">
			<h1 class="font-black text-4xl tracking-tighter">{title}</h1>
		</div>
	{/if}

	{@render children()}
</div>
