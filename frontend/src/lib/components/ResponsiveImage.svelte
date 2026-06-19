<script lang="ts">
	import { buildCfSrcset, defaultWidths, type FitMode } from '$lib/utils/cfImage';

	interface Props {
		src: string;
		alt: string;
		widths?: readonly number[];
		dprs?: readonly number[];
		width?: number;
		sizes?: string;
		fit?: FitMode;
		quality?: number;
		class?: string;
		style?: string;
		loading?: "lazy" | "eager";
		decoding?: "async" | "sync" | "auto";
		fetchpriority?: "high" | "low" | "auto";
		onerror?: (e: Event) => void;
		onload?: (e: Event) => void;
	}

	let {
		src,
		alt,
		widths,
		dprs,
		width,
		sizes = "100vw",
		fit = "cover",
		quality = 90,
		class: className = "",
		style = "",
		loading = "lazy",
		decoding = "async",
		fetchpriority = "auto",
		onerror,
		onload,
	}: Props = $props();

	// Default to bean preset if no widths/dprs provided
	const effectiveWidths = $derived(!widths && !dprs ? defaultWidths.bean : widths);

	const { primarySrc, srcset } = $derived(
		buildCfSrcset(src, { widths: effectiveWidths, dprs, width, fit, quality }),
	);
</script>

<img
	src={primarySrc}
	srcset={srcset || undefined}
	{sizes}
	{alt}
	{loading}
	{decoding}
	fetchpriority={fetchpriority}
	class={className}
	{style}
	{onerror}
	{onload}
/>
