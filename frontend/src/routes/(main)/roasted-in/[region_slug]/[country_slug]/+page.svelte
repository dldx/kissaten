<script lang="ts">
	import type { PageData } from './$types';
	import LocationLayout from '$lib/components/LocationLayout.svelte';

	let { data }: { data: PageData } = $props();
</script>

<LocationLayout pageContext={data.pageContext} />

<svelte:head>
	<title>{data.country.location_name} - {data.region.location_name} | Kissaten</title>
	<meta name="description" content="Specialty coffee roasters in {data.country.location_name}, {data.region.location_name}" />
</svelte:head>

<!-- Content is now rendered by the layout -->

