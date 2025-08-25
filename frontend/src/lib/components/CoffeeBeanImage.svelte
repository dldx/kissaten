<script lang="ts">
	import { api, type CoffeeBean } from "$lib/api";

	interface Props {
		bean: CoffeeBean;
		class?: string;
		size?: 'sm' | 'md' | 'lg' | 'xl';
		showFallback?: boolean;
	}

	let {
		bean,
		class: className = "",
		size = 'md',
		showFallback = true
	}: Props = $props();

	// Get image URL
	const imageUrl = bean.image_url ?? null;

	// Placeholder image
	const placeholderImage = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200' viewBox='0 0 200 200'%3E%3Crect width='200' height='200' fill='%23f3f4f6'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='0.35em' fill='%23666' font-family='sans-serif' font-size='14'%3ENo Image%3C/text%3E%3C/svg%3E";

	let imageLoaded = $state(false);
	let imageError = $state(false);

	// Size classes
	const sizeClasses = {
		sm: 'w-16 h-16',
		md: 'w-24 h-24',
		lg: 'w-32 h-32',
		xl: 'w-48 h-48'
	};
</script>

<div class={`relative ${sizeClasses[size]} rounded-lg overflow-hidden bg-gray-100 ${className}`}>
	{#if imageUrl && !imageError}
		<img
			src={imageUrl}
			alt="{bean.name} from {bean.roaster}"
			class="w-full h-full object-cover transition-opacity duration-300"
			class:opacity-0={!imageLoaded}
			class:opacity-100={imageLoaded}
			onload={() => (imageLoaded = true)}
			onerror={() => (imageError = true)}
		/>
	{/if}

	{#if (!imageUrl || imageError) && showFallback}
		<img
			src={placeholderImage}
			alt="No image available for {bean.name}"
			class="opacity-50 w-full h-full object-cover"
		/>
	{/if}

	<!-- Loading placeholder -->
	{#if imageUrl && !imageLoaded && !imageError}
		<div class="absolute inset-0 flex justify-center items-center bg-gray-200 animate-pulse">
			<div class="text-gray-400 text-xs">Loading...</div>
		</div>
	{/if}
</div>
