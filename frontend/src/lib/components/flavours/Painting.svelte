<script lang="ts">
  import { T, useTask, useLoader, useThrelte } from '@threlte/core';
  import { onMount } from 'svelte';
  import * as THREE from 'three';
  import Flavour from './Flavour.svelte';
  import { TensorPass, KuwaharaPass, FinalPass } from './PostProcessing';

  let { textureWidth = $bindable(), textureHeight = $bindable() } = $props();

  // Reactive state for controls
  let tensorPassEnabled = $state(false);
  let kuwaharaPassEnabled = $state(true);
  let finalPassEnabled = $state(false);
  let radius = $state(6);

  // Get Threlte context
  const { scene, camera, renderer, renderStage, autoRender, size } = useThrelte();

  // Load texture
  const watercolorTexture = useLoader(THREE.TextureLoader).load("https://cdn.maximeheckel.com/textures/paper/watercolor.png");

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

  // Custom render pipeline (simplified like the Threlte example)
  useTask(
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
    },
    { stage: renderStage, autoInvalidate: false }
  );
</script>


<!-- 3D Content -->
<T.Group scale={[1, 1, 1]}>
  <Flavour bind:textureWidth bind:textureHeight />
</T.Group>

<!-- Post-processing effects would need to be implemented differently in Threlte -->
<!-- This is a simplified version - you'd need to create custom post-processing -->
{#if originalSceneTarget && $watercolorTexture}
  <!-- Custom effects implementation would go here -->
  <!-- Threlte doesn't have direct equivalent to R3F's Effects component -->
{/if}

<style>
  .controls {
    position: fixed;
    top: 20px;
    right: 20px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 20px;
    border-radius: 8px;
    z-index: 1000;
    max-width: 250px;
  }

  .control-group {
    margin-bottom: 15px;
  }

  .control-group h3 {
    margin: 0 0 10px 0;
    font-size: 14px;
    font-weight: bold;
  }

  .control-group label {
    display: block;
    margin-bottom: 5px;
    font-size: 12px;
    cursor: pointer;
  }

  .control-group input[type="checkbox"] {
    margin-right: 8px;
  }

  .control-group input[type="range"] {
    width: 100%;
    margin-top: 5px;
  }
</style>