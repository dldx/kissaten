<script lang="ts">
  import AdvancedFilterButton from './AdvancedFilterButton.svelte';

	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import * as Dialog from "$lib/components/ui/dialog/index.js";
	import { Sparkles, LoaderCircle, Funnel, X, Camera, Image, CircleAlert, SlidersHorizontal, ThumbsUp, ThumbsDown } from "lucide-svelte";
	import { api } from "$lib/api";
	import { onMount, tick } from "svelte";
	import Dropzone from "svelte-file-dropzone";
	import { fileProxy, superForm } from "sveltekit-superforms";
	import { zodClient } from "sveltekit-superforms/adapters";
	import { z } from "zod";
	import { cn, resizeImage } from "$lib/utils";
	import ImageCapture from "$lib/components/ui/ImageCapture.svelte";
    import type { UserDefaults } from "$lib/types/userDefaults";
	import { smartSearchLoader } from "$lib/stores/smartSearchLoader.svelte";

	interface Props {
		value: string;
		loading?: boolean;
		available?: boolean;
		rateLimited?: boolean;
		rateLimitResetAt?: string | null;
		rateLimitedFilterHref?: string | null;
		placeholder?: string;
		class?: string;
		onSearch: (query: string, userDefaults: UserDefaults) => Promise<string | null>;
		onImageSearch: (image: File, userDefaults: UserDefaults) => Promise<string | null>;
		onToggleFilters?: () => void;
		autofocus?: boolean;
		hasActiveFilters?: boolean;
		showFilterToggleButton?: boolean;
		userDefaults: UserDefaults;
		/** Fingerprint of all active filter values; when it changes after a search the feedback row is hidden. */
		filterKey?: string;
	}

	let {
		value = $bindable(),
		loading = false,
		available = true,
		rateLimited = false,
		rateLimitResetAt = null,
		rateLimitedFilterHref = null,
		placeholder = "Describe the beans you're looking for...", // Random placeholder
		class: className = "",
		onSearch,
		onToggleFilters,
		onImageSearch,
		autofocus = false,
		hasActiveFilters = false,
		showFilterToggleButton = true,
		userDefaults,
		filterKey = undefined,
	}: Props = $props();

	let preview = $state<string | ArrayBuffer | null>("");
	let isDragActive = $state(false);
	let lastQueryHash = $state<string | null>(null);
	let voteCast = $state<'up' | 'down' | null>(null);
	let baseFilterKey = $state<string | null>(null);
	const placeholders = [
		"Find me coffee beans that taste like a pina colada...",
		"Light roast from european roasters with berry notes...",
		"Panama Geisha coffees with funky flavours...",
		"Colombian coffee with citrus flavours above 1800m...",
		"Pink bourbons from uk roasters...",
		"Chocolate coffee that's not bitter...",
	];


	const formSchema = z.object({
		image: z
			.instanceof(File, { message: "Please upload an image" })
			.refine(
				(f) =>
					f.type === "image/jpeg" ||
					f.type === "image/png" ||
					f.type === "image/webp" ||
					f.type === "image/avif",
				"Only jpg, jpeg, png, webp, or avif files are accepted",
			),
	});

	type FormSchema = z.infer<typeof formSchema>;

	const form = superForm(
		{ image: new File([""], "filename") },
		{
			validators: zodClient(formSchema),
			SPA: true,
		},
	);

	const { form: formData, enhance, errors } = form;
	let file = $state(fileProxy(form, "image"));

	async function onDrop(e: {
		detail: { acceptedFiles: File[]; fileRejections: unknown[] };
	}) {
		const { acceptedFiles } = e.detail;
		if (acceptedFiles.length > 0) {
			try {
				const resizedFile = await resizeImage(
					acceptedFiles[0],
					1500,
					1500,
				);
				await onImageSelected(resizedFile, await new Promise(resolve => {
					const reader = new FileReader();
					reader.onload = () => resolve(reader.result as string);
					reader.readAsDataURL(resizedFile);
				}));
			} catch (error) {
				console.error("Image resizing failed:", error);
				preview = null;
				$formData.image = new File([""], "filename");
				await form.validate("image");
			}
		}
	}

	async function onImageSelected(resizedFile: File, base64: string) {
		preview = base64;
		$formData.image = resizedFile;
		value = ""; // Clear text input
		await form.validate("image");
	}

	function clearImage() {
		preview = null;
		$formData.image = new File([""], "filename");
		$errors.image = [];
	}

	async function handleSearch() {
		console.log(userDefaults)
		if (loading || !available) return;

		lastQueryHash = null;
		voteCast = null;
		baseFilterKey = null;
		smartSearchLoader.setLoading(true);
		try {
			if (preview && $formData.image.size > 0) {
				if ($errors.image && $errors.image.length > 0) return;
				lastQueryHash = await onImageSearch($formData.image, userDefaults);
			} else if (value.trim()) {
				lastQueryHash = await onSearch(value, userDefaults);
			}
			if (lastQueryHash) {
				// Let Svelte propagate store updates back to props before snapshotting
				await tick();
				baseFilterKey = filterKey ?? null;
			}
		} finally {
			smartSearchLoader.setLoading(false);
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === "Enter") {
			handleSearch();
		}
	}

	async function submitFeedback(vote: 'up' | 'down') {
		if (!lastQueryHash || voteCast) return;
		voteCast = vote;
		await api.submitSearchFeedback(lastQueryHash, vote);
	}

	function handleCameraButtonClick() {
		if (isMobile) {
			showImageSourceDialog = true;
		} else {
			inputRef?.click();
		}
	}

	function handleCameraChoice() {
		showImageSourceDialog = false;
		cameraInputRef?.click();
	}

	onMount(() => {
		// Change the placeholder every 3 seconds (client-side only)
		const placeholderInterval = setInterval(() => {
			placeholder = placeholders[Math.floor(Math.random() * placeholders.length)];
		}, 3000);

		if (autofocus) {
			// Set autofocus on the input field when component mounts
			const inputElement = document.getElementById("smart-search-input");
			if (inputElement) {
				inputElement.focus();
			}
		}

		// Cleanup interval on component destroy
		return () => {
			clearInterval(placeholderInterval);
		};
	});
