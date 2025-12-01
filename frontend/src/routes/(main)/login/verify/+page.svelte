<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import { Loader2 } from "lucide-svelte";
	import Logo from "$lib/static/logo.svg?raw";
</script>

<div class="flex justify-center items-center px-4 py-8 min-h-[60vh]">
	<Card class="w-full max-w-md">
		<CardHeader class="space-y-4 text-center">
			<div class="flex justify-center">
				<div class="w-12 h-12">
					{@html Logo}
				</div>
			</div>
			<div class="flex justify-center text-primary">
				<Loader2 class="w-12 h-12 animate-spin" />
			</div>
			<CardTitle class="text-xl">Verifying your magic link...</CardTitle>
			<CardDescription>
				Please wait while we sign you in.
			</CardDescription>
		</CardHeader>
		<CardContent class="text-center">
			<p class="text-muted-foreground text-sm">
				This should only take a moment.
			</p>
		</CardContent>
	</Card>
</div>
