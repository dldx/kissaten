<script lang="ts">
	import UserIcon from "lucide-svelte/icons/user";
	import LogOutIcon from "lucide-svelte/icons/log-out";
	import VaultIcon from "lucide-svelte/icons/vault";
	import SettingsIcon from "lucide-svelte/icons/settings";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Popover from "$lib/components/ui/popover/index.js";
	import { authClient } from "$lib/auth-client";
	import { page } from "$app/state";
	import { goto } from "$app/navigation";
	import { toast } from "svelte-sonner";

	const session = authClient.useSession();

	async function handleSignOut() {
		await authClient.signOut({
			fetchOptions: {
				onSuccess: () => {
					if (page.url.pathname === "/vault") {
						goto("/");
					}
					toast.success("You have been signed out. Happy brewing!");
				},
			},
		});
	}
</script>

{#if $session.data}
	<Popover.Root>
		<Popover.Trigger
			class="inline-flex justify-center items-center bg-background hover:bg-accent disabled:opacity-50 shadow-sm border border-input rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring ring-offset-background w-9 h-9 font-medium text-sm whitespace-nowrap transition-colors hover:text-accent-foreground disabled:pointer-events-none"
		>
			<UserIcon class="w-[1.2rem] h-[1.2rem]" />
			<span class="sr-only">User menu</span>
		</Popover.Trigger>
		<Popover.Content class="w-64">
			<div class="flex flex-col gap-3">
				<div class="space-y-1">
					<p class="font-medium text-sm">Signed in as</p>
					<p class="text-muted-foreground text-sm truncate">
						{$session.data.user.name != ""
							? $session.data.user.name
							: $session.data.user.email}
					</p>
				</div>
				<div class="flex flex-col gap-2">
					<Button
						href="/vault"
						variant="outline"
						class="justify-start w-full"
					>
						<VaultIcon class="mr-2 w-4 h-4" />
						My Coffee Vault
					</Button>
					<Button
						href="/profile"
						variant="outline"
						class="justify-start w-full"
					>
						<SettingsIcon class="mr-2 w-4 h-4" />
						Profile
					</Button>
					<Button
						onclick={handleSignOut}
						variant="outline"
						class="justify-start w-full"
					>
						<LogOutIcon class="mr-2 w-4 h-4" />
						Sign Out
					</Button>
				</div>
			</div>
		</Popover.Content>
	</Popover.Root>
{:else}
	<Button href="/login" variant="outline" size="icon">
		<UserIcon class="w-[1.2rem] h-[1.2rem]" />
		<span class="sr-only">Sign in</span>
	</Button>
{/if}
