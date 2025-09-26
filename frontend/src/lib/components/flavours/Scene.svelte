<script lang="ts">
  import { Canvas, T } from '@threlte/core';
  import { OrbitControls } from '@threlte/extras';
  import { onDestroy } from 'svelte';
  import Painting from './Painting.svelte';
  import CameraController from './CameraController.svelte';
  import CanvasResizer from './CanvasResizer.svelte';
  import ImageDimensionsContext from './ImageDimensionsContext.svelte';

  // Div container size
  let divSize = $state({
    width: 800,
    height: 600
  });

  let textureWidth = $state(100);
  let textureHeight = $state(100);

  // Camera bounds for orthographic camera
  let cameraBounds = $state({
    left: -1,
    right: 1,
    top: 1,
    bottom: -1
  });

  // Calculate camera bounds to fit painting within the div
  function calculateCameraBounds() {
    if (textureWidth <= 0 || textureHeight <= 0 || divSize.width <= 0 || divSize.height <= 0) {
      // Set default bounds if dimensions are invalid
      cameraBounds = {
        left: -1,
        right: 1,
        top: 1,
        bottom: -1
      };
      return;
    }

    const divAspect = divSize.width / divSize.height;
    const textureAspect = textureWidth / textureHeight;

    // Base size for the painting (this should match the scale in Flavour.svelte)
    const baseSize = 3;

    // Calculate the actual sprite scale (matching Flavour.svelte logic)
    let spriteWidth, spriteHeight;
    if (textureAspect > 1) {
      // Landscape: scale by width, height will be smaller
      spriteWidth = baseSize;
      spriteHeight = baseSize / textureAspect;
    } else {
      // Portrait: scale by height, width will be smaller
      spriteWidth = baseSize * textureAspect;
      spriteHeight = baseSize;
    }

    // Now calculate camera bounds to fit the div
    if (textureAspect > divAspect) {
      // Sprite is wider than div - fit to width
      const scale = spriteWidth;
      const height = scale / textureAspect;
      cameraBounds = {
        left: -scale / 2,
        right: scale / 2,
        top: height / 2,
        bottom: -height / 2
      };
    } else {
      // Sprite is taller than div - fit to height
      const scale = spriteHeight;
      const width = scale * textureAspect;
      cameraBounds = {
        left: -width / 2,
        right: width / 2,
        top: scale / 2,
        bottom: -scale / 2
      };
    }
  }

  // Update camera bounds when div or texture size changes
  $effect(() => {
    calculateCameraBounds();
  });

  // Function to update div size (can be called from parent component)
  function updateDivSize(width: number, height: number) {
    divSize = { width, height };
  }

  // Expose the update function for parent components
  export { updateDivSize };

  // Reference to the div element
  let divElement: HTMLDivElement;

  // ResizeObserver to detect div size changes
  let resizeObserver: ResizeObserver | null = null;

  // Setup ResizeObserver when component mounts
  $effect(() => {
    if (divElement && typeof window !== 'undefined') {
      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const { width, height } = entry.contentRect;
          divSize = { width, height };
        }
      });
      resizeObserver.observe(divElement);
    }

    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
    };
  });
</script>

<div
  bind:this={divElement}
  style:width="100vw"
  style:height="100vh"
  style:position="relative"
>
  <!-- <ImageDimensionsContext> -->
    <Canvas
      dpr={2}
      autoRender={false}
    >
        <!-- Lighting -->
        <T.AmbientLight intensity={1.25} />

        <!-- Background -->
        <T.Scene>
          <T.Color attach="background" args={["#5386E0"]} />

          <!-- Main painting component -->
          <Painting bind:textureWidth bind:textureHeight />

          <!-- Camera controller -->

          <!-- Canvas resizer -->
          <!-- <CanvasResizer /> -->

          <!-- Camera -->
          <T.OrthographicCamera
            makeDefault
            position={[0, 0, 10]}
            left={cameraBounds.left}
            right={cameraBounds.right}
            top={cameraBounds.top}
            bottom={cameraBounds.bottom}
            near={0.01}
            far={500}
          >
            <!-- Controls -->
            <OrbitControls />
          <!-- <CameraController /> -->
          </T.OrthographicCamera>
        </T.Scene>
    </Canvas>
  <!-- </ImageDimensionsContext> -->
</div>
