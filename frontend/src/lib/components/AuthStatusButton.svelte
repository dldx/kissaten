<script lang="ts">
	import { Vault, RefreshCw, Coffee, Settings, FlaskConical, LogOut, User, RotateCcw } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Popover from "$lib/components/ui/popover/index.js";
	import { authClient } from "$lib/auth-client";
	import { page } from "$app/state";
	import { goto, invalidateAll } from "$app/navigation";
	import { toast } from "svelte-sonner";
	import { userSettings } from "$lib/stores/userSettings.svelte";
	import { setCurrentOwnerId } from "$lib/db/localdb";
	import { runGlobalSync, syncState } from "$lib/sync/syncManager.svelte";
	import { cn } from "$lib/utils";
	import { untrack } from "svelte";

	const authenticatedPaths = ["/vault", "/profile"];

	const session = authClient.useSession();

	let popoverOpen = $state(false);

	// Plain `let` (NOT $state) — writing inside the effect must not retrigger it.
	// We only want to react to changes in $session.data, not to our own bookkeeping.
	// `undefined` is a sentinel meaning "haven't observed yet", so we don't fire on
	// the initial mount when a user is already signed in (e.g. hard refresh).
	let prevSessionUserId: string | null | undefined = undefined;
	let firedForUserId: string | null = null;

	// When the session atom transitions from a confirmed signed-out state (null)
	// to a signed-in user, fire a verify-then-fix sync so guest data is correctly
	// claimed and any drift is repaired. The cache is invalidated separately by the
	// sign-in flow (e.g. `check-email/+page.svelte` does `await invalidateAll()` for
	// the OTP path; the magic-link path is a full navigation so the cache is empty).
	$effect(() => {
		const currentUserId = $session.data?.user.id ?? null;

		const shouldFire = untrack(() => {
			if (
				prevSessionUserId !== undefined &&
				prevSessionUserId === null &&
				currentUserId &&
				currentUserId !== firedForUserId
			) {
				firedForUserId = currentUserId;
				return true;
			}
			prevSessionUserId = currentUserId;
			if (!currentUserId) {
				// Reset on sign-out so a fresh sign-in (possibly the same user)
				// triggers the sync again.
				firedForUserId = null;
			}
			return false;
		});

		if (shouldFire) {
			console.log("[auth] Sign-in detected, running verify-then-fix sync.");
			void runGlobalSync({ mode: "verify-then-fix", silent: true });
		}
	});

	async function handleSignOut() {
		popoverOpen = false;
		await authClient.signOut({
			fetchOptions: {
				onSuccess: async () => {
					// Clear user context so next login doesn't see stale data
					setCurrentOwnerId(null);
					// Invalidate SvelteKit remote-function cache so the cached
					// `getUserWithoutRedirect` value doesn't briefly leak the
					// just-signed-out user into a sync call.
					await invalidateAll();
					if (authenticatedPaths.includes(page.url.pathname)) {
						goto("/");
					}
					toast.success("You have been signed out. Happy brewing!");
				},
			},
		});
	}

	function closePopover() {
		popoverOpen = false;
	}

	function handleForceFullSync() {
		popoverOpen = false;
		void runGlobalSync({ mode: "force-full", silent: false });
	}
</script>

{#if $session.data}
	<Popover.Root bind:open={popoverOpen}>
		<Popover.Trigger
			class="inline-flex justify-center items-center bg-background hover:bg-accent disabled:opacity-50 shadow-sm border border-input rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring ring-offset-background w-9 h-9 font-medium text-sm whitespace-nowrap transition-colors hover:text-accent-foreground disabled:pointer-events-none"
		>
			<User class="w-[1.2rem] h-[1.2rem]" />
			<span class="sr-only">User menu</span>
		</Popover.Trigger>
		<Popover.Content class="w-64">
			<div class="flex flex-col gap-3">
				<div class="flex justify-between items-center gap-1 px-2">
					<div class="space-y-1">
						<p class="font-medium text-sm">Signed in as</p>
						<p class="text-muted-foreground text-sm truncate">
							{$session.data.user.name != ""
								? $session.data.user.name
								: $session.data.user.email}
						</p>
					</div>
					<!-- Sync Button -->
					<Button
						onclick={() => runGlobalSync({ silent: false })}
						variant="outline"
						size="icon"
						disabled={syncState.isSyncing}
						title="Synchronize coffee data"
					>
						<RefreshCw
							class={cn(
								"w-[1.2rem] h-[1.2rem] transition-all",
								syncState.isSyncing && "animate-spin",
							)}
						/>
						<span class="sr-only">Sync data</span>
					</Button>
				</div>
				<div class="flex flex-col gap-2">
					<Button
						href="/vault"
						onclick={closePopover}
						variant="outline"
						class="justify-start w-full"
					>
						<Vault class="mr-2 w-4 h-4" />
						My Coffee Vault
					</Button>
					{#if userSettings.betaEnabled}
						<Button
							href="/tasting"
							onclick={closePopover}
							variant="outline"
							class="justify-start w-full"
						>
							<Coffee class="mr-2 w-4 h-4" />
							New Tasting
						</Button>
						<Button
							href="/brew-assistant"
							onclick={closePopover}
							variant="outline"
							class="justify-start w-full"
						>
							<FlaskConical class="mr-2 w-4 h-4" />
							Brew Assistant
						</Button>
					{/if}
					<Button
						href="/profile"
						onclick={closePopover}
						variant="outline"
						class="justify-start w-full"
					>
						<Settings class="mr-2 w-4 h-4" />
						Profile
					</Button>
					<Button
						onclick={handleForceFullSync}
						variant="outline"
						class="justify-start w-full"
						title="Re-fetch every record from the server and repair any drift"
					>
						<RotateCcw class="mr-2 w-4 h-4" />
						Force full sync
					</Button>
					<Button
						onclick={handleSignOut}
						variant="outline"
						class="justify-start w-full"
					>
						<LogOut class="mr-2 w-4 h-4" />
						Sign Out
					</Button>
				</div>
			</div>
		</Popover.Content>
	</Popover.Root>
{:else}
	<Button href="/login" variant="outline" size="icon">
		<User class="w-[1.2rem] h-[1.2rem]" />
		<span class="sr-only">Sign in</span>
	</Button>
{/if}
