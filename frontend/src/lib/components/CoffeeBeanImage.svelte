<script lang="ts">
	import { api, type CoffeeBean } from "$lib/api";

	interface Props {
		bean: CoffeeBean;
		class?: string;
		size?: "sm" | "md" | "lg" | "xl";
		showFallback?: boolean;
		clickable?: boolean;
		onclick?: () => void;
	}

	let {
		bean,
		class: className = "",
		size = "md",
		showFallback = true,
		clickable = false,
		onclick,
	}: Props = $props();

	// Get image URL
	let imageUrl = $derived((bean as any)?.image_data || bean?.image_url);

	let imageLoaded = $state(false);
	let imageError = $state(false);

	// Size classes
	const sizeClasses = {
		sm: "w-16 h-16",
		md: "w-24 h-24",
		lg: "w-32 h-32",
		xl: "w-48 h-48",
	};
</script>

{#if bean}
	{#if clickable}
		<button
			class={`relative ${sizeClasses[size]} rounded-lg overflow-hidden bg-gray-100 dark:bg-slate-800 cursor-pointer hover:opacity-90 transition-opacity ${className}`}
			style="view-transition-name: {bean.clean_url_slug ? `bean-image-${bean.clean_url_slug}` : 'none'};"
			{onclick}
			type="button"
		>
			<!-- Loading placeholder (behind the image) -->
			{#if imageUrl && !imageLoaded && !imageError}
				<div
					class="z-0 absolute inset-0 flex justify-center items-center bg-gray-200 animate-pulse"
				>
					<div class="text-gray-400 text-xs">Loading...</div>
				</div>
			{/if}

			{#if imageUrl && !imageError}
				<img
					src={imageUrl}
					alt="{bean.name} from {bean.roaster}"
					class="z-10 relative w-full h-full object-cover transition-opacity duration-300"
					onload={() => (imageLoaded = true)}
					onerror={() => (imageError = true)}
				/>
			{/if}

			{#if (!imageUrl || imageError) && showFallback}
				<div
					class="flex justify-center items-center w-full h-full placeholder-bg"
				>
					<img
						src={bean
							? "/static/data/roasters/" +
								bean.bean_url_path?.split("/")[1] +
								"/logo_sticker.png"
							: ""}
						alt="{bean?.roaster} logo"
						class="drop-shadow-xs max-w-[70%] max-h-[70%] object-contain"
					/>
				</div>
			{/if}
		</button>
	{:else}
		<div
			class={`relative ${sizeClasses[size]} rounded-lg overflow-hidden bg-gray-100 dark:bg-slate-800 ${className}`}
			style="view-transition-name: {bean.clean_url_slug ? `bean-image-${bean.clean_url_slug}` : 'none'};"
		>
			<!-- Loading placeholder (behind the image) -->
			{#if imageUrl && !imageLoaded && !imageError}
				<div
					class="z-0 absolute inset-0 flex justify-center items-center bg-gray-200 animate-pulse"
				>
					<div class="text-gray-400 text-xs">Loading...</div>
				</div>
			{/if}

			{#if imageUrl && !imageError}
				<img
					src={imageUrl}
					alt="{bean.name} from {bean.roaster}"
					class="z-10 relative w-full h-full object-cover transition-opacity duration-300"
					onload={() => (imageLoaded = true)}
					onerror={() => (imageError = true)}
				/>
			{/if}

			{#if (!imageUrl || imageError) && showFallback}
				<div
					class="flex justify-center items-center w-full h-full placeholder-bg"
				>
					<img
						src={bean
							? "/static/data/roasters/" +
								bean.bean_url_path?.split("/")[1] +
								"/logo_sticker.png"
							: ""}
						alt="{bean?.roaster} logo"
						class="drop-shadow-xs max-w-[70%] max-h-[70%] object-contain"
					/>
				</div>
			{/if}
		</div>
	{/if}
{/if}
