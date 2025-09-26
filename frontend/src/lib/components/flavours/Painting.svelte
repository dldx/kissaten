<script lang="ts">
  import { T, useTask, useLoader, useThrelte } from '@threlte/core';
  import { Suspense, Text, onReveal } from '@threlte/extras';
  import { onMount } from 'svelte';
  import * as THREE from 'three';
  import Flavour from './Flavour.svelte';
  import { TensorPass, KuwaharaPass, FinalPass } from './PostProcessing';

  let { imageUrl } = $props();

  // Reactive state for controls
  let tensorPassEnabled = $state(false);
  let kuwaharaPassEnabled = $state(true);
  let finalPassEnabled = $state(false);
  let radius = $state(20);
  let renderCount = $state(0);

  // Get Threlte context
  const { scene, camera, renderer, renderStage, autoRender, size } = useThrelte();

  // Load texture
  const watercolorTexture = useLoader(THREE.TextureLoader).load(
    'https://cdn.maximeheckel.com/textures/paper/watercolor.png'
  );

  // Configure texture when it loads
  if ($watercolorTexture) {
    $watercolorTexture.minFilter = THREE.LinearMipmapLinearFilter;
    $watercolorTexture.magFilter = THREE.LinearFilter;
    $watercolorTexture.generateMipmaps = true;
  }

  // Create FBO
  let originalSceneTarget = $state<THREE.WebGLRenderTarget | null>(null);

  // Create postprocessing passes
  let tensorPass: TensorPass | null = null;
  let kuwaharaPass: KuwaharaPass | null = null;
  let finalPass: FinalPass | null = null;

  // Setup effect composer (similar to the Threlte example)
  const setupEffectComposer = () => {
    if (!renderer || !scene || !camera || !$watercolorTexture) return;

    // Create FBO
    const fboWidth = $size.width * Math.min(window.devicePixelRatio, 2);
    const fboHeight = $size.height * Math.min(window.devicePixelRatio, 2);

    if (originalSceneTarget) {
      originalSceneTarget.dispose();
    }

    originalSceneTarget = new THREE.WebGLRenderTarget(fboWidth, fboHeight);

    // Create passes
    tensorPass = new TensorPass();
    kuwaharaPass = new KuwaharaPass({ radius, originalSceneTarget });
    finalPass = new FinalPass({ watercolorTexture: $watercolorTexture });
  };

  // Setup when dependencies are available
  useTask(() => {
    if ($watercolorTexture && $size) {
      setupEffectComposer();
    }
  });

  // Disable auto rendering (following Threlte example)
  onMount(() => {
    const previousAutoRender = autoRender.current;
    autoRender.set(false);
    return () => autoRender.set(previousAutoRender);
  });

  // Custom render pipeline that runs for 5 frames then stops
  const { start, stop } = useTask(
    (delta) => {
      if (!renderer || !scene || !camera || !originalSceneTarget) return;

      // Render original scene to FBO
      renderer.setRenderTarget(originalSceneTarget);
      renderer.render(scene, camera.current);

      // Clear screen and render postprocessed result
      renderer.setRenderTarget(null);
      renderer.clear();

      // Apply postprocessing
      let currentTexture = originalSceneTarget.texture;

      if (tensorPass && tensorPassEnabled) {
        tensorPass.material.uniforms.inputBuffer.value = currentTexture;
        tensorPass.renderToScreen = !kuwaharaPassEnabled && !finalPassEnabled;
        tensorPass.render(renderer, null, { texture: currentTexture });
        currentTexture = tensorPass.material.uniforms.inputBuffer.value;
      }

      if (kuwaharaPass && kuwaharaPassEnabled) {
        kuwaharaPass.material.uniforms.inputBuffer.value = currentTexture;
        kuwaharaPass.material.uniforms.radius.value = radius;
        kuwaharaPass.renderToScreen = !finalPassEnabled;
        kuwaharaPass.render(renderer, null, { texture: currentTexture });
        currentTexture = kuwaharaPass.material.uniforms.inputBuffer.value;
      }

      if (finalPass && finalPassEnabled) {
        finalPass.material.uniforms.inputBuffer.value = currentTexture;
        finalPass.renderToScreen = true;
        finalPass.render(renderer, null, { texture: currentTexture });
      }

      // Show original if no passes enabled
      if (!tensorPassEnabled && !kuwaharaPassEnabled && !finalPassEnabled) {
        renderer.render(scene, camera.current);
      }

      renderCount++;
      if (renderCount >= 5) {
        stop();
      }
    },
    { stage: renderStage, autoInvalidate: true }
  );

  onReveal(() => {
    start();
  });
</script>

<!-- 3D Content -->
<Suspense final>
  {#snippet fallback()}
    <Text
      text="Loading image..."
      fontSize={0.25}
      color="white"
      anchorX="50%"
      anchorY="50%"
      position={[0, 0, 0]}
    />
  {/snippet}

  {#snippet error({ errors })}
    <Text
      text={(errors?.map((e) => e.message ?? String(e)) ?? []).join(', ')}
      fontSize={0.2}
      color="red"
      anchorX="50%"
      anchorY="50%"
      position={[0, 0, 0]}
    />
  {/snippet}

  <T.Group scale={[1, 1, 1]}>
    <Flavour imageUrl={imageUrl} />
  </T.Group>
</Suspense>

<!-- Post-processing effects would need to be implemented differently in Threlte -->
<!-- This is a simplified version - you'd need to create custom post-processing -->
{#if originalSceneTarget && $watercolorTexture}
  <!-- Custom effects implementation would go here -->
  <!-- Threlte doesn't have direct equivalent to R3F's Effects component -->
{/if}

<style>
</style>