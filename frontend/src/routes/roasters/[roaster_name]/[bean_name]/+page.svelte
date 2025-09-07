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
	import { formatPrice } from "$lib/utils";
	import { api } from "$lib/api";
	import {
		Coffee,
		MapPin,
		DollarSign,
		Weight,
		Calendar,
		Zap,
		Grape,
		Mountain,
		User,
		Building,
		Clock,
		ExternalLink,
		ArrowLeft,
		Star,
		Package,
		Globe,
		Combine,
		BadgePoundSterling,
		Flame,
		Droplets,
		Leaf,
		Ban,
		TreePine,
	} from "lucide-svelte";
	import type { PageData } from "./$types";
	import 'iconify-icon';

	let { data } = $props();

	let { bean, recommendations } = $derived({
		bean: data.bean,
		recommendations: data.recommendations || [],
	});

	// Helper computations for origins
	const originDisplay = $derived(api.getOriginDisplayString(bean));
	const processes = $derived(api.getBeanProcesses(bean));
	const varieties = $derived(api.getVarieties(bean));

	// Deduplicated lists for display
	const uniqueCountries = $derived.by(() => {
		const countries = bean.origins
			.map(origin => origin.country)
			.filter(country => country != null);
		return [...new Set(countries)];
	});

	const uniqueProcesses = $derived([...new Set(processes)]);

	const uniqueVarieties = $derived( [...new Set(varieties)]);

	// Helper to get country display info
	const getCountryDisplayInfo = (countryCode: string) => {
		const origin = bean.origins.find(o => o.country === countryCode);
		return {
			code: countryCode,
			fullName: origin?.country_full_name || countryCode
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
					<div class="space-y-2">
						<h1 class="dark:drop-shadow-[0_0_12px_rgba(34,211,238,0.8)] font-bold dark:text-cyan-100 text-4xl">{bean.name}</h1>
						<div
							class="flex items-center dark:drop-shadow-[0_0_6px_rgba(34,211,238,0.4)] text-muted-foreground dark:text-cyan-300/80 text-xl"
						>
							<Coffee class="mr-2 w-5 h-5" />
							<span>Roasted by <a href={`/search?roaster=${encodeURIComponent(bean.roaster)}`} class="dark:hover:text-cyan-100 dark:text-cyan-200">{bean.roaster}</a></span>
						</div>
					</div>
				</div>

				<!-- Main Attributes -->
				<div class="flex flex-wrap gap-2">
					{#if uniqueCountries.length > 0}
						{#each uniqueCountries as country}
						{@const countryInfo = getCountryDisplayInfo(country)}
						<a
							class="inline-flex items-center bg-red-100 hover:bg-red-200 dark:bg-red-900/40 dark:shadow-[0_0_10px_rgba(239,68,68,0.3)] dark:drop-shadow-[0_0_4px_rgba(239,68,68,0.8)] px-3 py-1 dark:border dark:border-red-400/50 dark:hover:border-red-300 rounded-full font-medium text-red-800 dark:text-red-200 text-sm"
							href={`/search?origin=${country}`}
						>
							<iconify-icon icon="circle-flags:{country?.toLowerCase()}" class="mr-2 w-3 h-3"></iconify-icon>
							{countryInfo.fullName}
						</a>
						{/each}
					{/if}
					{#if uniqueProcesses.length > 0}
						<span
							class="inline-flex items-center bg-secondary hover:bg-secondary-hover dark:bg-cyan-900/40 dark:shadow-[0_0_10px_rgba(34,211,238,0.3)] dark:drop-shadow-[0_0_4px_rgba(34,211,238,0.8)] px-3 py-1 dark:border dark:border-cyan-400/50 rounded-full font-medium dark:text-cyan-200 text-sm"
						>
							<Droplets class="mr-1 w-3 h-3" />
						{#each uniqueProcesses as process, index (process)}
							{#if index > 0}/{/if}
						<a
							href={`/process/${api.normalizeProcessName(process)}`}
							>
							{process}
						</a>
						{/each}
						</span>
					{/if}
					{#if uniqueVarieties.length > 0}
						<span
							class="inline-flex items-center bg-accent dark:bg-emerald-900/40 dark:shadow-[0_0_10px_rgba(16,185,129,0.3)] dark:drop-shadow-[0_0_4px_rgba(16,185,129,0.8)] px-3 py-1 dark:border dark:border-emerald-400/50 rounded-full font-medium dark:text-emerald-200 text-sm text-accent-foreground hover:bg-accent-hover"
						>
							<Leaf class="mr-1 w-3 h-3" />
						{#each uniqueVarieties as variety, index (variety)}
							{#if index > 0}/{/if}
							<a
							href={`/varietals/${api.normalizeVarietalName(variety)}`}
							>
							{variety}
							</a>
						{/each}
						</span>
					{/if}
					{#if bean.roast_level}
						<span
							class="inline-flex items-center bg-primary dark:bg-orange-900/40 dark:shadow-[0_0_10px_rgba(251,146,60,0.3)] dark:drop-shadow-[0_0_4px_rgba(251,146,60,0.8)] px-3 py-1 dark:border dark:border-orange-400/50 rounded-full font-medium text-primary-foreground dark:text-orange-200 text-sm"
						>
							<a href={`/search?roast_level=${bean.roast_level}`}
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
						>
							<a href={`/search?roast_profile=${bean.roast_profile}`}
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
						>
							<Ban class="mr-1 w-3 h-3" />
							Decaf
						</a>
					{/if}
					{#if !bean.is_single_origin}
						<a
							class="inline-flex items-center bg-indigo-100 dark:bg-pink-900/40 dark:shadow-[0_0_10px_rgba(236,72,153,0.3)] dark:drop-shadow-[0_0_4px_rgba(236,72,153,0.8)] px-3 py-1 dark:border dark:border-pink-400/50 rounded-full font-medium text-indigo-800 dark:text-pink-200 text-sm"
							href={`/search?is_single_origin=false`}
						>
							<Combine class="mr-1 w-3 h-3" />
							Blend
						</a>
					{/if}
					{#if bean.cupping_score && bean.cupping_score > 0}
						<span
							class="inline-flex items-center bg-yellow-100 dark:bg-yellow-900/40 dark:shadow-[0_0_10px_rgba(234,179,8,0.3)] dark:drop-shadow-[0_0_4px_rgba(234,179,8,0.8)] px-3 py-1 dark:border dark:border-yellow-400/50 rounded-full font-medium text-yellow-800 dark:text-yellow-200 text-sm"
						>
							<Star class="mr-1 w-3 h-3" />
							{bean.cupping_score}/100
						</span>
					{/if}
				</div>
			</div>
			<!-- Tasting Notes -->
			{#if bean.tasting_notes && bean.tasting_notes.length > 0}
				<Card class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30">
					<CardHeader>
						<CardTitle class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300">
							<Grape class="mr-2 w-5 h-5" />
							Tasting Notes
						</CardTitle>
					</CardHeader>
					<CardContent>
						<div class="flex flex-wrap gap-2">
							{#each bean.tasting_notes as note}
								<a
									class="inline-flex items-center bg-primary/10 dark:bg-slate-800/60 dark:shadow-[0_0_6px_rgba(34,211,238,0.2)] px-3 py-1 dark:border dark:border-cyan-500/30 rounded-full font-medium text-primary dark:text-cyan-200/90 text-sm"
									href={`/search?tasting_notes_query="${encodeURIComponent(note)}"`}
								>
									{note}
								</a>
							{/each}
						</div>
					</CardContent>
				</Card>
			{/if}


			<!-- Description -->
			{#if bean.description && bean.description.trim()}
				<Card class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30">
					<CardHeader>
						<CardTitle class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300">
							<Coffee class="mr-2 w-5 h-5" />
							Description
						</CardTitle>
					</CardHeader>
					<CardContent>
						<p class="text-muted-foreground leading-relaxed">
							{bean.description}
						</p>
					</CardContent>
				</Card>
			{/if}

			<!-- Origin Details -->
			<Card class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30">
				<CardHeader>
					<CardTitle class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300">
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
									{#if origin.elevation && origin.elevation > 0}
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
											<span>{origin.elevation}m</span>
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
			<Card class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30">
				<CardHeader>
					<CardTitle class="dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300">Purchase</CardTitle>
				</CardHeader>
				<CardContent class="space-y-4">
					<!-- Price and Weight -->
					{#if bean.price || bean.weight}
						<div class="flex flex-wrap gap-4 text-2xl">
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
						<div class="flex items-center space-x-2">
							<span
								class="text-sm {bean.in_stock
									? 'text-green-600 dark:text-emerald-300 dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]'
									: 'text-red-600 dark:text-red-300 dark:drop-shadow-[0_0_8px_rgba(239,68,68,0.8)]'}"
							>
								{bean.in_stock
									? "✅ In stock"
									: "❌ Out of stock"}
							</span>
						</div>
					{/if}
					{#if bean.url}
						<Button
							class="w-full"
							onclick={() => window.open(bean.url, "_blank")}
						>
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
							<span class="text-muted-foreground">Updated:</span>
							<span>{formatDate(bean.scraped_at)}</span>
						</div>
					</div>
				</CardContent>
			</Card>

			<!-- Recommendations -->
			{#if recommendations && recommendations.length > 0}
				<Card class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30">
					<CardHeader>
						<CardTitle class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300">
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
