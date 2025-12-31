<script lang="ts">
	import { api, type CoffeeBean } from "$lib/api";

	interface Props {
		bean: CoffeeBean;
		class?: string;
		size?: "sm" | "md" | "lg" | "xl";
		showFallback?: boolean;
	}

	let {
		bean,
		class: className = "",
		size = "md",
		showFallback = true,
	}: Props = $props();

	// Get image URL
	let imageUrl = $derived(bean?.image_url);

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
	<div
		class={`relative ${sizeClasses[size]} rounded-lg overflow-hidden bg-gray-100 ${className}`}
		style="view-transition-name: bean-image-{bean.clean_url_slug};"
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
				class={(size == "sm" ? "" : " min-h-48 ") +
					"items-center flex justify-center h-full placeholder-bg"}
			>
				<img
					src={bean
						? "/static/data/roasters/" +
							bean.bean_url_path?.split("/")[1] +
							"/logo.png"
						: ""}
					alt="{bean?.roaster} logo"
					class="w-fit h-fit"
				/>
			</div>
		{/if}
	</div>
{/if}
