<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { ArrowLeft } from "lucide-svelte";
</script>

<div class="mb-6">
	<Button variant="ghost" onclick={() => history.back()} class="pl-2">
		<ArrowLeft class="mr-2 w-4 h-4" />
		Back
	</Button>
</div>
