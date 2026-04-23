<script lang="ts">
	import { superForm } from "sveltekit-superforms";
	import { zodClient } from "sveltekit-superforms/adapters";
	import { beanFormSchema } from "$lib/schemas/beanFormSchema";
	import { addCustomBean } from "$lib/api/custom_beans.remote";
	import { Button } from "$lib/components/ui/button";
	import { Input } from "$lib/components/ui/input";
	import { Label } from "$lib/components/ui/label";
	import { Textarea } from "$lib/components/ui/textarea";
	import * as Select from "$lib/components/ui/select";
	import { Loader2, Plus, Trash2, Sparkles, Shield, Info, Camera, X } from "lucide-svelte";
	import { toast } from "svelte-sonner";
	import type { CoffeeBean, SmartSearchResult } from "$lib/api";
	import { cn, getFlavourCategoryColors, resizeImage } from "$lib/utils";
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

	// Function to map initialData (from image search or existing) to form defaults
	function getDefaults() {
		return {
			name: initialData?.name || "",
			roaster: initialData?.roaster || "",
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
				process: o.process || "",
				variety: o.variety || "",
			})) || [{ country: "", region: "", producer: "", farm: "", elevation_min: 0, elevation_max: 0, process: "", variety: "" }]
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
				const result = await addCustomBean(form.data);
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
			country: "", region: "", producer: "", farm: "", elevation_min: 0, elevation_max: 0, process: "", variety: ""
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
	let fileInputRef = $state<HTMLInputElement | null>(null);

	async function handleImageUpload(e: Event) {
		const target = e.target as HTMLInputElement;
		const file = target.files?.[0];
		if (!file) return;

		isResizing = true;
		try {
			// Resize to 800x800 max for storage
			const resized = await resizeImage(file, 800, 800);
			const reader = new FileReader();
			reader.onload = (e) => {
				$formData.image_data = e.target?.result as string;
			};
			reader.readAsDataURL(resized);
		} catch (err) {
			console.error("Failed to resize image:", err);
			toast.error("Failed to process image");
		} finally {
			isResizing = false;
			target.value = ""; // Reset input
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
	<div class="flex items-start gap-3 bg-blue-50/50 dark:bg-blue-900/10 p-3 border border-blue-200/50 dark:border-blue-500/20 rounded-lg">
		<Info class="mt-0.5 w-5 h-5 text-blue-500 shrink-0" />
		<div class="space-y-1">
			<p class="font-medium text-blue-900 dark:text-blue-300 text-sm">Personal Bean Entry</p>
			<p class="text-blue-700/80 dark:text-blue-400/80 text-xs leading-relaxed">
				This entry is only visible to <strong>you</strong>.
				Kissaten uses the roaster details to help discover and add new roasters to the public database.
			</p>
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
			<Input id="roaster" bind:value={$formData.roaster} placeholder="e.g. Manhattan Coffee Roasters" />
			{#if $errors.roaster}<p class="text-destructive text-sm">{$errors.roaster}</p>{/if}
		</div>
	</div>

	<div class="space-y-2">
		<Label for="url" class="flex items-center gap-1.5">
			Roaster Website
		</Label>
		<Input id="url" type="url" bind:value={$formData.url} placeholder="e.g. https://manhattancoffeeroasters.com" />
		{#if $errors.url}<p class="text-destructive text-sm">{$errors.url}</p>{/if}
	</div>

	<div class="space-y-2">
		<Label>Bean Image</Label>
		<div class="flex items-center gap-4">
			{#if $formData.image_data}
				<div class="group relative w-24 h-24">
					<img src={$formData.image_data} alt="Bean preview" class="border rounded-lg w-full h-full object-cover" />
					<button
						type="button"
						onclick={removeImage}
						class="top-1 right-1 absolute bg-destructive opacity-0 group-hover:opacity-100 p-1 rounded-full text-destructive-foreground transition-opacity"
					>
						<X class="w-3 h-3" />
					</button>
				</div>
			{:else}
				<button
					type="button"
					onclick={() => fileInputRef?.click()}
					disabled={isResizing}
					class="flex flex-col justify-center items-center gap-2 bg-muted/30 hover:bg-muted/50 border-2 hover:border-primary/50 border-dashed rounded-lg w-24 h-24 text-muted-foreground hover:text-primary transition-all"
				>
					{#if isResizing}
						<Loader2 class="w-6 h-6 animate-spin" />
					{:else}
						<Camera class="w-6 h-6" />
						<span class="text-[10px]">Add Photo</span>
					{/if}
				</button>
			{/if}
			<div class="flex-1 text-muted-foreground text-xs leading-relaxed">
				<p>Upload a photo of the bag or the beans.</p>
			</div>
		</div>
		<input
			type="file"
			bind:this={fileInputRef}
			onchange={handleImageUpload}
			accept="image/*"
			class="hidden"
		/>
	</div>

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
					<div class="space-y-2">
						<Label>Variety</Label>
						<Input bind:value={origin.variety} placeholder="Pink Bourbon" />
					</div>
					<div class="space-y-2">
						<Label>Process</Label>
						<Input bind:value={origin.process} placeholder="Washed" />
					</div>
				</div>
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
			<Label>Price</Label>
			<Input type="number" step="0.01" bind:value={$formData.price} placeholder="0.00" />
		</div>
		<div class="space-y-2">
			<Label>Weight (g)</Label>
			<Input type="number" bind:value={$formData.weight} placeholder="250" />
		</div>
	</div>

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

	<div class="flex justify-end gap-3 bg-background/80 backdrop-blur pt-4 pb-2">
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
</form>
