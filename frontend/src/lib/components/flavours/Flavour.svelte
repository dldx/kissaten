<script lang="ts">
  import { T, useThrelte } from '@threlte/core';
  import { useTexture, useSuspense } from '@threlte/extras';
  import { getContext } from 'svelte';
  import { flavourImageDimensions } from '$lib/stores/flavourImageStore';

  // Props
  let {
    imageUrl = 'https://upload.wikimedia.org/wikipedia/commons/b/be/StarAnise.jpg'
  } = $props();

  // Load texture using Threlte's useTexture and make it suspense-ready
  console.log('🖼️ Loading texture from URL:', imageUrl);
  const suspend = useSuspense();
  const texture = suspend(useTexture(imageUrl));

  const { size } = useThrelte();

  // Calculate scale to cover the viewport while maintaining aspect ratio
  let scale = $derived([1, 1, 1] as [number, number, number]);

  $effect(() => {
    if ($texture?.image && $size.width > 0 && $size.height > 0) {
      const textureWidth = $texture.image.naturalWidth;
      const textureHeight = $texture.image.naturalHeight;
      const textureAspect = textureWidth / textureHeight;
      const viewportAspect = $size.width / $size.height;
      console.log('$texture.image', $texture.image);
      flavourImageDimensions.set({ width: textureWidth, height: textureHeight });

      let newScale: [number, number, number];

      if (textureAspect > viewportAspect) {
        // Texture is wider than viewport, scale to viewport height
        const scaleHeight = $size.height;
        const scaleWidth = scaleHeight * textureAspect;
        newScale = [scaleWidth, scaleHeight, 1];
      } else {
        // Texture is taller or same aspect as viewport, scale to viewport width
        const scaleWidth = $size.width;
        const scaleHeight = scaleWidth / textureAspect;
        newScale = [scaleWidth, scaleHeight, 1];
      }
      scale = newScale;
    }
  });
</script>

<T.Sprite {scale}>
  <T.SpriteMaterial map={$texture} transparent={true} alphaTest={0.1} />
</T.Sprite>