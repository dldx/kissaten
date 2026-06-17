<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card/index.js";
	import * as Breadcrumb from "$lib/components/ui/breadcrumb";
	import * as Dialog from "$lib/components/ui/dialog";
	import CoffeeBeanImage from "$lib/components/CoffeeBeanImage.svelte";
	import BackButton from "$lib/components/BackButton.svelte";
	import {
		formatPrice,
		getFlavourCategoryColors,
		addUtmParams,
	} from "$lib/utils";
	import { api } from "$lib/api";
	import { db } from "$lib/db/localdb";
	import { dbUpdateTrigger } from "$lib/db/updates.svelte";
	import SaveBeanButton from "$lib/components/vault/SaveBeanButton.svelte";
	import BeanNotesEditor from "$lib/components/vault/BeanNotesEditor.svelte";
	import RecommendationTabs from "$lib/components/RecommendationTabs.svelte";
	import BeanTastingsCard from "$lib/components/tasting/BeanTastingsCard.svelte";
	import {
		Coffee,
		MapPin,
		Weight,
		Calendar,
		Grape,
		Mountain,
		User,
		ExternalLink,
		ArrowLeft,
		Star,
		Package,
		Globe,
		Combine,
		Flame,
		Droplets,
		Leaf,
		Ban,
		TreePine,
		Pencil,
		Shield,
		Sparkles,
	} from "lucide-svelte";
	import "iconify-icon";
	import DOMPurify from "dompurify";
	import { marked } from "marked";
	import { browser } from "$app/environment";
	import { page } from "$app/state";
	import { slide } from "svelte/transition";
	import { flip } from "svelte/animate";
	import { onMount, untrack } from "svelte";
	import { trackBeanView, getTastingsForBean, type TastingSession } from "$lib/db/localdb";
	import { userSettings } from "$lib/stores/userSettings.svelte";
	import { defaultSeo, toAbsoluteUrl, safeJsonLdStringify } from "$lib/seo";

	// Configure marked to treat single newlines as line breaks
	marked.setOptions({
		breaks: true,
	});
	const humanizeDuration = (timeInSecs: number) => {
		const days = Math.floor(timeInSecs / (1000 * 60 * 60 * 24));
		if (days > 0) return `${days} day${days > 1 ? "s" : ""}`;
		const hours = Math.floor(timeInSecs / (1000 * 60 * 60));
		if (hours > 0) return `${hours} hour${hours > 1 ? "s" : ""}`;
		const minutes = Math.floor(timeInSecs / (1000 * 60));
		if (minutes > 0) return `${minutes} minute${minutes > 1 ? "s" : ""}`;
		return "just now";
	};

	let { data } = $props();

	let bean = $state(data.bean);
	let recommendations = $state(data.recommendations || []);

	$effect(() => {
		if (data.bean) bean = data.bean;
		if (data.recommendations) recommendations = data.recommendations;
	});

	// Client-side hydration for custom beans
	onMount(async () => {
		if (!bean && data.isCustom && browser) {
			const { db } = await import("$lib/db/localdb");
			const { page } = await import("$app/stores");
			const params = untrack(() => {
				let p;
				page.subscribe((val) => (p = val.params))();
				return p;
			});

			const bean_name = params?.bean_name;
			if (!bean_name) return;

			const custom = await db.customBeans
				.where("syncId")
				.equals(bean_name)
				.first();

			if (custom) {
				bean = custom.beanData;
			}
		}
	});

	// Vault status and notes (local-first)
	let localSavedStatus = $state({
		saved: false,
		savedBeanId: null as string | null,
		notes: "",
		isLoading: true
	});

	$effect(() => {
		const url = bean?.bean_url_path;
		const _s = dbUpdateTrigger.savedBeans;
		const _c = dbUpdateTrigger.customBeans;
		
		async function updateStatus() {
			if (!url) return;

			// Check savedBeans locally
			const saved = await db.savedBeans
				.where('beanUrlPath')
				.equals(url)
				.filter(b => !b.deletedAt)
				.first();

			if (saved) {
				localSavedStatus = {
					saved: true,
					savedBeanId: saved.syncId,
					notes: saved.notes || "",
					isLoading: false
				};
				return;
			}
			
			// Check customBeans locally
			const custom = await db.customBeans
				.where('beanUrlPath')
				.equals(url)
				.filter(b => !b.deletedAt)
				.first();

			if (custom) {
				 localSavedStatus = {
					saved: true,
					savedBeanId: custom.syncId,
					notes: "",
					isLoading: false
				};
				return;
			}
			
			localSavedStatus = {
				saved: false,
				savedBeanId: null,
				notes: "",
				isLoading: false
			};
		}
		
		updateStatus();
	});

	let localNotes = $state<string | undefined>(undefined);
	let imageDialogOpen = $state(false);
	let dialogImageError = $state(false);
	let expandedNotes = $state<Record<string, boolean>>({});

	// Tasting history for this bean
	let beanTastings = $state<TastingSession[]>([]);

	$effect(() => {
		if (bean?.bean_url_path) {
			getTastingsForBean(bean.bean_url_path).then((tastings) => {
				beanTastings = tastings;
			});
		}
	});

	// Track bean view on mount
	onMount(() => {
		if (bean?.bean_url_path) {
			trackBeanView($state.snapshot(bean));
		}
	});

	// Sync local notes with the database status
	$effect(() => {
		if (bean && localSavedStatus.saved) {
			localNotes = localSavedStatus.notes;
		}
	});

	// Auto-expand recommendations if they share tasting notes with the current bean
	$effect(() => {
		if (bean?.bean_url_path) {
			expandedNotes = {}; // Reset on bean change
		}
	});

	$effect(() => {
		if (!bean || recommendations.length === 0) return;

		const currentNotes = (bean.tasting_notes ?? []).map((n: any) =>
			typeof n === "string" ? n : n.note,
		);

		untrack(() => {
			recommendations.forEach((rec: any) => {
				// Only auto-expand if we haven't touched this recBean yet
				if (expandedNotes[rec.bean_url_path] === undefined) {
					const hasHiddenCommonNote = (rec.tasting_notes ?? [])
						.slice(2)
						.some((note: string) => currentNotes.includes(note));
					if (hasHiddenCommonNote) {
						expandedNotes[rec.bean_url_path] = true;
					}
				}
			});
		});
	});

	// Helper computations for origins
	const originDisplay = $derived(
		bean ? api.getOriginDisplayString(bean) : "",
	);
	const processes = $derived(bean ? api.getBeanProcesses(bean) : []);
	const varieties = $derived(bean ? api.getVarieties(bean) : []);

	// Deduplicated lists for display
	const uniqueCountries = $derived.by(() => {
		if (!bean?.origins) return [];
		const countries = bean.origins
			.map((origin) => origin.country)
			.filter((country) => country != null);
		return [...new Set(countries)];
	});

	const uniqueProcesses = $derived([...new Set(processes)]);

	const uniqueVarieties = $derived([...new Set(varieties)]);

	const countryNameFromCode = $derived((code: string) => {
		if (!code) return "";
		if (code.length > 2) return code; // Already a full name or something else
		const options = page.data.originOptions || [];
		const country = options.find((o: any) => o.value === code.toUpperCase());
		return country ? country.text : code;
	});

	const isCustomBean = $derived(
		data.isCustom ||
			bean?.is_custom ||
			bean?.bean_url_path?.startsWith("/custom/"),
	);

	const displayImage = $derived(
		bean ? (bean as any).image_data || bean.image_url : null,
	);

	// Helper to get country display info
	const getCountryDisplayInfo = (countryCode: string) => {
		if (!bean?.origins) return { code: countryCode, fullName: countryCode };
		const origin = bean.origins.find((o) => o.country === countryCode);
		return {
			code: countryCode,
			fullName: origin?.country_full_name || countryCode,
		};
	};

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return "N/A";
		return new Date(dateStr).toLocaleDateString("en-US", {
			year: "numeric",
			month: "long",
			day: "numeric",
		});
	}
