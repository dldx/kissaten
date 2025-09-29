<script lang="ts">
  import { Canvas } from '@threlte/core';
  import InnerScene from './InnerScene.svelte';

  let { imageUrl } = $props();
  // Div container size
  let divSize = $state({
    width: 800,
    height: 600
  });

  // Reference to the div element
  let divElement: HTMLDivElement;

  // Setup ResizeObserver when component mounts
  $effect(() => {
    if (divElement && typeof window !== 'undefined') {
      const resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          divSize = { width, height };
        }
      });
      resizeObserver.observe(divElement);
      return () => {
        resizeObserver.disconnect();
      };
    }
  });
</script>

<div
  bind:this={divElement}
  style:width="100vw"
  style:height="100vh"
  style:position="relative"
>
  <Canvas dpr={2} autoRender={false}>
    <InnerScene {imageUrl} />
  </Canvas>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
  }
  :global(canvas) {
    overflow: hidden;
  }
</style>
