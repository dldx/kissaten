<script lang="ts">
  import { useThrelte } from '@threlte/core';
  import { getContext } from 'svelte';
  import * as THREE from 'three';

  const imageDimensionsContext = getContext<{
    imageDimensions: () => { width: number; height: number };
    setImageDimensions: (dimensions: { width: number; height: number }) => void;
  }>('imageDimensions');
  const { camera, size } = useThrelte();

  // Effect to update camera zoom when image dimensions change
  $effect(() => {
    const dimensions = imageDimensionsContext?.imageDimensions();
    const currentSize = $size;

    if (dimensions && $camera && currentSize) {
      // Calculate zoom to fit image perfectly in viewport
      const imageAspectRatio = dimensions.width / dimensions.height;
      const canvasAspectRatio = currentSize.width / currentSize.height;

      // Base zoom factor - adjust this to control the overall size
      const baseZoom = 80;

      // Calculate zoom to fit the image in the viewport while maintaining aspect ratio
      let zoom;
      if (imageAspectRatio > canvasAspectRatio) {
        // Image is wider than canvas - fit to width
        zoom = baseZoom * (canvasAspectRatio / imageAspectRatio);
      } else {
        // Image is taller than canvas - fit to height
        zoom = baseZoom;
      }

      // Ensure minimum zoom for visibility
      zoom = Math.max(zoom, 20);

      // Type assertion to access OrthographicCamera properties
      if ($camera && 'zoom' in $camera) {
        ($camera as THREE.OrthographicCamera).zoom = zoom;
        ($camera as THREE.OrthographicCamera).updateProjectionMatrix();
      }

      console.log('📷 Camera zoom updated:', {
        imageAspectRatio,
        canvasAspectRatio,
        zoom,
        imageDimensions: dimensions,
        canvasSize: currentSize
      });
    }
  });
</script>

<!-- This component doesn't render anything, it just controls the camera -->