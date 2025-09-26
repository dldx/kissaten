<script>
  import { setContext } from 'svelte';

  // Props - children will be passed as snippet
  let { children } = $props();

  // State for image dimensions
  let imageDimensions = $state({ width: 0, height: 0 });

  // Function to update dimensions
  function setImageDimensions(dimensions) {
    imageDimensions = dimensions;
  }

  // Set context that child components can access
  setContext('imageDimensions', {
    imageDimensions: () => imageDimensions,
    setImageDimensions
  });
</script>

{@render children()}