</script>

{#if available}
	<div class={`space-y-2 ${className}`}>
		{#if rateLimited}
			{@const hoursLeft = rateLimitResetAt ? Math.ceil((new Date(rateLimitResetAt).getTime() - Date.now()) / 3_600_000) : null}
			<div class="flex flex-wrap items-center gap-2 bg-amber-50 dark:bg-amber-950/30 px-3 py-2 border border-amber-200 dark:border-amber-800 rounded-md text-amber-800 dark:text-amber-300 text-sm">
				<CircleAlert class="w-4 h-4 shrink-0" />
				<span class="flex flex-wrap items-center gap-1">
					<strong>Smart search is overloaded.</strong>
					<span>Falling back to standard keyword search.</span>
					{#if hoursLeft !== null && hoursLeft > 0}
						(Restores in ~{hoursLeft} {hoursLeft === 1 ? 'hour' : 'hours'})
					{/if}
					Try the
				{#if rateLimitedFilterHref}
					<a href={rateLimitedFilterHref} class="inline-flex items-center gap-1 font-medium hover:underline">
						<SlidersHorizontal class="w-3.5 h-3.5" /> Advanced Search
					</a>
				{:else}
					<AdvancedFilterButton onToggleFilters={onToggleFilters} hasActiveFilters={hasActiveFilters} showLabel={true}/>
				{/if}
				</span>
			</div>
		{/if}
		<div class="flex flex-row gap-2 w-full">
			<form class="relative flex-1" method="POST" use:enhance>
				<Dropzone
					on:drop={(e) => {
						onDrop(e);
						isDragActive = false;
					}}
					noClick={true}
					on:dragenter={() => (isDragActive = true)}
					on:dragleave={() => (isDragActive = false)}
					accept={[
						"image/jpeg",
						"image/png",
						"image/webp",
						"image/avif",
					]}
					inputElement={inputRef}
					class={cn(
						"border border-input rounded-md focus-within:ring-2 focus-within:ring-ring ring-offset-background focus-within:ring-offset-2",
						{
							"border-dashed border-primary ring-2 ring-primary ring-offset-2":
								isDragActive,
						},
						{ "border-destructive": $errors.image?.length },
					)}
				>
					<div class="relative flex-1">
						<Sparkles
							class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform"
						/>
						<Input
							id="smart-search-input"
							type="search"
							bind:value
							placeholder={preview
								? "Image selected for search"
								: placeholder}
							class="pl-10 pr-8 border-0 focus-visible:ring-0 focus-visible:ring-offset-0 transition-all duration-300 {preview
								? 'h-24'
								: 'h-10'}"
							onkeypress={handleKeyPress}
							disabled={loading || !!preview}
						/>
						<div class="top-1/2 right-3 absolute -translate-y-1/2">
							<ImageCapture
								onImageSelected={onImageSelected}
								onClear={clearImage}
								preview={preview as string}
								loading={loading}
								showClearButton={true}
								class={preview ? "w-20 h-20" : "w-4 h-4 p-0"}
							/>
						</div>
					</div>
				</Dropzone>
			</form>

		<div class="flex items-center gap-2">
				<Button
					variant="secondary"
					size="default"
					onclick={handleSearch}
					disabled={loading ||
						(!value.trim() && !preview) ||
						($errors.image && $errors.image.length > 0) ||
						rateLimited}
					class={preview
						? "inline-flex h-24 transition-all duration-300"
						: "hidden md:inline-flex"}
				>
					{#if loading && !preview}
						<LoaderCircle class="mr-2 w-3 h-3 animate-spin" />
						Digging deep into the vault...
					{:else if loading && preview}
						<LoaderCircle class="mr-2 w-3 h-3 animate-spin" />
						Analyzing image...
					{:else}
						<Sparkles class="mr-2 w-3 h-3" />
						Find some brews!
					{/if}
				</Button>
				{#if showFilterToggleButton}
					<AdvancedFilterButton onToggleFilters={onToggleFilters} hasActiveFilters={hasActiveFilters} showLabel={false}/>

				{/if}
			</div>
		</div>

		{#if $errors.image?.length}
			<p class="mt-1 text-destructive text-xs">{$errors.image[0]}</p>
		{/if}
		{#if value && !preview}
			<p class="mt-1 text-muted-foreground text-xs">
				Tweak the advanced filters if our smart search doesn't give you
				what you're looking for.
			</p>
		{/if}
	{#if lastQueryHash && !loading && (filterKey === undefined || filterKey === baseFilterKey)}
		<div class="flex items-center gap-2 mt-1 text-muted-foreground text-xs">
			{#if voteCast}
				<span>Thanks for your feedback!</span>
			{:else}
				<span>Was this correct?</span>
				<button
					type="button"
					onclick={() => submitFeedback('up')}
					class="hover:text-green-600 transition-colors"
					aria-label="Thumbs up"
				>
					<ThumbsUp class="inline w-3.5 h-3.5" />
				</button>
				<button
					type="button"
					onclick={() => submitFeedback('down')}
					class="hover:text-red-500 transition-colors"
					aria-label="Thumbs down"
				>
					<ThumbsDown class="inline w-3.5 h-3.5" />
				</button>
			{/if}
		</div>
	{/if}
	</div>
{/if}
