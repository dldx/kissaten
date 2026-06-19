<script lang="ts">
	import { api, type CoffeeBean } from "$lib/api";
	import { defaultWidths } from "$lib/utils/cfImage";
	import ResponsiveImage from "./ResponsiveImage.svelte";
	import { Coffee } from "lucide-svelte";

	interface Props {
		bean: CoffeeBean;
		class?: string;
		size?: "sm" | "md" | "lg" | "xl";
		fluid?: boolean;
		sizes?: string;
		showFallback?: boolean;
		clickable?: boolean;
		onclick?: () => void;
	}

	let {
		bean,
		class: className = "",
		size = "md",
		fluid = false,
		sizes,
		showFallback = true,
		clickable = false,
		onclick,
	}: Props = $props();

	let imageUrl = $derived((bean as any)?.image_data || bean?.image_url);

	let imageLoaded = $state(false);
	let imageError = $state(false);

	const sizeClasses = {
		sm: "w-16 h-16",
		md: "w-24 h-24",
		lg: "w-32 h-32",
		xl: "w-48 h-48",
	};

	const sizeToWidth = {
		sm: 64,
		md: 96,
		lg: 128,
		xl: 192,
	};

	// Fallback logo path derived once; empty if we can't construct it
	const fallbackLogoSrc = $derived(
		bean?.bean_url_path
			? `/static/data/roasters/${bean.bean_url_path.split("/")[1]}/logo_sticker.png`
			: "",
	);

	// Fallback sizes for fluid or fixed contexts
	const effectiveSizes = $derived(
		sizes ??
			(fluid
				? "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 400px"
				: `${sizeToWidth[size]}px`),
	);
</script>

{#if bean}
	{#if clickable}
		<button
			class={`relative ${fluid ? "w-full h-full" : sizeClasses[size]} rounded-lg overflow-hidden bg-gray-100 dark:bg-slate-800 cursor-pointer hover:opacity-90 transition-opacity ${className}`}
			style="view-transition-name: {bean.clean_url_slug ? `bean-image-${bean.clean_url_slug}` : 'none'};"
			{onclick}
			type="button"
		>
			{#if imageUrl && !imageLoaded && !imageError}
				<div
					class="z-0 absolute inset-0 flex justify-center items-center bg-gray-200 animate-pulse"
				>
					<div class="text-gray-400 text-xs">Loading...</div>
				</div>
			{/if}

			{#if imageUrl && !imageError}
				{#if fluid}
					<ResponsiveImage
						src={imageUrl}
						alt="{bean.name} from {bean.roaster}"
						widths={defaultWidths.bean}
						sizes={effectiveSizes}
						fit="cover"
						class="z-10 relative w-full h-full object-cover transition-opacity duration-300"
						onload={() => (imageLoaded = true)}
						onerror={() => (imageError = true)}
					/>
				{:else}
					<ResponsiveImage
						src={imageUrl}
						alt="{bean.name} from {bean.roaster}"
						width={sizeToWidth[size]}
						dprs={[1, 2, 3]}
						sizes={effectiveSizes}
						fit="cover"
						class="z-10 relative w-full h-full object-cover transition-opacity duration-300"
						onload={() => (imageLoaded = true)}
						onerror={() => (imageError = true)}
					/>
				{/if}
			{/if}

			{#if (!imageUrl || imageError) && showFallback}
				<div class="flex justify-center items-center w-full h-full placeholder-bg">
					{#if bean.is_custom || bean.bean_url_path?.startsWith('/custom')}
						<div class="flex flex-col justify-center items-center text-muted-foreground/40">
							<Coffee class="w-12 h-12 mb-2" />
							<span class="text-[10px] font-medium uppercase tracking-widest">Custom Bean</span>
						</div>
					{:else}
						{#if fluid}
							<ResponsiveImage
								src={fallbackLogoSrc}
								alt="{bean.roaster} logo"
								widths={defaultWidths.logo}
								sizes={effectiveSizes}
								fit="contain"
								class="drop-shadow-xs max-w-[70%] max-h-[70%] object-contain"
							/>
						{:else}
							<ResponsiveImage
								src={fallbackLogoSrc}
								alt="{bean.roaster} logo"
								width={(size === 'sm' || size === 'md') ? 70 : 134}
								dprs={[1, 2, 3]}
								sizes={effectiveSizes}
								fit="contain"
								class="drop-shadow-xs max-w-[70%] max-h-[70%] object-contain"
							/>
						{/if}
					{/if}
				</div>
			{/if}
		</button>
	{:else}
		<div
			class={`relative ${fluid ? "w-full h-full" : sizeClasses[size]} rounded-lg overflow-hidden bg-gray-100 dark:bg-slate-800 ${className}`}
			style="view-transition-name: {bean.clean_url_slug ? `bean-image-${bean.clean_url_slug}` : 'none'};"
		>
			{#if imageUrl && !imageLoaded && !imageError}
				<div
					class="z-0 absolute inset-0 flex justify-center items-center bg-gray-200 animate-pulse"
				>
					<div class="text-gray-400 text-xs">Loading...</div>
				</div>
			{/if}

			{#if imageUrl && !imageError}
				{#if fluid}
					<ResponsiveImage
						src={imageUrl}
						alt="{bean.name} from {bean.roaster}"
						widths={defaultWidths.bean}
						sizes={effectiveSizes}
						fit="cover"
						class="z-10 relative w-full h-full object-cover transition-opacity duration-300"
						onload={() => (imageLoaded = true)}
						onerror={() => (imageError = true)}
					/>
				{:else}
					<ResponsiveImage
						src={imageUrl}
						alt="{bean.name} from {bean.roaster}"
						width={sizeToWidth[size]}
						dprs={[1, 2, 3]}
						sizes={effectiveSizes}
						fit="cover"
						class="z-10 relative w-full h-full object-cover transition-opacity duration-300"
						onload={() => (imageLoaded = true)}
						onerror={() => (imageError = true)}
					/>
				{/if}
			{/if}

			{#if (!imageUrl || imageError) && showFallback}
				<div class="flex justify-center items-center w-full h-full placeholder-bg">
					{#if bean.is_custom || bean.bean_url_path?.startsWith('/custom')}
						<div class="flex flex-col justify-center items-center text-muted-foreground/40">
							<Coffee class="w-12 h-12 mb-2" />
							<span class="text-[10px] font-medium uppercase tracking-widest">Custom Bean</span>
						</div>
					{:else}
						{#if fluid}
							<ResponsiveImage
								src={fallbackLogoSrc}
								alt="{bean.roaster} logo"
								widths={defaultWidths.logo}
								sizes={effectiveSizes}
								fit="contain"
								class="drop-shadow-xs max-w-[70%] max-h-[70%] object-contain"
							/>
						{:else}
							<ResponsiveImage
								src={fallbackLogoSrc}
								alt="{bean.roaster} logo"
								width={(size === 'sm' || size === 'md') ? 70 : 134}
								dprs={[1, 2, 3]}
								sizes={effectiveSizes}
								fit="contain"
								class="drop-shadow-xs max-w-[70%] max-h-[70%] object-contain"
							/>
						{/if}
					{/if}
				</div>
			{/if}
		</div>
	{/if}
{/if}
