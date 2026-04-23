<script lang="ts">
	import { superForm } from "sveltekit-superforms";
	import { zodClient } from "sveltekit-superforms/adapters";
	import { beanFormSchema } from "$lib/schemas/beanFormSchema";
	import { addCustomBean, extractBeanFromImage } from "$lib/api/custom_beans.remote";
	import { Button } from "$lib/components/ui/button";
	import { Input } from "$lib/components/ui/input";
	import { Label } from "$lib/components/ui/label";
	import Textarea from "$lib/components/ui/textarea/textarea.svelte";
	import * as Select from "$lib/components/ui/select";
	import { Loader2, Plus, Trash2, Sparkles, Shield, Info, Camera, X, Settings2 } from "lucide-svelte";
	import { Switch } from "$lib/components/ui/switch";
	import { toast } from "svelte-sonner";
	import type { CoffeeBean, SmartSearchResult } from "$lib/api";
	import { cn, getFlavourCategoryColors, resizeImage } from "$lib/utils";
	import ImageCapture from "$lib/components/ui/ImageCapture.svelte";
	import {
		TASTING_CONVERSATION,
		DEFECT_CONVERSATION,
	} from "$lib/tasting/conversation";

	interface Props {
		initialData?: Partial<CoffeeBean> | null;
		onSuccess?: (result: { id: string; bean_url_path: string; bean: CoffeeBean }) => void;
		onCancel?: () => void;
	}

	let { initialData = null, onSuccess, onCancel }: Props = $props();

	let isAdvancedMode = $state(false);

	// Function to map initialData (from image search or existing) to form defaults
	function getDefaults() {
		return {
			name: initialData?.name || "",
			roaster: initialData?.roaster || "",
			roaster_location: (initialData as any)?.roaster_location || "",
			url: initialData?.url || "",
			description: initialData?.description || "",
			is_single_origin: initialData?.is_single_origin ?? true,
			roast_level: (initialData?.roast_level as any) || null,
			roast_profile: (initialData?.roast_profile as any) || null,
			price: initialData?.price || undefined,
			weight: initialData?.weight || undefined,
			currency: initialData?.currency || "GBP",
			is_decaf: initialData?.is_decaf || false,
			cupping_score: initialData?.cupping_score || null,
			tasting_notes: initialData?.tasting_notes?.map(n => typeof n === 'string' ? n : n.note) || [],
			image_data: (initialData as any)?.image_data || null,
			origins: initialData?.origins?.map(o => ({
				country: o.country || "",
				region: o.region || "",
				producer: o.producer || "",
				farm: o.farm || "",
				elevation_min: o.elevation_min || 0,
				elevation_max: o.elevation_max || 0,
				latitude: o.latitude || null,
				longitude: o.longitude || null,
				process: o.process || "",
				variety: o.variety || "",
				harvest_date: o.harvest_date || null,
				fob_price: o.fob_price || null,
				farm_gate_price: o.farm_gate_price || null,
				price_paid_to_producer: o.price_paid_to_producer || null,
				importer_name: o.importer_name || null,
			})) || [{
				country: "",
				region: "",
				producer: "",
				farm: "",
				elevation_min: 0,
				elevation_max: 0,
				latitude: null,
				longitude: null,
				process: "",
				variety: "",
				harvest_date: null,
				fob_price: null,
				farm_gate_price: null,
				price_paid_to_producer: null,
				importer_name: null,
			}],
			price_paid_for_green_coffee: initialData?.price_paid_for_green_coffee || null,
			currency_of_price_paid_for_green_coffee: initialData?.currency_of_price_paid_for_green_coffee || null,
		};
	}

	const form = superForm(getDefaults(), {
		validators: zodClient(beanFormSchema),
		SPA: true,
		dataType: "json",
		invalidateAll: false,
		onUpdate: async ({ form }) => {
			if (!form.valid) return;

			try {
				const submissionData = {
					...form.data,
					roaster_location: form.data.roaster_location || null,
					price_paid_for_green_coffee: form.data.price_paid_for_green_coffee || null,
					currency_of_price_paid_for_green_coffee: form.data.currency_of_price_paid_for_green_coffee || null,
					cupping_score: form.data.cupping_score || null,
					origins: form.data.origins.map(o => ({
						...o,
						harvest_date: o.harvest_date || undefined,
						latitude: o.latitude || undefined,
						longitude: o.longitude || undefined,
						fob_price: o.fob_price || undefined,
						farm_gate_price: o.farm_gate_price || undefined,
						price_paid_to_producer: o.price_paid_to_producer || undefined,
						importer_name: o.importer_name || undefined,
					}))
				};
				const result = await addCustomBean(submissionData as any);
				toast.success("Bean added to your private collection!");
				if (onSuccess) onSuccess(result);
			} catch (err: any) {
				toast.error(err.message || "Failed to add bean");
			}
		}
	});

	const { form: formData, enhance, delayed, errors } = form;

	function addOrigin() {
		$formData.origins = [...$formData.origins, {
				country: "",
				region: "",
				producer: "",
				farm: "",
				elevation_min: 0,
				elevation_max: 0,
				latitude: null,
				longitude: null,
				process: "",
				variety: "",
				harvest_date: null,
				fob_price: null,
				farm_gate_price: null,
				price_paid_to_producer: null,
				importer_name: null,
		}];
	}

	function removeOrigin(index: number) {
		if ($formData.origins.length > 1) {
			$formData.origins = $formData.origins.filter((_, i) => i !== index);
		}
	}

	function addTastingNote(note: string) {
		if (note.trim() && !$formData.tasting_notes.includes(note.trim())) {
			$formData.tasting_notes = [...$formData.tasting_notes, note.trim()];
		}
	}

	function removeTastingNote(index: number) {
		$formData.tasting_notes = $formData.tasting_notes.filter((_, i) => i !== index);
	}

	let newNote = $state("");
	let isResizing = $state(false);
	let isExtracting = $state(false);

	async function onImageSelected(resized: File, base64Data: string) {
		$formData.image_data = base64Data;

		// Automatically try to extract details from the image
		isExtracting = true;
		try {
			toast.info("Extracting coffee details from image...");
			const extractedBeanData = await extractBeanFromImage(base64Data);

			if (extractedBeanData) {
				// Merge extracted data into form, prioritizing non-empty values
				if (extractedBeanData.name) $formData.name = extractedBeanData.name;
				if (extractedBeanData.roaster) $formData.roaster = extractedBeanData.roaster;
				if (extractedBeanData.description) $formData.description = extractedBeanData.description;
				if (extractedBeanData.roast_level) $formData.roast_level = extractedBeanData.roast_level as any;
				if (extractedBeanData.roast_profile) $formData.roast_profile = extractedBeanData.roast_profile as any;
				if (extractedBeanData.price) $formData.price = extractedBeanData.price;
				if (extractedBeanData.weight) $formData.weight = extractedBeanData.weight;
				if (extractedBeanData.currency) $formData.currency = extractedBeanData.currency;
				if (extractedBeanData.is_decaf !== undefined) $formData.is_decaf = extractedBeanData.is_decaf;
				if (extractedBeanData.cupping_score) $formData.cupping_score = extractedBeanData.cupping_score;
				if (extractedBeanData.price_paid_for_green_coffee) $formData.price_paid_for_green_coffee = extractedBeanData.price_paid_for_green_coffee;
				if (extractedBeanData.currency_of_price_paid_for_green_coffee) $formData.currency_of_price_paid_for_green_coffee = extractedBeanData.currency_of_price_paid_for_green_coffee;

				if (extractedBeanData.tasting_notes && extractedBeanData.tasting_notes.length > 0) {
					const notes = extractedBeanData.tasting_notes.map(n => typeof n === 'string' ? n : n.note);
					// Add only new notes
					notes.forEach(note => {
						if (!$formData.tasting_notes.includes(note)) {
							$formData.tasting_notes = [...$formData.tasting_notes, note];
						}
					});
				}

				if (extractedBeanData.origins && extractedBeanData.origins.length > 0) {
					// If we currently have just one empty origin, replace it
					const isFirstOriginEmpty = $formData.origins.length === 1 &&
												!$formData.origins[0].country &&
												!$formData.origins[0].region;

					const newOrigins = extractedBeanData.origins.map(o => ({
						country: o.country || "",
						region: o.region || "",
						producer: o.producer || "",
						farm: o.farm || "",
						elevation_min: o.elevation_min || 0,
						elevation_max: o.elevation_max || 0,
						latitude: o.latitude || null,
						longitude: o.longitude || null,
						process: o.process || "",
						variety: o.variety || "",
						harvest_date: o.harvest_date || null,
						fob_price: o.fob_price || null,
						farm_gate_price: o.farm_gate_price || null,
						price_paid_to_producer: o.price_paid_to_producer || null,
						importer_name: o.importer_name || null,
					}));

					if (isFirstOriginEmpty) {
						$formData.origins = newOrigins;
					} else {
						// Append new origins if they aren't duplicates
						newOrigins.forEach(newO => {
							const exists = $formData.origins.some(oldO =>
								oldO.country === newO.country && oldO.region === newO.region
							);
							if (!exists) {
								$formData.origins = [...$formData.origins, newO];
							}
						});
					}
				}

				toast.success("Details extracted successfully!");
			}
		} catch (err: any) {
			console.error("Extraction failed:", err);
			toast.error("Could not extract details automatically, but image is saved.");
		} finally {
			isExtracting = false;
		}
	}

	function removeImage() {
		$formData.image_data = null;
	}

	const roastLevels = ["Extra-Light", "Light", "Medium-Light", "Medium", "Medium-Dark", "Dark"];
	const roastProfiles = ["Espresso", "Filter", "Omni", "Both"];

	function getCategoryForNote(noteName: string) {
		const categories = [...TASTING_CONVERSATION, ...DEFECT_CONVERSATION];
		return categories.find(
			(c) =>
				c.name === noteName ||
				c.flavors?.some((f) => (typeof f === "string" ? f : f.name) === noteName) ||
				c.subTypes?.some(
					(s) => s.name === noteName || s.flavors.some((f) => (typeof f === "string" ? f : f.name) === noteName)
				),
		);
	}
