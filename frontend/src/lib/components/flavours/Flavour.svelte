<script lang="ts">
  import { T, useLoader } from '@threlte/core';
  import * as THREE from 'three';
  import { getContext } from 'svelte';

  // Props
  let {
    imageUrl = "https://upload.wikimedia.org/wikipedia/commons/b/be/StarAnise.jpg",
    textureWidth = $bindable(),
    textureHeight = $bindable()
  } = $props();

  // Get image dimensions context
  const imageDimensionsContext = getContext<{
    imageDimensions: () => { width: number; height: number };
    setImageDimensions: (dimensions: { width: number; height: number }) => void;
  }>('imageDimensions');

  // Load texture using Threlte's useLoader
  console.log('🖼️ Loading texture from URL:', imageUrl);
  const texture = useLoader(THREE.TextureLoader).load(imageUrl);

  // Calculate scale based on image dimensions to maintain aspect ratio
  let scale = $state([1, 1, 1] as [number, number, number]);
  let dimensionsSet = $state(false);

  // Function to calculate and set scale based on dimensions
  function calculateScale(width: number, height: number) {
    if (width <= 0 || height <= 0) return;

    const aspectRatio = width / height;
    const baseSize = 3;

    if (aspectRatio > 1) {
      // Landscape: scale by width, height will be smaller
      scale = [baseSize, baseSize / aspectRatio, 1];
    } else {
      // Portrait: scale by height, width will be smaller
      scale = [baseSize * aspectRatio, baseSize, 1];
    }

    console.log('📐 Calculated scale for aspect ratio:', aspectRatio, 'scale:', scale);
  }

  // Set dimensions once when texture loads
  $effect(() => {
    if ($texture && !dimensionsSet) {
      // Get texture dimensions
      textureWidth = $texture.image?.width || $texture.image?.naturalWidth || 0;
      textureHeight = $texture.image?.height || $texture.image?.naturalHeight || 0;

      if (textureWidth > 0 && textureHeight > 0) {
        // Calculate scale from texture dimensions
        calculateScale(textureWidth, textureHeight);

        // Update context with dimensions
        if (imageDimensionsContext?.setImageDimensions) {
          imageDimensionsContext.setImageDimensions({
            width: textureWidth,
            height: textureHeight
          });
        }

        dimensionsSet = true;
        console.log('📐 Set dimensions once from texture:', { width: textureWidth, height: textureHeight });
      }
    }
  });
</script>

<T.Sprite scale={scale}>
  <T.SpriteMaterial
    map={$texture}
    transparent={true}
    alphaTest={0.1}
  />
</T.Sprite>