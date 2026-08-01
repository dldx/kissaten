<script lang="ts">
	import { page } from "$app/state";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import ShieldOffIcon from "lucide-svelte/icons/shield-off";
	import ArrowLeftIcon from "lucide-svelte/icons/arrow-left";
	import HomeIcon from "lucide-svelte/icons/home";
	import MailIcon from "lucide-svelte/icons/mail";
</script>

<svelte:head>
	<title>Admin access required | Kissaten</title>
	<meta name="robots" content="noindex,nofollow" />
</svelte:head>

<div class="mx-auto px-4 py-16 container">
	<div class="mx-auto max-w-lg">
		<Card.Root>
			<Card.Content class="pt-10 pb-8">
				<div class="flex flex-col items-center text-center">
					<div
						class="flex justify-center items-center bg-muted mb-5 rounded-full w-16 h-16"
					>
						<ShieldOffIcon class="w-8 h-8 text-muted-foreground" />
					</div>

					<h1 class="font-bold text-2xl">Admin access required</h1>

					<p class="mt-3 text-muted-foreground text-balance">
						{page.error?.message ||
							"This area is only available to site administrators."}
					</p>

					<p class="mt-2 text-muted-foreground text-sm">
						If you think you should have access, please reach out to a
						Kissaten admin and they'll be happy to help.
					</p>

					<div class="flex flex-wrap justify-center gap-3 mt-8 w-full">
						<Button onclick={() => history.back()} variant="outline" class="flex-1 sm:flex-none">
							<ArrowLeftIcon class="mr-2 w-4 h-4" />
							Go back
						</Button>
						<Button href="/" variant="outline" class="flex-1 sm:flex-none">
							<HomeIcon class="mr-2 w-4 h-4" />
							Home
						</Button>
						<Button href="/profile" class="flex-1 sm:flex-none">
							<MailIcon class="mr-2 w-4 h-4" />
							My profile
						</Button>
					</div>
				</div>
			</Card.Content>
		</Card.Root>

		<p class="mt-6 text-muted-foreground text-xs text-center">
			Error code: {page.status}
		</p>
	</div>
</div>
