<script lang="ts">
  import { T, useThrelte } from '@threlte/core';
  import { OrbitControls } from '@threlte/extras';
  import Painting from './Painting.svelte';

  let { imageUrl } = $props();
  const { size } = useThrelte();
</script>

<!-- Lighting -->
<T.AmbientLight intensity={1.25} />

<!-- Background -->
<T.Scene>
  <T.Color attach="background" args={['#5386E0']} />

  <!-- Main painting component -->
  <Painting {imageUrl} />

  <!-- Camera -->
  <T.OrthographicCamera
    makeDefault
    position={[0, 0, 10]}
    left={$size.width / -2}
    right={$size.width / 2}
    top={$size.height / 2}
    bottom={$size.height / -2}
    near={0.01}
    far={500}
  >
    <!-- Controls -->
    <OrbitControls />
  </T.OrthographicCamera>
</T.Scene>
