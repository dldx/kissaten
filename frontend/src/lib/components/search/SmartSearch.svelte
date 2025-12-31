<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import * as Dialog from "$lib/components/ui/dialog/index.js";
	import { Sparkles, Loader2, Filter, X, Camera, Image } from "lucide-svelte";
	import { onMount } from "svelte";
	import Dropzone from "svelte-file-dropzone";
	import { fileProxy, superForm } from "sveltekit-superforms";
	import { zodClient } from "sveltekit-superforms/adapters";
	import { z } from "zod";
	import { cn } from "$lib/utils";
    import type { UserDefaults } from "$lib/types/userDefaults";
	import { smartSearchLoader } from "$lib/stores/smartSearchLoader.svelte";

	function resizeImage(
		file: File,
		maxWidth: number,
		maxHeight: number,
	): Promise<File> {
		return new Promise((resolve, reject) => {
			const img = document.createElement("img");
			img.src = URL.createObjectURL(file);
			img.onload = () => {
				const canvas = document.createElement("canvas");
				const ctx = canvas.getContext("2d");
				if (!ctx) {
					return reject(new Error("Could not get canvas context"));
				}

				let { width, height } = img;
				const ratio = Math.min(maxWidth / width, maxHeight / height);

				if (ratio < 1) {
					// only resize if image is larger than max dimensions
					width *= ratio;
					height *= ratio;
				}

				canvas.width = width;
				canvas.height = height;

				ctx.drawImage(img, 0, 0, width, height);

				canvas.toBlob(
					(blob) => {
						if (!blob) {
							return reject(
								new Error("Canvas to Blob conversion failed"),
							);
						}
						const resizedFile = new File([blob], file.name, {
							type: "image/jpeg",
							lastModified: Date.now(),
						});
						resolve(resizedFile);
					},
					"image/jpeg",
					0.9, // quality
				);
			};
			img.onerror = () => {
				reject(new Error("Image load error"));
			};
		});
	}

	interface Props {
		value: string;
		loading?: boolean;
		available?: boolean;
		placeholder?: string;
		class?: string;
		onSearch: (query: string, userDefaults: UserDefaults) => void | Promise<void>;
		onImageSearch: (image: File, userDefaults: UserDefaults) => void | Promise<void>;
		onToggleFilters?: () => void;
		autofocus?: boolean;
		hasActiveFilters?: boolean;
		showFilterToggleButton?: boolean;
		userDefaults: UserDefaults;
	}

	let {
		value = $bindable(),
		loading = false,
		available = true,
		placeholder = "Describe the beans you're looking for...", // Random placeholder
		class: className = "",
		onSearch,
		onToggleFilters,
		onImageSearch,
		autofocus = false,
		hasActiveFilters = false,
		showFilterToggleButton = true,
		userDefaults,
	}: Props = $props();

	let preview = $state<string | ArrayBuffer | null>("");
	let inputRef = $state<HTMLInputElement | null>(null);
	let cameraInputRef = $state<HTMLInputElement | null>(null);
	let isDragActive = $state(false);
	let showImageSourceDialog = $state(false);
	let isMobile = $state(false);
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
				const reader = new FileReader();
				reader.onload = () => (preview = reader.result);
				reader.readAsDataURL(resizedFile);
				$formData.image = resizedFile;
				value = ""; // Clear text input
			} catch (error) {
				console.error("Image resizing failed:", error);
				preview = null;
				$formData.image = new File([""], "filename");
			}
		}
		await form.validate("image");
	}

	async function handleImageSearch(
		e: Event & { currentTarget: EventTarget & HTMLInputElement },
	) {
		const acceptedFile = e.currentTarget.files?.[0];

		if (!acceptedFile) {
			preview = null;
			$formData.image = new File([""], "filename");
			await form.validate("image");
			return;
		}

		try {
			const resizedFile = await resizeImage(acceptedFile, 1000, 1000);
			const reader = new FileReader();
			reader.onload = () => (preview = reader.result);
			reader.readAsDataURL(resizedFile);
			$formData.image = resizedFile;
			value = ""; // Clear text input
		} catch (error) {
			console.error("Image resizing failed:", error);
			preview = null;
			$formData.image = new File([""], "filename");
		}
		await form.validate("image");
	}

	function clearImage() {
		preview = null;
		$formData.image = new File([""], "filename");
		if (inputRef) {
			inputRef.value = "";
		}
		$errors.image = [];
	}

	async function handleSearch() {
		console.log(userDefaults)
		if (loading || !available) return;

		smartSearchLoader.setLoading(true);
		try {
			if (preview && $formData.image.size > 0) {
				if ($errors.image && $errors.image.length > 0) return;
				await onImageSearch($formData.image, userDefaults);
			} else if (value.trim()) {
				await onSearch(value, userDefaults);
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

	// Change the placeholder every 5 seconds
	setInterval(() => {
		placeholder =
			placeholders[Math.floor(Math.random() * placeholders.length)];
	}, 3000);

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

	function handleGalleryChoice() {
		showImageSourceDialog = false;
		inputRef?.click();
	}

	onMount(() => {
		// Detect if device is mobile
		isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;

		if (!autofocus) return;
		// Set autofocus on the input field when component mounts
		const inputElement = document.getElementById("smart-search-input");
		if (inputElement) {
			inputElement.focus();
		}
	});
</script>

{#if available}
	<div class={`space-y-2 ${className}`}>
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
						{#if preview}
							<div
								class="top-1/2 right-2 absolute flex items-center gap-2 bg-muted p-1 rounded-md -translate-y-1/2"
							>
								<img
									src={preview as string}
									alt="Preview of selected"
									class="rounded w-20 h-20 object-cover"
								/>
								<button
									type="button"
									onclick={clearImage}
									class="bg-muted-foreground/20 hover:bg-muted-foreground/40 p-0.5 rounded-full text-secondary-foreground"
								>
									<X class="w-3 h-3" />
								</button>
							</div>
						{:else}
							<button
								type="button"
								onclick={handleCameraButtonClick}
								class="top-1/2 right-3 absolute -translate-y-1/2"
								aria-label="Select an image"
							>
								<Camera
									class="w-4 h-4 text-muted-foreground hover:text-foreground"
								/>
							</button>
						{/if}
					</div>
				</Dropzone>
			</form>
		<!-- File input for gallery/normal picker -->
		<input
			type="file"
			bind:this={inputRef}
			oninput={handleImageSearch}
			class="hidden"
			name="image"
			accept="image/jpeg,image/png,image/webp,image/avif"
		/>
		<!-- File input for camera -->
		<input
			type="file"
			bind:this={cameraInputRef}
			oninput={handleImageSearch}
			class="hidden"
			name="camera-image"
			accept="image/jpeg,image/png,image/webp,image/avif"
			capture="environment"
		/>

		<div class="flex items-center gap-2">
				<Button
					variant="secondary"
					size="default"
					onclick={handleSearch}
					disabled={loading ||
						(!value.trim() && !preview) ||
						($errors.image && $errors.image.length > 0)}
					class={preview
						? "inline-flex h-24 transition-all duration-300"
						: "hidden md:inline-flex"}
				>
					{#if loading && !preview}
						<Loader2 class="mr-2 w-3 h-3 animate-spin" />
						Digging deep into the vault...
					{:else if loading && preview}
						<Loader2 class="mr-2 w-3 h-3 animate-spin" />
						Analyzing image...
					{:else}
						<Sparkles class="mr-2 w-3 h-3" />
						Find some brews!
					{/if}
				</Button>
				{#if showFilterToggleButton}
				<Button
					variant="ghost"
					size="default"
					onclick={onToggleFilters}
					class="relative px-3 {hasActiveFilters
						? 'ring-2 ring-orange-500 dark:ring-emerald-500/50'
						: ''}"
					title="Toggle advanced filters panel"
					aria-label="Toggle advanced filters"
				>
					<Filter
						class="w-4 h-4 {hasActiveFilters
							? 'text-orange-600 dark:text-emerald-400'
							: ''}"
					/>
					{#if hasActiveFilters}
						<div
							class="top-0 right-0 absolute bg-orange-500 dark:bg-emerald-500 rounded-full w-2 h-2 -translate-y-1 translate-x-1 transform"
						></div>
						{/if}
					</Button>
				{/if}
			</div>
		</div>

		<!-- Image Source Dialog (Mobile) -->
		<Dialog.Root bind:open={showImageSourceDialog}>
			<Dialog.Content class="sm:max-w-md">
				<Dialog.Header>
					<Dialog.Title>Choose Image Source</Dialog.Title>
					<Dialog.Description>
						Select where you'd like to get your image from
					</Dialog.Description>
				</Dialog.Header>
				<div class="flex flex-col gap-3 py-4">
					<Button
						onclick={handleCameraChoice}
						variant="default"
						class="w-full h-20 text-lg"
					>
						<Camera class="mr-2 w-6 h-6" />
						Take Photo
					</Button>
					<Button
						onclick={handleGalleryChoice}
						variant="secondary"
						class="w-full h-20 text-lg"
					>
						<Image class="mr-2 w-6 h-6" />
						Choose from Gallery
					</Button>
				</div>
			</Dialog.Content>
		</Dialog.Root>

		{#if $errors.image?.length}
			<p class="mt-1 text-destructive text-xs">{$errors.image[0]}</p>
		{/if}
		{#if value && !preview}
			<p class="mt-1 text-muted-foreground text-xs">
				Tweak the advanced filters if our smart search doesn't give you
				what you're looking for.
			</p>
		{/if}
	</div>
{/if}