</script>

<form use:enhance class="space-y-6 pb-4">
	<div class="space-y-2">
		<div class="flex justify-between items-center mb-1">
			<Label>Bean Label</Label>
			<div class="flex items-center gap-2">
				<span class="text-muted-foreground text-xs">{isAdvancedMode ? 'Showing all fields' : 'Simplified view'}</span>
				<Switch bind:checked={isAdvancedMode} />
			</div>
		</div>
		<div class="flex items-center gap-4">
			<ImageCapture
				onImageSelected={onImageSelected}
				onClear={removeImage}
				preview={$formData.image_data}
				loading={isResizing || isExtracting}
				label="Add Photo"
				class={$formData.image_data ? "w-24 h-24" : "flex flex-col justify-center items-center gap-2 bg-muted/30 hover:bg-muted/50 rounded-lg w-24 h-24 text-muted-foreground hover:text-primary transition-all"}
				triggerVariant="ghost"
			/>
			<div class="flex-1 text-muted-foreground text-xs leading-relaxed">
				<p>Upload a photo of the bean label to extract details.</p>
				{#if isExtracting}
					<p class="mt-1 font-medium text-primary italic animate-pulse">Analyzing image with AI...</p>
				{:else if $formData.image_data}
					<div class="flex items-center gap-1.5 mt-1 text-primary">
						<Sparkles class="w-3 h-3" />
						<span>AI has extracted some details! Check below.</span>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<div class="gap-4 grid grid-cols-1 md:grid-cols-2">
		<div class="space-y-2">
			<Label for="name">Bean Name</Label>
			<Input id="name" bind:value={$formData.name} placeholder="e.g. Geisha Spirits" />
			{#if $errors.name}<p class="text-destructive text-sm">{$errors.name}</p>{/if}
		</div>

		<div class="space-y-2">
			<Label for="roaster">Roaster</Label>
			<div class="flex gap-2">
				<Input id="roaster" class="flex-1" bind:value={$formData.roaster} placeholder="e.g. Manhattan Coffee Roasters" />
				{#if isAdvancedMode}
					<div class="w-24">
						<Input id="roaster_location" bind:value={$formData.roaster_location} placeholder="UK" maxlength={2} />
					</div>
				{/if}
			</div>
			<div class="flex justify-between">
				{#if $errors.roaster}<p class="text-destructive text-sm">{$errors.roaster}</p>{:else}<div></div>{/if}
				{#if isAdvancedMode && $errors.roaster_location}
					<p class="text-destructive text-sm text-right">{$errors.roaster_location}</p>
				{/if}
			</div>
		</div>
	</div>

	{#if isAdvancedMode}
		<div class="space-y-2">
			<Label for="url" class="flex items-center gap-1.5">
				Roaster Website
			</Label>
			<Input id="url" type="url" bind:value={$formData.url} placeholder="e.g. https://manhattancoffeeroasters.com" />
			{#if $errors.url}<p class="text-destructive text-sm">{$errors.url}</p>{/if}
		</div>
	{/if}

	<div class="space-y-4 bg-muted/30 p-4 border rounded-lg">
		<div class="flex justify-between items-center">
			<Label class="font-semibold text-lg">Origins</Label>
			<Button type="button" variant="outline" size="sm" onclick={addOrigin}>
				<Plus class="mr-2 w-4 h-4" /> Add Origin
			</Button>
		</div>

		{#each $formData.origins as origin, i}
			<div class="relative space-y-4 bg-background p-4 border rounded">
				{#if $formData.origins.length > 1}
					<Button type="button" variant="ghost" size="icon" class="top-2 right-2 absolute text-destructive" onclick={() => removeOrigin(i)}>
						<Trash2 class="w-4 h-4" />
					</Button>
				{/if}

				<div class="gap-4 grid grid-cols-1 sm:grid-cols-2">
					<div class="space-y-2">
						<Label>Country (2-letter code)</Label>
						<Input bind:value={origin.country} placeholder="CO" max-lengths={2} class="uppercase" />
					</div>
					<div class="space-y-2">
						<Label>Region</Label>
						<Input bind:value={origin.region} placeholder="Huila" />
					</div>
					{#if isAdvancedMode}
						<div class="space-y-2">
							<Label>Farm</Label>
							<Input bind:value={origin.farm} placeholder="La Palma y El Tucan" />
						</div>
						<div class="space-y-2">
							<Label>Producer</Label>
							<Input bind:value={origin.producer} placeholder="Juan Valdez" />
						</div>
					{/if}
					<div class="space-y-2">
						<Label>Variety</Label>
						<Input bind:value={origin.variety} placeholder="Pink Bourbon" />
					</div>
					<div class="space-y-2">
						<Label>Process</Label>
						<Input bind:value={origin.process} placeholder="Washed" />
					</div>
				</div>

				{#if isAdvancedMode}
					<div class="gap-4 grid grid-cols-1 sm:grid-cols-3">
						<div class="space-y-2">
							<Label>Harvest Date</Label>
							<Input type="date" value={origin.harvest_date || ''} oninput={(e: any) => origin.harvest_date = (e.currentTarget as HTMLInputElement).value || null} />
						</div>
						<div class="space-y-2">
							<Label>Elevation (Min-Max)</Label>
							<div class="flex items-center gap-2">
								<Input type="number" bind:value={origin.elevation_min} placeholder="1500" class="flex-1" />
								<span>-</span>
								<Input type="number" bind:value={origin.elevation_max} placeholder="1800" class="flex-1" />
							</div>
						</div>
						<div class="space-y-2">
							<Label>Importer</Label>
							<Input value={origin.importer_name || ''} oninput={(e: any) => origin.importer_name = (e.currentTarget as HTMLInputElement).value || null} placeholder="Nordic Approach" />
						</div>
					</div>

					<div class="gap-4 grid grid-cols-1 sm:grid-cols-3">
						<div class="space-y-2">
							<Label>FOB Price ($/kg)</Label>
							<Input type="number" step="0.01" value={origin.fob_price ?? ''} oninput={(e: any) => origin.fob_price = (e.currentTarget as HTMLInputElement).valueAsNumber || null} placeholder="0.00" />
						</div>
						<div class="space-y-2">
							<Label>Farm Gate ($/kg)</Label>
							<Input type="number" step="0.01" value={origin.farm_gate_price ?? ''} oninput={(e: any) => origin.farm_gate_price = (e.currentTarget as HTMLInputElement).valueAsNumber || null} placeholder="0.00" />
						</div>
						<div class="space-y-2">
							<Label>Paid to Producer ($/kg)</Label>
							<Input type="number" step="0.01" value={origin.price_paid_to_producer ?? ''} oninput={(e: any) => origin.price_paid_to_producer = (e.currentTarget as HTMLInputElement).valueAsNumber || null} placeholder="0.00" />
						</div>
					</div>

					<div class="gap-4 grid grid-cols-1 sm:grid-cols-2">
						<div class="space-y-2">
							<Label>Latitude</Label>
							<Input type="number" step="0.000001" value={origin.latitude ?? ''} oninput={(e: any) => origin.latitude = (e.currentTarget as HTMLInputElement).valueAsNumber || null} placeholder="2.441" />
						</div>
						<div class="space-y-2">
							<Label>Longitude</Label>
							<Input type="number" step="0.000001" value={origin.longitude ?? ''} oninput={(e: any) => origin.longitude = (e.currentTarget as HTMLInputElement).valueAsNumber || null} placeholder="-76.606" />
						</div>
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<div class="gap-4 grid grid-cols-2 sm:grid-cols-4">
		<div class="space-y-2">
			<Label>Roast Level</Label>
			<select bind:value={$formData.roast_level} class="flex bg-background disabled:opacity-50 px-3 py-2 border border-input rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ring-offset-background focus-visible:ring-offset-2 w-full h-10 text-sm disabled:cursor-not-allowed">
				<option value={null}>Select...</option>
				{#each roastLevels as level}
					<option value={level}>{level}</option>
				{/each}
			</select>
		</div>
		{#if isAdvancedMode}
			<div class="space-y-2">
				<Label>Roast Profile</Label>
				<select bind:value={$formData.roast_profile} class="flex bg-background disabled:opacity-50 px-3 py-2 border border-input rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ring-offset-background focus-visible:ring-offset-2 w-full h-10 text-sm disabled:cursor-not-allowed">
					<option value={null}>Select...</option>
					{#each roastProfiles as profile}
						<option value={profile}>{profile}</option>
					{/each}
				</select>
			</div>
			<div class="space-y-2">
				<Label>Cupping Score</Label>
				<Input type="number" step="0.1" value={$formData.cupping_score ?? ''} oninput={(e: any) => $formData.cupping_score = (e.currentTarget as HTMLInputElement).valueAsNumber || null} placeholder="85.5" />
			</div>
		{/if}
		<div class="space-y-2">
			<Label>Decaf</Label>
			<div class="flex items-center space-x-2 h-10">
				<input type="checkbox" bind:checked={$formData.is_decaf} id="is_decaf" class="w-4 h-4" />
				<Label for="is_decaf" class="font-normal">Decaffeinated</Label>
			</div>
		</div>
	</div>

	{#if isAdvancedMode}
		<div class="gap-4 grid grid-cols-1 sm:grid-cols-3">
			<div class="space-y-2">
				<Label>Price</Label>
				<div class="flex gap-2">
					<Input type="number" step="0.01" bind:value={$formData.price} placeholder="0.00" class="flex-1" />
					<Input bind:value={$formData.currency} placeholder="GBP" class="w-20 uppercase" />
				</div>
			</div>
			<div class="space-y-2">
				<Label>Weight (g)</Label>
				<Input type="number" bind:value={$formData.weight} placeholder="250" />
			</div>
			<div class="space-y-2">
				<Label>Green Coffee Price (per kg)</Label>
				<div class="flex gap-2">
					<Input type="number" step="0.01" value={$formData.price_paid_for_green_coffee ?? ''} oninput={(e: any) => $formData.price_paid_for_green_coffee = (e.currentTarget as HTMLInputElement).valueAsNumber || null} placeholder="0.00" class="flex-1" />
					<Input value={$formData.currency_of_price_paid_for_green_coffee || ''} oninput={(e: any) => $formData.currency_of_price_paid_for_green_coffee = (e.currentTarget as HTMLInputElement).value || null} placeholder="USD" class="w-20 uppercase" />
				</div>
			</div>
		</div>
	{/if}

	<div class="space-y-2">
		<Label>Roaster's Tasting Notes</Label>
		<div class="flex gap-2">
			<Input bind:value={newNote} placeholder="Add a note (e.g. Jasmine)" onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') { e.preventDefault(); addTastingNote(newNote); newNote = ''; } }} />
			<Button type="button" size="sm" onclick={() => { addTastingNote(newNote); newNote = ''; }}>Add</Button>
		</div>
		<div class="flex flex-wrap gap-2 mt-2">
			{#each $formData.tasting_notes as note, i}
				{@const cat = getCategoryForNote(note)}
				{@const colors = getFlavourCategoryColors(cat?.isDefect ? "defects" : cat?.name || "Other")}
				<span class={cn(
					"flex items-center gap-1 px-2 py-1 border rounded-full font-medium text-sm",
					cat?.isDefect
						? "border-destructive/30 bg-destructive/10 text-destructive"
						: cn(colors.bg, colors.text, colors.border, colors.darkBg, colors.darkText, colors.darkBorder)
				)}>
					{note}
					<button type="button" onclick={() => removeTastingNote(i)} class="hover:text-destructive">
						<Trash2 class="w-3 h-3" />
					</button>
				</span>
			{/each}
		</div>
	</div>

	<div class="space-y-2">
		<Label for="description">Description</Label>
		<Textarea id="description" bind:value={$formData.description} placeholder="Enter any additional details..." rows={3} />
	</div>

	<div class="flex flex-wrap md:flex-nowrap justify-end items-center gap-3 bg-background/80 backdrop-blur pt-4 pb-2 border-t">
		<div class="flex items-center gap-2 mr-auto px-3 py-1.5 text-blue-700 dark:text-blue-300 text-xs text-xs">
			<span>Visible only to you. Roaster details help improve the public database.</span>
		</div>
		<div class="flex gap-2">
			<Button type="button" variant="outline" onclick={onCancel}>Cancel</Button>
			<Button type="submit" disabled={$delayed}>
				{#if $delayed}
					<Loader2 class="mr-2 w-4 h-4 animate-spin" />
					Saving...
				{:else}
					Add to your collection
				{/if}
			</Button>
		</div>
	</div>
</form>