</script>

<svelte:head>
	<title>{bean?.name ? `${bean.name} by ${bean.roaster}` : "Coffee Bean"} | Kissaten</title>
	<meta
		name="description"
		content={bean?.description ||
			`${bean?.name || "Coffee"} coffee bean from ${bean?.roaster || ""}. Origin: ${originDisplay}.`}
	/>
	<link
		rel="canonical"
		href={bean?.bean_url_path
			? toAbsoluteUrl(bean.bean_url_path)
			: toAbsoluteUrl(page.url.pathname)}
	/>
	<meta property="og:type" content="product" />
	{#if bean}
		{@const ogImage = toAbsoluteUrl(
			`/og/bean/${page.params.roaster_name}/${page.params.bean_name}`
		)}
		<meta property="og:image" content={ogImage} />
		<meta property="og:image:width" content="1200" />
		<meta property="og:image:height" content="630" />
		<meta property="og:image:alt" content={`${bean.name} by ${bean.roaster}`} />
		<meta name="twitter:image" content={ogImage} />
		<meta name="twitter:image:alt" content={`${bean.name} by ${bean.roaster}`} />
		<meta property="product:price:amount" content={bean.price?.toString() ?? ''} />
		<meta property="product:price:currency" content={bean.currency || 'USD'} />
		{@html `<script type="application/ld+json">${safeJsonLdStringify({
			'@context': 'https://schema.org',
			'@type': 'Product',
			name: bean.name,
			brand: bean.roaster ? { '@type': 'Brand', name: bean.roaster } : undefined,
			description: bean.description || `${bean.name} coffee from ${bean.roaster}`,
			image: ogImage,
			offers: bean.price
				? {
						'@type': 'Offer',
						price: bean.price,
						priceCurrency: bean.currency || 'USD',
						availability: bean.in_stock
							? 'https://schema.org/InStock'
							: 'https://schema.org/OutOfStock',
						url: bean.url || undefined,
					}
				: undefined,
		})}</script>`}
	{/if}
</svelte:head>

{#if !bean}
	<div class="mx-auto px-4 py-8 container">
		<div class="flex justify-center items-center min-h-[400px]">
			<div class="text-center">
				<p class="text-muted-foreground">Loading coffee bean...</p>
			</div>
		</div>
	</div>
{:else}
	<div class="mx-auto px-4 py-8 container">
		<!-- Breadcrumb Navigation -->
		<Breadcrumb.Root class="mb-6">
			<Breadcrumb.List>
				<Breadcrumb.Item>
					<Breadcrumb.Link href="/">Home</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator />
				<Breadcrumb.Item>
					<Breadcrumb.Link href="/search">Search</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator />
				<Breadcrumb.Item>
					<Breadcrumb.Link href="/roasters">Roasters</Breadcrumb.Link>
				</Breadcrumb.Item>
				<Breadcrumb.Separator />
				<Breadcrumb.Item>
					<Breadcrumb.Link
						href={isCustomBean ? "/vault/collection" : `/search?roaster=${encodeURIComponent(bean.roaster)}`}
						>{isCustomBean ? "Private Collection" : bean.roaster}</Breadcrumb.Link
					>
				</Breadcrumb.Item>
				<Breadcrumb.Separator />
				<Breadcrumb.Item>
					<Breadcrumb.Page>{bean.name}</Breadcrumb.Page>
				</Breadcrumb.Item>
			</Breadcrumb.List>
		</Breadcrumb.Root>

		<!-- Back Button -->
		<BackButton />

		<div class="gap-8 grid grid-cols-1 lg:grid-cols-4">
			<!-- Image Section -->
			<div class="lg:col-span-1">
				<div class="top-8 sticky flex justify-center items-center">
					<CoffeeBeanImage
						{bean}
						size="xl"
						class="mx-auto w-full max-w-md h-full"
						clickable={true}
						onclick={() => {
							imageDialogOpen = true;
							dialogImageError = false;
						}}
					/>
				</div>
			</div>

			<!-- Image Expansion Dialog -->
			<Dialog.Root bind:open={imageDialogOpen}>
				<Dialog.Content class="w-[95vw] max-w-7xl">
					<Dialog.Header>
						<Dialog.Title>{bean.name}</Dialog.Title>
						<Dialog.Description>
							{bean.roaster} - {originDisplay}
						</Dialog.Description>
					</Dialog.Header>
					<div class="flex justify-center items-center w-full">
						{#if displayImage && !dialogImageError}
							<img
								src={displayImage}
								alt="{bean.name} from {bean.roaster}"
								class="rounded-lg w-auto max-h-[80vh] object-cover"
								onerror={() => (dialogImageError = true)}
							/>
						{/if}

						{#if !displayImage || dialogImageError}
							<div
								class="flex justify-center items-center bg-gray-100 dark:bg-slate-800 rounded-lg w-full h-96 placeholder-bg"
							>
								{#if isCustomBean}
									<div
										class="flex flex-col justify-center items-center text-muted-foreground/40"
									>
										<Coffee class="mb-4 w-24 h-24" />
										<span
											class="font-medium text-sm uppercase tracking-widest"
											>Custom Bean</span
										>
									</div>
								{:else}
									<img
										src={bean
											? "/static/data/roasters/" +
												bean.bean_url_path?.split(
													"/",
												)[1] +
												"/logo_sticker.png"
											: ""}
										alt="{bean?.roaster} logo"
										class="drop-shadow-md max-w-[50%] max-h-[50%] object-contain"
									/>
								{/if}
							</div>
						{/if}
					</div>

				</Dialog.Content>
			</Dialog.Root>

			<!-- Main Content -->
			<div class="space-y-6 lg:col-span-2">
				<!-- Header -->
				<div class="space-y-4">
					<div class="flex justify-between items-start">
						<div class="flex-1 space-y-2">
							<div class="flex justify-center lg:justify-start items-center gap-2">
								<h1
									class="dark:drop-shadow-[0_0_12px_rgba(34,211,238,0.8)] font-bold dark:text-cyan-100 text-4xl lg:text-left text-center"
									style="view-transition-name: bean-title;"
								>
									{bean.name}
								</h1>
								{#if isCustomBean}
									<div
										class="flex items-center bg-blue-500/10 px-2 py-1 rounded-full text-blue-500 text-xs transition-all animate-in fade-in zoom-in duration-300"
									>
										<Shield class="mr-1 w-3 h-3" />
										<span>Private</span>
									</div>
								{/if}
								<SaveBeanButton {bean} notes={localNotes} />
							</div>
							<div
								class="flex justify-center lg:justify-start items-center dark:drop-shadow-[0_0_6px_rgba(34,211,238,0.4)] text-muted-foreground dark:text-cyan-300/80 text-xl"
							>
								<Coffee class="mr-2 w-5 h-5" />
								<span
									>Roasted by <a
										href={`/search?roaster=${encodeURIComponent(bean.roaster)}`}
										class="dark:hover:text-cyan-100 dark:text-cyan-200"
										>{bean.roaster}, {countryNameFromCode(
											bean.roaster_location,
										)}</a
									></span
								>
							</div>
						</div>
					</div>

					<!-- Main Attributes -->
					<div class="flex flex-wrap justify-center lg:justify-start gap-2">
						{#if uniqueCountries.length > 0}
							{#each uniqueCountries as country (country)}
								{@const countryInfo =
									getCountryDisplayInfo(country)}
								<div
									animate:flip={{ duration: 400 }}
									style="display: contents;"
								>
									<a
										class="inline-flex items-center bg-red-100 hover:bg-red-200 dark:bg-red-900/40 dark:hover:bg-red-900/60 dark:hover:shadow-[0_0_15px_rgba(239,68,68,0.4)] dark:shadow-[0_0_10px_rgba(239,68,68,0.3)] dark:drop-shadow-[0_0_4px_rgba(239,68,68,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(239,68,68,1)] px-3 py-1 dark:border dark:border-red-400/50 dark:hover:border-red-300 rounded-full font-medium text-sm transition-all duration-200"
										href={`/origins/${country}`}
										transition:slide={{ duration: 400 }}
									>
										<iconify-icon
											icon="circle-flags:{country?.toLowerCase()}"
											class="mr-2 w-3 h-3"
										></iconify-icon>
										{countryNameFromCode(country)}
									</a>
								</div>
							{/each}
						{/if}
						{#if uniqueVarieties.length > 0}
							<div
								class="group inline-flex items-center bg-accent hover:bg-accent/80 dark:bg-emerald-900/40 dark:hover:bg-emerald-900/60 dark:hover:shadow-[0_0_15px_rgba(16,185,129,0.4)] dark:shadow-[0_0_10px_rgba(16,185,129,0.3)] dark:drop-shadow-[0_0_4px_rgba(16,185,129,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(16,185,129,1)] px-1.5 py-1 dark:border dark:border-emerald-400/50 dark:hover:border-emerald-300 rounded-full font-medium text-sm transition-all duration-200"
								transition:slide={{ duration: 400 }}
							>
								<Leaf class="mx-1.5 w-3 h-3" />
								{#each uniqueVarieties as variety, index (variety)}
									<div
										animate:flip={{ duration: 400 }}
										style="display: contents;"
									>
										{#if index > 0}<span class="mx-0.5"
												>/&#8203;</span
											>{/if}
										<a
											href={`/varietals/${api.normalizeVarietalName(variety)}`}
											class="px-0.5 hover:underline"
										>
											{variety}
										</a>
									</div>
								{/each}
								<span class="mr-1"></span>
							</div>
						{/if}
						{#if uniqueProcesses.length > 0}
							<div
								class="group inline-flex items-center bg-secondary hover:bg-secondary/80 dark:bg-cyan-900/40 dark:hover:bg-cyan-900/60 dark:hover:shadow-[0_0_15px_rgba(34,211,238,0.4)] dark:shadow-[0_0_10px_rgba(34,211,238,0.3)] dark:drop-shadow-[0_0_4px_rgba(34,211,238,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(34,211,238,1)] px-1.5 py-1 dark:border dark:border-cyan-400/50 dark:hover:border-cyan-300 rounded-full font-medium text-sm transition-all duration-200"
								transition:slide={{ duration: 400 }}
							>
								<Droplets class="mx-1.5 w-3 h-3" />
								{#each uniqueProcesses as process, index (process)}
									<div
										animate:flip={{ duration: 400 }}
										style="display: contents;"
									>
										{#if index > 0}<span class="mx-0.5"
												>/</span
											>{/if}
										<a
											href={`/processes/${api.normalizeProcessName(process)}`}
											class="px-0.5 hover:underline"
										>
											{process}
										</a>
									</div>
								{/each}
								<span class="mr-1"></span>
							</div>
						{/if}
						{#if bean.roast_level}
							<span
								class="inline-flex items-center bg-primary hover:bg-primary/90 dark:bg-orange-900/40 dark:hover:bg-orange-900/60 dark:hover:shadow-[0_0_15px_rgba(251,146,60,0.4)] dark:shadow-[0_0_10px_rgba(251,146,60,0.3)] dark:drop-shadow-[0_0_4px_rgba(251,146,60,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(251,146,60,1)] px-3 py-1 dark:border dark:border-orange-400/50 dark:hover:border-orange-300 rounded-full font-medium text-sm transition-all duration-200"
								transition:slide={{ duration: 400 }}
							>
								<a
									href={`/search?roast_level=${bean.roast_level}`}
									class="inline-flex items-center"
								>
									<Flame class="mr-1 w-3 h-3" />
									{bean.roast_level} roast
								</a>
							</span>
						{/if}
						{#if bean?.roast_profile}
							<span
								class="inline-flex items-center bg-blue-100 hover:bg-blue-200 dark:bg-purple-900/40 dark:hover:bg-purple-900/60 dark:hover:shadow-[0_0_15px_rgba(168,85,247,0.4)] dark:shadow-[0_0_10px_rgba(168,85,247,0.3)] dark:drop-shadow-[0_0_4px_rgba(168,85,247,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(168,85,247,1)] px-3 py-1 dark:border dark:border-purple-400/50 dark:hover:border-purple-300 rounded-full font-medium text-sm transition-all duration-200"
								transition:slide={{ duration: 400 }}
							>
								<a
									href={`/search?roast_profile=${bean.roast_profile}`}
									class="inline-flex items-center"
								>
									<Coffee class="mr-1 w-3 h-3" />
									{bean.roast_profile == "Both" ? "Filter & Espresso" : bean.roast_profile} profile
								</a>
							</span>
						{/if}
						{#if bean?.is_decaf}
							<a
								class="inline-flex items-center bg-orange-100 hover:bg-orange-200 dark:bg-red-900/40 dark:hover:bg-red-900/60 dark:hover:shadow-[0_0_15px_rgba(239,68,68,0.4)] dark:shadow-[0_0_10px_rgba(239,68,68,0.3)] dark:drop-shadow-[0_0_4px_rgba(239,68,68,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(239,68,68,1)] px-3 py-1 dark:border dark:border-red-400/50 dark:hover:border-red-300 rounded-full font-medium text-sm transition-all duration-200"
								href={`/search?is_decaf=true`}
								transition:slide={{ duration: 400 }}
							>
								<Ban class="mr-1 w-3 h-3" />
								Decaf
							</a>
						{/if}
						{#if !bean?.is_single_origin}
							<a
								class="inline-flex items-center bg-indigo-100 hover:bg-indigo-200 dark:bg-pink-900/40 dark:hover:bg-pink-900/60 dark:hover:shadow-[0_0_15px_rgba(236,72,153,0.4)] dark:shadow-[0_0_10px_rgba(236,72,153,0.3)] dark:drop-shadow-[0_0_4px_rgba(236,72,153,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(236,72,153,1)] px-3 py-1 dark:border dark:border-pink-400/50 dark:hover:border-pink-300 rounded-full font-medium text-sm transition-all duration-200"
								href={`/search?is_single_origin=false`}
								transition:slide={{ duration: 400 }}
							>
								<Combine class="mr-1 w-3 h-3" />
								Blend
							</a>
						{/if}
						{#if bean?.cupping_score && bean?.cupping_score > 0}
							<span
								class="inline-flex items-center bg-yellow-100 hover:bg-yellow-200 dark:bg-yellow-900/40 dark:hover:bg-yellow-900/60 dark:hover:shadow-[0_0_15px_rgba(234,179,8,0.4)] dark:shadow-[0_0_10px_rgba(234,179,8,0.3)] dark:drop-shadow-[0_0_4px_rgba(234,179,8,0.8)] dark:hover:drop-shadow-[0_0_6px_rgba(234,179,8,1)] px-3 py-1 dark:border dark:border-yellow-400/50 dark:hover:border-yellow-300 rounded-full font-medium text-sm transition-all duration-200"
								transition:slide={{ duration: 400 }}
							>
								<Star class="mr-1 w-3 h-3" />
								{bean?.cupping_score}/100
							</span>
						{/if}
					</div>
				</div>
				<!-- User Notes -->
				{#if localSavedStatus.saved}
						<div transition:slide|global>
							<Card
								class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] border-primary/20 dark:border-cyan-500/30"
							>
								<CardHeader>
									<div
										class="flex justify-between items-center"
									>
										<CardTitle
											class="flex items-center dark:drop-shadow-[0_0_8px_rgba(34,211,238,0.6)] dark:text-cyan-300"
										>
											<Pencil class="mr-2 w-5 h-5" />
											My Notes
										</CardTitle>
									</div>
									<CardDescription
										>Personal notes about this coffee. Only
										visible to you.</CardDescription
									>
								</CardHeader>
								<CardContent>
									<BeanNotesEditor
										savedBeanId={localSavedStatus.savedBeanId!}
										initialNotes={localSavedStatus.notes}
										textareaClass="min-h-[140px]"
										placeholder="What did you think of this coffee? (flavour, brewing notes, etc...)"
										onNoteChange={(n) => (localNotes = n)}
									/>
								</CardContent>
							</Card>
						</div>
				{/if}

				<!-- Tasting History & Roaster Notes -->
				{#if localSavedStatus.saved || (bean.tasting_notes && bean.tasting_notes.length > 0) || beanTastings.length > 0}
						<BeanTastingsCard
							beanUrlPath={bean.bean_url_path}
							tastings={beanTastings}
							roasterNotes={bean.tasting_notes}
							isSaved={localSavedStatus.saved || false}
						/>
				{/if}
				<!-- Description -->
				{#if bean?.description && bean?.description.trim()}
					<Card
						class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
						style="view-transition-name: bean-description;"
					>
						<CardHeader>
							<CardTitle
								class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300"
							>
								<Coffee class="mr-2 w-5 h-5" />
								Description
							</CardTitle>
						</CardHeader>
						<CardContent>
							<p class="text-muted-foreground leading-relaxed">
								{#if browser}
									{@html DOMPurify.sanitize(
										marked.parse(
											bean.description,
										) as string,
									)}
								{:else}
									{bean.description.replace(
										/  +\n/g,
										"<br />",
									)}
								{/if}
							</p>
						</CardContent>
					</Card>
				{/if}

				<!-- Origin Details -->
				<Card
					class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
					style="view-transition-name: bean-origin;"
				>
					<CardHeader>
						<CardTitle
							class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300"
						>
							<MapPin class="mr-2 w-5 h-5" />
							{bean.is_single_origin ? "Origin" : "Origins"}
						</CardTitle>
						{#if !bean.is_single_origin}
							<CardDescription
								>This coffee is a blend of multiple origins</CardDescription
							>
						{/if}
					</CardHeader>
					<CardContent>
						<!-- Multiple Origins Display (Blend) -->
						<div class={bean.origins.length > 1 ? "space-y-4" : ""}>
							{#each bean.origins as origin, index}
								<div
									class={bean.origins.length > 1
										? "pl-4 border-primary border-l-4"
										: ""}
								>
									{#if bean.origins.length > 1}
										<h4 class="mb-2 font-semibold text-sm">
											Origin {index + 1}
										</h4>
									{/if}
									<div
										class="gap-4 grid grid-cols-1 md:grid-cols-2"
									>
										{#if origin.country}
											<div
												class="flex items-center space-x-2"
											>
												<Globe
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Country:</span
												>
												<span class="font-medium">
													<a
														href={`/origins/${origin.country.toLowerCase()}`}
														class="hover:underline"
													>
														{origin.country_full_name ||
															countryNameFromCode(
																origin.country,
															)}
													</a>
												</span>
											</div>
										{/if}
										{#if origin.region}
											<div
												class="flex items-center space-x-2"
											>
												<MapPin
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Region:</span
												>
												<span>
													{#if origin.region_canonical && origin.country}
														<a
															href={`/origins/${origin.country.toLowerCase()}/${api.normalizeRegionName(origin.region_canonical)}`}
															class="hover:underline"
														>
															{origin.region}
														</a>
													{:else}
														{origin.region}
													{/if}
												</span>
											</div>
										{/if}
										{#if origin.producer}
											<div
												class="flex items-center space-x-2"
											>
												<User
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Producer:</span
												>
												<span>{origin.producer}</span>
											</div>
										{/if}
										{#if origin.farm}
											<div
												class="flex items-center space-x-2"
											>
												<TreePine
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Farm:</span
												>
												<span>
													{#if origin.farm_canonical && origin.country && origin.region_canonical}
														<a
															href={`/origins/${origin.country.toLowerCase()}/${api.normalizeRegionName(origin.region_canonical)}/${api.normalizeFarmName(origin.farm_canonical)}`}
															class="hover:underline"
														>
															{origin.farm}
														</a>
													{:else}
														{origin.farm}
													{/if}
												</span>
											</div>
										{/if}
										{#if origin.elevation_min && origin.elevation_min > 0}
											<div
												class="flex items-center space-x-2"
											>
												<Mountain
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Elevation:</span
												>
												<span>
													{#if origin.elevation_max && origin.elevation_max > origin.elevation_min}
														{origin.elevation_min}-{origin.elevation_max}m
													{:else}
														{origin.elevation_min}m
													{/if}
												</span>
											</div>
										{/if}
										{#if origin.latitude && origin.longitude}
											<div
												class="flex items-center space-x-2"
											>
												<MapPin
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Coordinates:</span
												>
												<span
													>{origin.latitude.toFixed(
														4,
													)}, {origin.longitude.toFixed(
														4,
													)}</span
												>
											</div>
										{/if}
										{#if origin.process}
											<div
												class="flex items-center space-x-2"
											>
												<Droplets
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Process:</span
												>
												<span
													><a
														href={`/processes/${api.normalizeProcessName(origin.process)}`}
														class="hover:underline"
														>{origin.process}</a
													></span
												>
											</div>
										{/if}
										{#if origin.variety}
											<div
												class="flex items-center space-x-2"
											>
												<Leaf
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Variety:</span
												>
												<span
													>{#each origin.variety_canonical ?? [] as variety, i}
														{#if i > 0},&nbsp;{/if}<a
															href={`/varietals/${api.normalizeVarietalName(variety)}`}
															class="hover:underline"
															>{variety}</a
														>
													{/each}</span
												>
											</div>
										{/if}
										{#if origin.harvest_date}
											<div
												class="flex items-center space-x-2"
											>
												<Calendar
													class="mr-1 w-4 h-4 text-muted-foreground"
												/>
												<span
													class="font-medium text-muted-foreground"
													>Harvest Date:</span
												>
												<span
													>{new Date(
														origin.harvest_date,
													).toLocaleDateString(
														"en-GB",
														{
															year: "numeric",
															month: "long",
														},
													)}</span
												>
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>

						<!-- Single Origin Status -->
						<div
							class="flex items-center space-x-2 mt-4 pt-4 border-t"
						>
							<Package
								class="mr-1 w-4 h-4 text-muted-foreground"
							/>
							<span class="font-medium text-muted-foreground"
								>Type:</span
							>
							<span
								>{bean.is_single_origin
									? "Single Origin"
									: "Blend"}</span
							>
						</div>
					</CardContent>
				</Card>
			</div>

			<!-- Sidebar -->
			<div class="space-y-6">
				<!-- Coffee Information -->
				<Card
					class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
				>
					<CardHeader>
						<CardTitle
							class="dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300"
							>{isCustomBean ? "Coffee Info" : "Purchase"}</CardTitle
						>
					</CardHeader>
					<CardContent class="space-y-4">
						<!-- Price and Weight -->
						{#if (bean.price && !isCustomBean) || bean.weight}
							<div
								class="flex flex-wrap justify-between gap-4 text-2xl"
							>
								{#if bean.price && !isCustomBean}
									<div
										class="flex items-center dark:drop-shadow-[0_0_10px_rgba(16,185,129,0.8)] font-semibold text-muted-foreground dark:text-emerald-300"
									>
										<span
											>{formatPrice(
												bean.price,
												bean.currency,
											)}</span
										>
									</div>
								{/if}
								{#if bean.weight}
									<div
										class="flex items-center dark:drop-shadow-[0_0_4px_rgba(34,211,238,0.4)] text-muted-foreground dark:text-cyan-400/80"
									>
										<Weight class="mr-2 w-6 h-6" />
										<span>{bean.weight}g</span>
									</div>
								{/if}
							</div>
						{/if}

						{#if isCustomBean}
							<Button
								class="py-2 w-full h-auto text-center leading-tight whitespace-normal"
								href={`/tasting?bean=${encodeURIComponent(bean.bean_url_path || "")}`}
							>
								<Sparkles class="mr-2 w-4 h-4 shrink-0" />
								Start Tasting Session
							</Button>
						{/if}

						{#if bean.in_stock !== null && !isCustomBean}
							<div
								class="flex justify-between items-center space-x-2"
							>
								<span
									class="text-sm {bean.in_stock
										? 'text-green-600 dark:text-emerald-300 dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]'
										: 'text-red-600 dark:text-red-300 dark:drop-shadow-[0_0_8px_rgba(239,68,68,0.8)]'}"
								>
									{bean.in_stock
										? "✅ In stock"
										: "❌ Out of stock"}
								</span><span
									class="text-muted-foreground text-sm"
									title={new Date(
										bean.scraped_at,
									).toLocaleString("en-GB")}
									>(checked {humanizeDuration(
										new Date().getTime() -
											new Date(bean.scraped_at).getTime(),
									)} ago)
								</span>
							</div>
						{/if}
						{#if bean.url && !isCustomBean}
							<Button
								class="py-2 w-full h-auto text-center leading-tight whitespace-normal"
								href={addUtmParams(bean.url, {
									source: "kissaten.app",
									medium: "referral",
									campaign: "bean_profile",
								})}
								target="_blank"
							>
								<ExternalLink class="mr-2 w-4 h-4 shrink-0" />
								View on {bean.roaster}
							</Button>
						{/if}

						{#if userSettings.betaEnabled}
							<Button
								variant="outline"
								class="dark:hover:bg-cyan-500/10 dark:hover:text-white dark:text-white mt-1 py-2 border-primary/20 dark:border-cyan-500/20 w-full h-auto text-center leading-tight whitespace-normal transition-colors"
								href={`/brew-assistant?bean_url_path=${encodeURIComponent(bean.bean_url_path || "")}`}
							>
								<Coffee class="mr-2 w-4 h-4 text-amber-500 shrink-0" />
								Brew with Assistant (Beta)
							</Button>
						{/if}

						<!-- Additional Details -->
						<div class="space-y-2 text-sm">
							{#if bean.cupping_score && bean.cupping_score > 0}
								<div class="flex justify-between">
									<span class="text-muted-foreground"
										>Cupping Score:</span
									>
									<span class="font-medium"
										>{bean.cupping_score}/100</span
									>
								</div>
							{/if}
							{#if bean.price_paid_for_green_coffee}
								<div class="flex justify-between">
									<span class="text-muted-foreground"
										>Green Price:</span
									>
									<span
										>{formatPrice(
											bean.price_paid_for_green_coffee,
											bean.currency_of_price_paid_for_green_coffee ||
												"USD",
										)}/kg</span
									>
								</div>
							{/if}
							<div class="flex justify-between">
								<span class="text-muted-foreground"
									>{isCustomBean ? "Added:" : "First spotted:"}</span
								>
								<span
									title={new Date(
										bean.date_added,
									).toLocaleString("en-GB")}
									>{humanizeDuration(
										new Date().getTime() -
											new Date(bean.date_added).getTime(),
									)} ago</span
								>
							</div>
							{#if !isCustomBean}
								<hr />
								<div
									class="w-full text-muted-foreground text-justify"
								>
									Prices and stock status may not always be
									accurate. If you spot an error, please <a
										target="_blank"
										class="underline"
										href="https://github.com/dldx/kissaten/issues"
										>file an issue</a
									>.
								</div>
							{/if}
						</div>
					</CardContent>
				</Card>

				<!-- Recommendations -->
				{#if recommendations && recommendations.length > 0}
					<RecommendationTabs {bean} initialRecommendations={recommendations} />
				{/if}
			</div>
		</div>
	</div>
{/if}
