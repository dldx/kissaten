<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card/index.js";
	import CoffeeBeanImage from "$lib/components/CoffeeBeanImage.svelte";
	import { formatPrice, getFlavourCategoryColors } from "$lib/utils";
	import { api } from "$lib/api";
	import { checkBeanSaved } from "$lib/api/vault.remote";
	import SaveBeanButton from "$lib/components/vault/SaveBeanButton.svelte";
	import BeanNotesEditor from "$lib/components/vault/BeanNotesEditor.svelte";
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
	} from "lucide-svelte";
	import "iconify-icon";
	import DOMPurify from "dompurify";
	import { marked } from "marked";
	import { browser } from "$app/environment";
	import { fade, slide } from "svelte/transition";
	import { flip } from "svelte/animate";

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

	let { bean, recommendations } = $derived({
		bean: data.bean,
		recommendations: data.recommendations || [],
	});

	// Vault status and notes
	const beanUrlPath = $derived(
		bean.bean_url_path || api.getBeanUrlPath(bean),
	);
	const savedStatus = $derived(checkBeanSaved(beanUrlPath));
	let localNotes = $state<string | undefined>(undefined);

	// Sync local notes with the database status
	$effect(() => {
		savedStatus.then((status) => {
			if (status.saved) {
				localNotes = status.notes;
			}
		});
	});

	// Helper computations for origins
	const originDisplay = $derived(api.getOriginDisplayString(bean));
	const processes = $derived(api.getBeanProcesses(bean));
	const varieties = $derived(api.getVarieties(bean));

	// Deduplicated lists for display
	const uniqueCountries = $derived.by(() => {
		const countries = bean.origins
			.map((origin) => origin.country)
			.filter((country) => country != null);
		return [...new Set(countries)];
	});

	const uniqueProcesses = $derived([...new Set(processes)]);

	const uniqueVarieties = $derived([...new Set(varieties)]);

	// Helper to get country display info
	const getCountryDisplayInfo = (countryCode: string) => {
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
	<title>{bean.name} by {bean.roaster} - Kissaten</title>
	<meta
		name="description"
		content={bean.description ||
			`${bean.name} coffee bean from ${bean.roaster}. Origin: ${originDisplay}.`}
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Breadcrumb Navigation -->
	<nav class="mb-6 text-sm">
		<ol class="flex items-center space-x-2">
			<li>
				<a href="/" class="text-muted-foreground hover:text-foreground"
					>Home</a
				>
			</li>
			<li class="text-muted-foreground">•</li>
			<li>
				<a
					href="/search"
					class="text-muted-foreground hover:text-foreground"
					>Search</a
				>
			</li>
			<li class="text-muted-foreground">•</li>
			<li>
				<a
					href="/roasters"
					class="text-muted-foreground hover:text-foreground"
					>Roasters</a
				>
			</li>
			<li class="text-muted-foreground">•</li>
			<li class="font-medium text-foreground">{bean.name}</li>
		</ol>
	</nav>

	<!-- Back Button -->
	<div class="mb-6">
		<Button variant="ghost" onclick={() => history.back()} class="pl-2">
			<ArrowLeft class="mr-2 w-4 h-4" />
			Back
		</Button>
	</div>

	<div class="gap-8 grid grid-cols-1 lg:grid-cols-4">
		<!-- Image Section -->
		<div class="lg:col-span-1">
			<div class="top-8 sticky">
				<CoffeeBeanImage
					{bean}
					size="xl"
					class="mx-auto w-full max-w-md h-full"
				/>
			</div>
		</div>

		<!-- Main Content -->
		<div class="space-y-6 lg:col-span-2">
			<!-- Header -->
			<div class="space-y-4">
				<div class="flex justify-between items-start">
					<div class="flex-1 space-y-2">
						<div class="flex items-center gap-3">
							<h1
								class="dark:drop-shadow-[0_0_12px_rgba(34,211,238,0.8)] font-bold dark:text-cyan-100 text-4xl"
								style="view-transition-name: bean-title;"
							>
								{bean.name}
							</h1>
							<SaveBeanButton {bean} notes={localNotes} />
						</div>
						<div
							class="flex items-center dark:drop-shadow-[0_0_6px_rgba(34,211,238,0.4)] text-muted-foreground dark:text-cyan-300/80 text-xl"
						>
							<Coffee class="mr-2 w-5 h-5" />
							<span
								>Roasted by <a
									href={`/search?roaster=${encodeURIComponent(bean.roaster)}`}
									class="dark:hover:text-cyan-100 dark:text-cyan-200"
									>{bean.roaster}, {bean.roaster_country_code}</a
								></span
							>
						</div>
					</div>
				</div>

				<!-- Main Attributes -->
				<div class="flex flex-wrap gap-2">
					{#if uniqueCountries.length > 0}
						{#each uniqueCountries as country (country)}
							{@const countryInfo =
								getCountryDisplayInfo(country)}
							<div
								animate:flip={{ duration: 400 }}
								style="display: contents;"
							>
								<a
									class="inline-flex items-center bg-red-100 hover:bg-red-200 dark:bg-red-900/40 dark:shadow-[0_0_10px_rgba(239,68,68,0.3)] dark:drop-shadow-[0_0_4px_rgba(239,68,68,0.8)] px-3 py-1 dark:border dark:border-red-400/50 dark:hover:border-red-300 rounded-full font-medium text-red-800 dark:text-red-200 text-sm"
									href={`/search?origin=${country}`}
									transition:slide={{ duration: 400 }}
								>
									<iconify-icon
										icon="circle-flags:{country?.toLowerCase()}"
										class="mr-2 w-3 h-3"
									></iconify-icon>
									{countryInfo.fullName}
								</a>
							</div>
						{/each}
					{/if}
					{#if uniqueProcesses.length > 0}
						<div
							class="inline-flex items-center bg-secondary dark:bg-cyan-900/40 dark:shadow-[0_0_10px_rgba(34,211,238,0.3)] dark:drop-shadow-[0_0_4px_rgba(34,211,238,0.8)] px-1.5 py-1 dark:border dark:border-cyan-400/50 rounded-full font-medium dark:text-cyan-200 text-sm"
							transition:slide={{ duration: 400 }}
						>
							<Droplets class="mx-1.5 w-3 h-3" />
							{#each uniqueProcesses as process, index (process)}
								<div
									animate:flip={{ duration: 400 }}
									style="display: contents;"
								>
									{#if index > 0}<span class="mx-0.5">/</span
										>{/if}
									<a
										href={`/process/${api.normalizeProcessName(process)}`}
										class="hover:underline px-0.5"
									>
										{process}
									</a>
								</div>
							{/each}
							<span class="mr-1"></span>
						</div>
					{/if}
					{#if uniqueVarieties.length > 0}
						<div
							class="inline-flex items-center bg-accent dark:bg-emerald-900/40 dark:shadow-[0_0_10px_rgba(16,185,129,0.3)] dark:drop-shadow-[0_0_4px_rgba(16,185,129,0.8)] px-1.5 py-1 dark:border dark:border-emerald-400/50 rounded-full font-medium dark:text-emerald-200 text-sm text-accent-foreground"
							transition:slide={{ duration: 400 }}
						>
							<Leaf class="mx-1.5 w-3 h-3" />
							{#each uniqueVarieties as variety, index (variety)}
								<div
									animate:flip={{ duration: 400 }}
									style="display: contents;"
								>
									{#if index > 0}<span class="mx-0.5">/</span
										>{/if}
									<a
										href={`/varietals/${api.normalizeVarietalName(variety)}`}
										class="hover:underline px-0.5"
									>
										{variety}
									</a>
								</div>
							{/each}
							<span class="mr-1"></span>
						</div>
					{/if}
					{#if bean.roast_level}
						<span
							class="inline-flex items-center bg-primary dark:bg-orange-900/40 dark:shadow-[0_0_10px_rgba(251,146,60,0.3)] dark:drop-shadow-[0_0_4px_rgba(251,146,60,0.8)] px-3 py-1 dark:border dark:border-orange-400/50 rounded-full font-medium text-primary-foreground dark:text-orange-200 text-sm"
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
					{#if bean.roast_profile}
						<span
							class="inline-flex items-center bg-blue-100 dark:bg-purple-900/40 dark:shadow-[0_0_10px_rgba(168,85,247,0.3)] dark:drop-shadow-[0_0_4px_rgba(168,85,247,0.8)] px-3 py-1 dark:border dark:border-purple-400/50 rounded-full font-medium text-blue-800 dark:text-purple-200 text-sm"
							transition:slide={{ duration: 400 }}
						>
							<a
								href={`/search?roast_profile=${bean.roast_profile}`}
								class="inline-flex items-center"
							>
								<Coffee class="mr-1 w-3 h-3" />
								{bean.roast_profile} profile
							</a>
						</span>
					{/if}
					{#if bean.is_decaf}
						<a
							class="inline-flex items-center bg-orange-100 dark:bg-red-900/40 dark:shadow-[0_0_10px_rgba(239,68,68,0.3)] dark:drop-shadow-[0_0_4px_rgba(239,68,68,0.8)] px-3 py-1 dark:border dark:border-red-400/50 rounded-full font-medium text-orange-800 dark:text-red-200 text-sm"
							href={`/search?is_decaf=true`}
							transition:slide={{ duration: 400 }}
						>
							<Ban class="mr-1 w-3 h-3" />
							Decaf
						</a>
					{/if}
					{#if !bean.is_single_origin}
						<a
							class="inline-flex items-center bg-indigo-100 dark:bg-pink-900/40 dark:shadow-[0_0_10px_rgba(236,72,153,0.3)] dark:drop-shadow-[0_0_4px_rgba(236,72,153,0.8)] px-3 py-1 dark:border dark:border-pink-400/50 rounded-full font-medium text-indigo-800 dark:text-pink-200 text-sm"
							href={`/search?is_single_origin=false`}
							transition:slide={{ duration: 400 }}
						>
							<Combine class="mr-1 w-3 h-3" />
							Blend
						</a>
					{/if}
					{#if bean.cupping_score && bean.cupping_score > 0}
						<span
							class="inline-flex items-center bg-yellow-100 dark:bg-yellow-900/40 dark:shadow-[0_0_10px_rgba(234,179,8,0.3)] dark:drop-shadow-[0_0_4px_rgba(234,179,8,0.8)] px-3 py-1 dark:border dark:border-yellow-400/50 rounded-full font-medium text-yellow-800 dark:text-yellow-200 text-sm"
							transition:slide={{ duration: 400 }}
						>
							<Star class="mr-1 w-3 h-3" />
							{bean.cupping_score}/100
						</span>
					{/if}
				</div>
			</div>
			<!-- User Notes -->
			{#await savedStatus then status}
				{#if status.saved}
					<div transition:slide|global>
						<Card
							class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30 border-primary/20"
						>
							<CardHeader>
								<div class="flex justify-between items-center">
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
									savedBeanId={status.savedBeanId!}
									initialNotes={status.notes}
									textareaClass="min-h-[140px]"
									placeholder="What did you think of this coffee? (grind size, temperature, flavour notes...)"
									onNoteChange={(n) => (localNotes = n)}
								/>
							</CardContent>
						</Card>
					</div>
				{/if}
			{/await}
			<!-- Tasting Notes -->
			{#if bean.tasting_notes && bean.tasting_notes.length > 0}
				<Card
					class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
				>
					<CardHeader>
						<CardTitle
							class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300"
						>
							<Grape class="mr-2 w-5 h-5" />
							Tasting Notes
						</CardTitle>
					</CardHeader>
					<CardContent>
						<div class="flex flex-wrap gap-2">
							{#each bean.tasting_notes as note, note_index (typeof note === "string" ? note : note.note)}
								{@const noteText =
									typeof note === "string" ? note : note.note}
								{@const flavourCategoryColors =
									getFlavourCategoryColors(
										typeof note === "string"
											? ""
											: (note.primary_category ?? ""),
									)}
								<div
									animate:flip={{ duration: 400 }}
									style="display: contents;"
								>
									<a
										class="inline-flex items-center {flavourCategoryColors.bg} {flavourCategoryColors.darkBg} {flavourCategoryColors.text} {flavourCategoryColors.darkText} dark:shadow-[0_0_6px_rgba(34,211,238,0.2)] px-3 py-1 dark:border dark:border-cyan-500/30 rounded-full font-medium text-sm"
										href={`/search?tasting_notes_query="${encodeURIComponent(noteText)}"`}
										transition:slide={{
											delay: 50 * note_index,
											duration: 400,
										}}
									>
										{noteText}
									</a>
								</div>
							{/each}
						</div>
					</CardContent>
				</Card>
			{/if}

			<!-- Description -->
			{#if bean.description && bean.description.trim()}
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
									marked.parse(bean.description) as string,
								)}
							{:else}
								{bean.description.replace(/  +\n/g, "<br />")}
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
											<span class="font-medium"
												>{origin.country_full_name ||
													origin.country}</span
											>
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
											<span>{origin.region}</span>
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
											<span>{origin.farm}</span>
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
												>{origin.latitude.toFixed(4)}, {origin.longitude.toFixed(
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
											<span>{origin.process}</span>
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
											<span>{origin.variety}</span>
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
												).toLocaleDateString("en-GB", {
													year: "numeric",
													month: "long",
												})}</span
											>
										</div>
									{/if}
								</div>
							</div>
						{/each}
					</div>

					<!-- Single Origin Status -->
					<div class="flex items-center space-x-2 mt-4 pt-4 border-t">
						<Package class="mr-1 w-4 h-4 text-muted-foreground" />
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
			<!-- Purchase Information -->
			<Card
				class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
			>
				<CardHeader>
					<CardTitle
						class="dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300"
						>Purchase</CardTitle
					>
				</CardHeader>
				<CardContent class="space-y-4">
					<!-- Price and Weight -->
					{#if bean.price || bean.weight}
						<div
							class="flex flex-wrap justify-between gap-4 text-2xl"
						>
							{#if bean.price}
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
					{#if bean.in_stock !== null}
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
								title={new Date(bean.scraped_at).toLocaleString(
									"en-GB",
								)}
								>(checked {humanizeDuration(
									new Date().getTime() -
										new Date(bean.scraped_at).getTime(),
								)} ago)
							</span>
						</div>
					{/if}
					{#if bean.url}
						<Button class="w-full" href={bean.url} target="_blank">
							<ExternalLink class="mr-2 w-4 h-4" />
							View on {bean.roaster}
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
								>First spotted:</span
							>
							<span
								title={new Date(bean.date_added).toLocaleString(
									"en-GB",
								)}
								>{humanizeDuration(
									new Date().getTime() -
										new Date(bean.date_added).getTime(),
								)} ago</span
							>
						</div>
						<hr />
						<div class="w-full text-muted-foreground text-justify">
							Prices and stock status may not always be accurate.
							If you spot an error, please <a
								target="_blank"
								class="underline"
								href="https://github.com/dldx/kissaten/issues"
								>file an issue</a
							>.
						</div>
					</div>
				</CardContent>
			</Card>

			<!-- Recommendations -->
			{#if recommendations && recommendations.length > 0}
				<Card
					class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
				>
					<CardHeader>
						<CardTitle
							class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300"
						>
							<Star class="mr-2 w-5 h-5" />
							Similar Beans
						</CardTitle>
						<CardDescription
							>Based on tasting notes and processing method</CardDescription
						>
					</CardHeader>
					<CardContent>
						<div class="space-y-4">
							{#each recommendations.slice(0, 4) as recBean}
								<div
									class="flex gap-3 pb-4 last:pb-0 border-b last:border-b-0"
								>
									<!-- Small image for recommendation -->
									<div class="flex-shrink-0">
										<CoffeeBeanImage
											bean={recBean}
											size="sm"
											class="rounded-md"
										/>
									</div>

									<div class="flex-1 space-y-2">
										<a
											href={"/roasters" +
												recBean.bean_url_path}
											class="block hover:text-primary dark:hover:text-cyan-300 transition-colors"
										>
											<h4
												class="dark:drop-shadow-[0_0_6px_rgba(34,211,238,0.4)] font-medium dark:text-cyan-200/90 line-clamp-2"
											>
												{recBean.name}
											</h4>
										</a>
										<p
											class="text-muted-foreground dark:text-cyan-400/70 text-sm"
										>
											{recBean.roaster}
										</p>
										<div
											class="flex items-center text-muted-foreground text-xs"
										>
											<MapPin class="mr-1 w-3 h-3" />
											<span
												>{api.getOriginDisplayString(
													recBean,
												)}</span
											>
										</div>
										{#if recBean.price}
											<div
												class="flex justify-between items-center"
											>
												<span
													class="dark:drop-shadow-[0_0_6px_rgba(16,185,129,0.6)] font-medium dark:text-emerald-300/90 text-sm"
													>{formatPrice(
														recBean.price,
														recBean.currency,
													)}</span
												>
												{#if recBean.weight}
													<span
														class="text-muted-foreground text-xs"
														>{recBean.weight}g</span
													>
												{/if}
											</div>
										{/if}
										{#if recBean.tasting_notes && recBean.tasting_notes.length > 0}
											<div class="flex flex-wrap gap-1">
												{#each recBean.tasting_notes.slice(0, 2) as note}
													<span
														class="inline-flex items-center bg-primary/10 dark:bg-slate-800/60 dark:shadow-[0_0_6px_rgba(34,211,238,0.2)] px-2 py-0.5 dark:border dark:border-cyan-500/30 rounded-full dark:text-cyan-200/90 text-xs"
													>
														{note}
													</span>
												{/each}
												{#if recBean.tasting_notes.length > 2}
													<span
														class="text-muted-foreground text-xs"
														>+{recBean.tasting_notes
															.length - 2}</span
													>
												{/if}
											</div>
										{/if}
									</div>
								</div>
							{/each}
							{#if recommendations.length > 4}
								<Button
									variant="outline"
									size="sm"
									class="w-full"
								>
									View All Recommendations
								</Button>
							{/if}
						</div>
					</CardContent>
				</Card>
			{/if}
		</div>
	</div>
</div>
