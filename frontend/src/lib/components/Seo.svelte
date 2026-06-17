<script lang="ts">
	import { page } from '$app/state';
	import { defaultSeo, toAbsoluteUrl, buildTitle, type SeoProps } from '$lib/seo';

	let {
		title,
		description,
		image,
		url,
		type = 'website',
		noindex = false,
		product,
	}: SeoProps = $props();

	const canonicalPath = $derived(page.url.pathname);
	const canonicalUrl = $derived(url ? toAbsoluteUrl(url) : `${defaultSeo.siteUrl}${canonicalPath}`);
	const finalTitle = $derived(buildTitle(title));
	const finalImage = $derived(toAbsoluteUrl(image ?? defaultSeo.defaultImage));
	const finalDescription = $derived(
		(description ?? '').trim() ||
			'Discover extraordinary coffee beans from roasters around the world. Free, open data, updated daily.'
	);
</script>

<svelte:head>
	<title>{finalTitle}</title>
	<meta name="description" content={finalDescription} />
	<link rel="canonical" href={canonicalUrl} />

	{#if noindex}
		<meta name="robots" content="noindex,follow" />
	{:else}
		<meta name="robots" content="index,follow,max-image-preview:large" />
	{/if}

	<meta property="og:site_name" content={defaultSeo.siteName} />
	<meta property="og:title" content={finalTitle} />
	<meta property="og:description" content={finalDescription} />
	<meta property="og:url" content={canonicalUrl} />
	<meta property="og:type" content={type} />
	<meta property="og:image" content={finalImage} />
	<meta property="og:locale" content={defaultSeo.locale} />

	<meta name="twitter:card" content={defaultSeo.twitterCard} />
	<meta name="twitter:title" content={finalTitle} />
	<meta name="twitter:description" content={finalDescription} />
	<meta name="twitter:image" content={finalImage} />
</svelte:head>
