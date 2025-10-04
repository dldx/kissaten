<script>
  import { getContext } from 'svelte';

  const imageDimensionsContext = getContext('imageDimensions');

  // Effect to update canvas size when image dimensions change
  $effect(() => {
    const dimensions = imageDimensionsContext?.imageDimensions();

    if (dimensions && imageDimensionsContext?.setCanvasSize) {
      imageDimensionsContext.setCanvasSize({
        width: dimensions.width,
        height: dimensions.height
      });
    }
  });
</script>

<!-- This component doesn't render anything, it just manages canvas sizing -->