<script lang="ts">
	import { onMount } from "svelte";
	import { api } from "$lib/api";
	import { populateNoteCategoryMap, noteToCategoryMap } from "$lib/stores/tastingNotesStore.svelte";

	let { children } = $props();

	onMount(async () => {
		// Only fetch if the store is empty (avoids redundant requests when navigating between tasting routes)
		if (Object.keys(noteToCategoryMap).length === 0) {
			try {
				const r = await api.getTastingNoteCategories();
				if (r.success && r.data) populateNoteCategoryMap(r.data);
			} catch {
				// Non-fatal — the hardcoded TASTING_CONVERSATION is the fallback
			}
		}
	});
</script>

{@render children()}
