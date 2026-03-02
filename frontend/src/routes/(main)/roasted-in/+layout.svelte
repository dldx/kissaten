<script lang="ts">
	import type { LayoutData } from './$types';

	let { children, data }: { children?: any; data: LayoutData } = $props();
</script>

{@render children?.()}