<script lang="ts">
	import { Camera, Image as ImageIcon, X, Loader2 } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button";
	import * as Dialog from "$lib/components/ui/dialog";
	import { resizeImage, cn } from "$lib/utils";
	import { onMount } from "svelte";

	interface Props {
		/** Function called when an image is selected and processed */
		onImageSelected: (file: File, base64: string) => void;
		/** Function called when the image is cleared */
		onClear?: () => void;
		/** Initial image preview URL */
		preview?: string | null;
		/** Whether the component is in a loading state */
		loading?: boolean;
		/** Width and height to resize the image to (default: 1000) */
		maxSize?: number;
		/** Custom class for the trigger button */
		class?: string;
		/** Optional ID for the file input */
		id?: string;
		/** Whether to show the clear button (default: true) */
		showClearButton?: boolean;
		/** Label for the trigger (optional) */
		label?: string;
		/** Variant for the trigger button when no image is selected */
		triggerVariant?: "ghost" | "outline" | "secondary" | "default";
	}

	let {
		onImageSelected,
		onClear,
		preview = null,
		loading = false,
		maxSize = 1000,
		class: className = "",
		id = "image-capture-input",
		showClearButton = true,
		label,
		triggerVariant = "ghost"
	}: Props = $props();

	let isMobile = $state(false);
	let showSourceDialog = $state(false);
	let galleryInputRef = $state<HTMLInputElement | null>(null);
	let cameraInputRef = $state<HTMLInputElement | null>(null);

	onMount(() => {
		isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;
	});

	async function handleFile(file: File) {
		try {
			const resized = await resizeImage(file, maxSize, maxSize);
			const reader = new FileReader();
			reader.onload = () => {
				const base64 = reader.result as string;
				onImageSelected(resized, base64);
			};
			reader.readAsDataURL(resized);
		} catch (err) {
			console.error("[ImageCapture] Resize error:", err);
		}
	}

	async function handleInput(e: Event) {
		const target = e.target as HTMLInputElement;
		const file = target.files?.[0];
		if (!file) return;
		await handleFile(file);
		target.value = ""; // Reset
	}

	function handleTrigger() {
		if (isMobile) {
			showSourceDialog = true;
		} else {
			galleryInputRef?.click();
		}
	}

	function handleClear() {
		if (onClear) onClear();
		if (galleryInputRef) galleryInputRef.value = "";
		if (cameraInputRef) cameraInputRef.value = "";
	}
</script>

<div class={cn("inline-block relative", className)}>
	{#if preview}
		<div class="group relative">
			<img src={preview} alt="Selected" class="border rounded-md w-full h-full object-cover" />
			{#if showClearButton}
				<button
					type="button"
					onclick={handleClear}
					class="-top-1 -right-1 absolute bg-destructive opacity-0 group-hover:opacity-100 shadow-sm p-1 rounded-full text-destructive-foreground transition-opacity"
					aria-label="Clear image"
				>
					<X class="w-3 h-3" />
				</button>
			{/if}
		</div>
	{:else}
		<Button
			type="button"
			variant={triggerVariant}
			size="icon"
			onclick={handleTrigger}
			disabled={loading}
			class={cn("w-10 h-10", className)}
			aria-label="Take or upload photo"
		>
			{#if loading}
				<Loader2 class="w-4 h-4 animate-spin" />
			{:else}
				<Camera class="w-4 h-4 text-muted-foreground hover:text-foreground" />
				{#if label}
					<span class="ml-2 text-xs">{label}</span>
				{/if}
			{/if}
		</Button>
	{/if}

	<input
		{id}
		type="file"
		bind:this={galleryInputRef}
		onchange={handleInput}
		accept="image/jpeg,image/png,image/webp,image/avif"
		class="hidden"
	/>
	<input
		type="file"
		bind:this={cameraInputRef}
		onchange={handleInput}
		accept="image/jpeg,image/png,image/webp,image/avif"
		capture="environment"
		class="hidden"
	/>

	<Dialog.Root bind:open={showSourceDialog}>
		<Dialog.Content class="sm:max-w-md">
			<Dialog.Header>
				<Dialog.Title>Choose Image Source</Dialog.Title>
				<Dialog.Description>
					Select how you want to provide the image.
				</Dialog.Description>
			</Dialog.Header>
			<div class="flex flex-col gap-3 py-4">
				<Button
					variant="secondary"
					class="gap-3 w-full h-20 text-lg"
					onclick={() => {
						showSourceDialog = false;
						cameraInputRef?.click();
					}}
				>
					<Camera class="w-6 h-6" />
					Take Photo
				</Button>
				<Button
					variant="secondary"
					class="gap-3 w-full h-20 text-lg"
					onclick={() => {
						showSourceDialog = false;
						galleryInputRef?.click();
					}}
				>
					<ImageIcon class="w-6 h-6" />
					Choose from Gallery
				</Button>
			</div>
		</Dialog.Content>
	</Dialog.Root>
</div>
