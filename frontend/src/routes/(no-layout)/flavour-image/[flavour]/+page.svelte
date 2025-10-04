<script lang="ts">
import Scene from '$lib/components/flavours/Scene.svelte';
import { flavourImageDimensions } from '$lib/stores/flavourImageStore';

// get params from url
let { data } = $props();

let sizeKey = $state(0);

</script>
<svelte:window on:resize={() => sizeKey = window.innerWidth * window.innerHeight} />
{#key sizeKey + $flavourImageDimensions.width}
<Scene imageUrl={data.imageUrl} />
{/key}

<style>
    :global(body) {
        background-color: black;
    }
</style>