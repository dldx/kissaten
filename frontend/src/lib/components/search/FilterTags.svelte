<script lang="ts">
	import {
		X,
		Search,
		Citrus,
		Coffee,
		MapPin,
		User,
		TreePine,
		Flame,
		Droplets,
		Leaf,
		CreditCard,
		Scale,
		Mountain,
		CheckCircle,
		Ban,
		Zap,
		Combine,
		Plus,
	} from "lucide-svelte";
	import Broom from "virtual:icons/mdi/broom";
	import { cn, formatPrice, getCountryFlag } from "$lib/utils";
	import { type RoasterLocationOption, roasterLocationDisplayName } from "$lib/utils/roasterLocations";
	import { Button } from "../ui/button";
	import { currencyState } from "$lib/stores/currency.svelte";

	interface FilterTag {
		key: string;
		label: string;
		value: string;
		originalValue?: string; // Original value for removal (e.g., country code, location code)
		icon: any; // Lucide icon component
		type:
			| "search"
			| "tasting_notes"
			| "roaster"
			| "roaster_location"
			| "origin"
			| "roast_level"
			| "roast_profile"
			| "process"
			| "variety"
			| "price_range"
			| "weight_range"
			| "elevation_range"
			| "region"
			| "producer"
			| "farm"
			| "in_stock"
			| "is_tasting_kit"
			| "is_decaf"
			| "is_single_origin"
			| "min_large_weight";
		isOrigin?: boolean; // Special flag for origin styling
	}

	interface OriginOption {
		value: string;
		text: string;
	}

	interface Props {
		// Filter values
		searchQuery: string;
		tastingNotesQuery: string;
		roasterFilter: string[];
		roasterLocationFilter: string[];
		originFilter: string[];
		roastLevelFilter: string;
		roastProfileFilter: string;
		processFilter: string;
		varietyFilter: string;
		minPrice: string;
		maxPrice: string;
		minWeight: string;
		maxWeight: string;
		minElevation: string;
		maxElevation: string;
		minLargeWeight: string;
		regionFilter: string;
		producerFilter: string;
		farmFilter: string;
		inStockOnly: boolean;
		isTastingKit: boolean;
		isDecaf: boolean | undefined;
		isSingleOrigin: boolean | undefined;

		// Options
		originOptions?: OriginOption[];
		roasterLocationOptions?: RoasterLocationOption[];
		defaultRoasterLocations?: string[];

		// Callbacks
		onRemoveFilter: (type: string, value?: string) => void;
		onClearAll: () => void;
		onAddRoasterLocationDefaults?: () => void;

		// Styling
		class?: string;
	}

	let {
		searchQuery,
		tastingNotesQuery,
		roasterFilter,
		roasterLocationFilter,
		originFilter,
		roastLevelFilter,
		roastProfileFilter,
		processFilter,
		varietyFilter,
		minPrice,
		maxPrice,
		minWeight,
		maxWeight,
		minElevation,
		maxElevation,
		minLargeWeight,
		regionFilter,
		producerFilter,
		farmFilter,
		inStockOnly,
		isTastingKit,
		isDecaf,
		isSingleOrigin,
		originOptions,
		roasterLocationOptions,
		defaultRoasterLocations = [],
		onRemoveFilter,
		onClearAll,
		onAddRoasterLocationDefaults,
		class: className = "",
	}: Props = $props();

	// Generate filter tags from current filter state
	const filterTags = $derived.by(() => {
		const tags: FilterTag[] = [];

		// Search query
		if (searchQuery) {
			tags.push({
				key: "search",
				label: "search query",
				value: searchQuery,
				icon: Search,
				type: "search",
			});
		}

		// Tasting notes query
		if (tastingNotesQuery) {
			// Parse tasting notes query to show individual notes
			const notes = tastingNotesQuery
				.split(/[&|]/)
				.map((note) => note.trim().replace(/"/g, ""))
				.filter(
					(note) =>
						note && note !== "General" && note !== "Tasting Notes",
				);

			notes.forEach((note) => {
				tags.push({
					key: `tasting_note_${note}`,
					label: "tasting note",
					value: note,
					icon: Citrus,
					type: "tasting_notes",
				});
			});
		}

		// Roaster filters
		[...new Set(roasterFilter)].forEach((roaster) => {
			tags.push({
				key: `roaster_${roaster}`,
				label: "roaster",
				value: roaster,
				icon: Coffee,
				type: "roaster",
			});
		});

		// Roaster location filters
		[...new Set(roasterLocationFilter)].forEach((location) => {
			// Resolve the location code to its human-readable name (e.g.
			// "XE" -> "Europe"), falling back to the raw code.
			const countryName = roasterLocationDisplayName(location, roasterLocationOptions);

			// Format as "{Country name} roasters"
			const displayValue = `Roasters in ${countryName}`;

			tags.push({
				key: `roaster_location_${location}`,
				label: "roaster location filter",
				value: displayValue,
				originalValue: location, // Store original location code for removal
				icon: MapPin,
				type: "roaster_location",
			});
		});

		// Origin filters
		[...new Set(originFilter)].forEach((origin) => {
			// Find the full country name from originOptions
			const originOption = originOptions?.find(
				(option) => option.value === origin,
			);
			const countryName = originOption?.text || origin;
			const countryFlag = getCountryFlag(origin);

			tags.push({
				key: `origin_${origin}`,
				label: "coffee origin",
				value: `${countryFlag} ${countryName}`,
				originalValue: origin, // Store original country code for removal
				icon: MapPin,
				type: "origin",
				isOrigin: true, // Special flag for origin styling
			});
		});

		// Roast level
		if (roastLevelFilter) {
			tags.push({
				key: "roast_level",
				label: "roast level",
				value: roastLevelFilter,
				icon: Flame,
				type: "roast_level",
			});
		}

		// Roast profile
		if (roastProfileFilter) {
			tags.push({
				key: "roast_profile",
				label: "roast profile",
				value: roastProfileFilter,
				icon: Coffee,
				type: "roast_profile",
			});
		}

		// Process
		if (processFilter) {
			tags.push({
				key: "process",
				label: "processing method",
				value: processFilter,
				icon: Droplets,
				type: "process",
			});
		}

		// Variety
		if (varietyFilter) {
			tags.push({
				key: "variety",
				label: "varietal",
				value: varietyFilter,
				icon: Leaf,
				type: "variety",
			});
		}

		// Price range
		if (minPrice || maxPrice) {
			let priceRange = "";
			if (minPrice && maxPrice) {
				priceRange = `${formatPrice(parseFloat(minPrice), currencyState.selectedCurrency)} - ${formatPrice(parseFloat(maxPrice), currencyState.selectedCurrency)}`;
			} else if (minPrice) {
				priceRange = `${formatPrice(parseFloat(minPrice), currencyState.selectedCurrency)}+`;
			} else if (maxPrice) {
				priceRange = `≤${formatPrice(parseFloat(maxPrice), currencyState.selectedCurrency)}`;
			}
			tags.push({
				key: "price_range",
				label: "price range",
				value: priceRange,
				icon: CreditCard,
				type: "price_range",
			});
		}

		// Weight range
		if (minWeight || maxWeight) {
			let weightRange = "";
			if (minWeight && maxWeight) {
				weightRange = `${minWeight}g - ${maxWeight}g`;
			} else if (minWeight) {
				weightRange = `${minWeight}g+`;
			} else if (maxWeight) {
				weightRange = `≤${maxWeight}g`;
			}
			tags.push({
				key: "weight_range",
				label: "weight range",
				value: weightRange,
				icon: Scale,
				type: "weight_range",
			});
		}

		// Elevation range
		if (minElevation || maxElevation) {
			let elevationRange = "";
			if (minElevation && maxElevation) {
				elevationRange = `${minElevation}m - ${maxElevation}m`;
			} else if (minElevation) {
				elevationRange = `${minElevation}m+`;
			} else if (maxElevation) {
				elevationRange = `≤${maxElevation}m`;
			}
			tags.push({
				key: "elevation_range",
				label: "elevation range",
				value: elevationRange,
				icon: Mountain,
				type: "elevation_range",
			});
		}

		// Min large bag weight
		if (minLargeWeight) {
			tags.push({
				key: "min_large_weight",
				label: "min bag size",
				value: `${minLargeWeight}g`,
				icon: Scale,
				type: "min_large_weight",
			});
		}

		// Region
		if (regionFilter) {
			tags.push({
				key: "region",
				label: "region",
				value: regionFilter,
				icon: MapPin,
				type: "region",
			});
		}

		// Producer
		if (producerFilter) {
			tags.push({
				key: "producer",
				label: "producer",
				value: producerFilter,
				icon: User,
				type: "producer",
			});
		}

		// Farm
		if (farmFilter) {
			tags.push({
				key: "farm",
				label: "farm",
				value: farmFilter,
				icon: TreePine,
				type: "farm",
			});
		}

		// In stock only
		if (inStockOnly) {
			tags.push({
				key: "in_stock",
				label: "",
				value: "In stock only",
				icon: CheckCircle,
				type: "in_stock",
			});
		}

		// Sampling kits
		if (isTastingKit) {
			tags.push({
				key: "is_tasting_kit",
				label: "",
				value: "Sampling kits",
				icon: Coffee,
				type: "is_tasting_kit",
			});
		}

		// Decaf
		if (isDecaf !== undefined) {
			tags.push({
				key: "is_decaf",
				label: "decaf type",
				value: isDecaf ? "Decaf only" : "Caffeinated only",
				icon: isDecaf ? Ban : Zap,
				type: "is_decaf",
			});
		}

		// Single origin
		if (isSingleOrigin !== undefined) {
			tags.push({
				key: "is_single_origin",
				label: "blend type",
				value: isSingleOrigin ? "Single origin only" : "Blends only",
				icon: isSingleOrigin ? MapPin : Combine,
				type: "is_single_origin",
			});
		}

		return tags;
	});

	// Check if there are any active filters
	const hasActiveFilters = $derived(filterTags.length > 0);

	// Show suggested tag to re-add default roaster locations when the user
	// has cleared their roaster location filter but has saved defaults.
	const showLocationDefaultsSuggestion = $derived(
		roasterLocationFilter.length === 0 && defaultRoasterLocations.length > 0,
	);

	function handleRemoveTag(tag: FilterTag) {
		// Use originalValue for removal if available (for location/country codes), otherwise use display value
		const valueToRemove = tag.originalValue || tag.value;
		onRemoveFilter(tag.type, valueToRemove);
	}
</script>

{#if hasActiveFilters || showLocationDefaultsSuggestion}
	<div class={cn("bg-muted/50 p-3 border-0 rounded-lg", className)}>
		{#if hasActiveFilters}
			<div class="flex justify-between items-center mb-2">
				<span class="font-medium text-muted-foreground text-sm"
					>Active Filters</span
				>
				<Button
					variant="outline"
					size="icon"
					onclick={onClearAll}
					title="Clear all filters"
				>
					<Broom />
				</Button>
			</div>
		{/if}
		<div class="flex flex-wrap gap-2">
			{#each filterTags as tag (tag.key)}
				{@const IconComponent = tag.icon}
				<button
					onclick={() => handleRemoveTag(tag)}
					title="Click to remove {tag.label}: {tag.value}"
					class="inline-flex items-center gap-1 bg-background hover:bg-destructive/10 px-2.5 py-0.5 border border-border hover:border-destructive/20 rounded-full font-semibold text-xs transition-colors"
				>
					{#if !tag.isOrigin}
						<IconComponent class="w-3 h-3" />
					{/if}
					<span class="text-xs">{tag.value}</span>
					<X class="opacity-70 hover:opacity-100 w-3 h-3" />
				</button>
			{/each}
			{#if showLocationDefaultsSuggestion}
				<button
					onclick={onAddRoasterLocationDefaults}
					title="Add your default roaster locations back"
					class="inline-flex items-center gap-1 bg-primary/5 hover:bg-primary/10 px-2.5 py-0.5 border border-dashed border-primary/30 hover:border-primary/50 rounded-full font-medium text-xs text-primary transition-colors"
				>
					<Plus class="w-3 h-3" />
					<span class="text-xs">Roasters in your location</span>
				</button>
			{/if}
		</div>
	</div>
{/if}
