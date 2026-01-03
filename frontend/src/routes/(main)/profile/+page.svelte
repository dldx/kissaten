<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
    import * as Form from "$lib/components/ui/form/index.js";
	import { Switch } from "$lib/components/ui/switch/index.js";
	import UserIcon from "lucide-svelte/icons/user";
	import MailIcon from "lucide-svelte/icons/mail";
	import BellIcon from "lucide-svelte/icons/bell";
	import MapPinIcon from "lucide-svelte/icons/map-pin";
	import CircleCheck from "lucide-svelte/icons/circle-check";
	import CircleAlert from "lucide-svelte/icons/circle-alert";
	import { getProfile, updateProfile } from "$lib/api/profile.remote";
	import Svelecte from 'svelecte';

	let { data } = $props();

	let successMessage = $state<string | null>(null);
	let profileData = $state(getProfile());
	let newsletterSubscribed = $state(true);
	let defaultRoasterLocations = $state<string[]>([]);

	$effect(() => {
		profileData.then(profile => {
			newsletterSubscribed = profile.newsletterSubscribed ?? true;
			// Parse comma-separated location codes into array
			if (profile.defaultRoasterLocations) {
				defaultRoasterLocations = profile.defaultRoasterLocations.split(',').filter(Boolean);
			} else {
				defaultRoasterLocations = [];
			}
		});
	});

	$effect(() => {
		if (updateProfile.result?.success) {
			successMessage = "Your profile has been updated successfully.";
			newsletterSubscribed = updateProfile.result.newsletterSubscribed;
			// Refresh profile data
			profileData = getProfile();
		}
	});

</script>

<svelte:head>
	<title>Profile Settings - Kissaten</title>
</svelte:head>

<div class="py-8 container">
	<div class="mx-auto max-w-2xl">
		<Card.Root>
			<Card.Header>
				<Card.Title class="font-bold text-3xl">Profile Settings</Card.Title>
				<Card.Description>
					Update your personal details and preferences
				</Card.Description>
			</Card.Header>
			<Card.Content class="space-y-6">
				<!-- Success Message -->
				{#if successMessage}
					<div class="flex items-start gap-3 bg-green-50 dark:bg-green-950/20 px-4 py-3 border border-green-200 dark:border-green-900 rounded-md text-green-800 dark:text-green-200">
						<CircleCheck class="mt-0.5 w-5 h-5 shrink-0" />
						<div>
							<p class="font-medium">Profile updated!</p>
							<p class="mt-1 text-sm">{successMessage}</p>
						</div>
					</div>
				{/if}

				<!-- Error Messages -->
				{#each updateProfile.fields.allIssues() as issue}
					<div class="flex items-start gap-3 bg-red-50 dark:bg-red-950/20 px-4 py-3 border border-red-200 dark:border-red-900 rounded-md text-red-800 dark:text-red-200">
						<CircleAlert class="mt-0.5 w-5 h-5 shrink-0" />
						<div>
							<p class="font-medium">Error</p>
							<p class="mt-1 text-sm">{issue.message}</p>
						</div>
					</div>
				{/each}

				<!-- Profile Form -->
				{#await profileData}
					<div class="py-8 text-muted-foreground text-center">Loading profile...</div>
				{:then profile}
					<form {...updateProfile.enhance(({ submit }) => submit())}>
						<div class="space-y-6">
							<!-- Email (Read-only) -->
							<div class="space-y-2">
								<Label for="email">
									<div class="flex items-center gap-2">
										<MailIcon class="w-4 h-4" />
										Email
									</div>
								</Label>
								<Input
									id="email"
									type="email"
									value={profile.email}
									disabled
									class="bg-muted"
								/>
								<p class="text-muted-foreground text-sm">
									Your email address cannot be changed
								</p>
							</div>

							<!-- Name -->
							<div class="space-y-2">
								<Label for="name">
									<div class="flex items-center gap-2">
										<UserIcon class="w-4 h-4" />
										Name
									</div>
								</Label>
								<input
									{...updateProfile.fields.name.as('text')}
									value={profile.name}
									placeholder="Enter your name"
									maxlength={100}
									class="flex bg-transparent file:bg-transparent disabled:opacity-50 shadow-sm px-3 py-1 border border-input file:border-0 rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring w-full h-9 file:font-medium placeholder:text-muted-foreground file:text-foreground md:text-sm file:text-sm text-base transition-colors disabled:cursor-not-allowed"
									oninput={() => {
										successMessage = null;
									}}
								/>
								{#each updateProfile.fields.name.issues() ?? [] as issue}
									<p class="text-destructive text-sm">{issue.message}</p>
								{/each}
								<p class="text-muted-foreground text-sm">
									This is the name that will be displayed on your profile
								</p>
							</div>

							<!-- Default Roaster Locations -->
							<div class="space-y-2">
								<Label for="defaultRoasterLocations">
									<div class="flex items-center gap-2">
										<MapPinIcon class="w-4 h-4" />
										Default Roaster Locations
									</div>
								</Label>
								<Svelecte
									bind:value={defaultRoasterLocations}
									options={data.roasterLocationOptions || []}
									placeholder="Select default roaster locations..."
									searchable
									clearable
									multiple
									class="w-full"
									onchange={() => {
										successMessage = null;
									}}
								/>
								<input
									type="hidden"
									name="defaultRoasterLocations"
									value={defaultRoasterLocations.join(',')}
								/>
								<p class="text-muted-foreground text-sm">
									These locations will be pre-selected when you search for coffee beans
								</p>
							</div>

							<!-- Newsletter Subscription -->
							<div class="flex justify-between items-center p-4 border rounded-lg">
								<div class="flex-1 space-y-0.5">
									<Label class="font-medium text-base">
										<div class="flex items-center gap-2">
											<BellIcon class="w-4 h-4" />
											Newsletter Subscription
										</div>
									</Label>
									<p class="text-muted-foreground text-sm">
										Receive updates about new features and roasters added to Kissaten. We won't send this more than once a month.
									</p>
								</div>
								<Switch
									bind:checked={newsletterSubscribed}
									onchange={() => {
										successMessage = null;
									}}
									aria-busy={!!updateProfile.pending}
								/>
							</div>
							<input
								type="hidden"
								name="newsletterSubscribed"
								value={newsletterSubscribed}
							/>

							<!-- Form Actions -->
							<div class="flex justify-end gap-3">
								<Button
									type="button"
									variant="outline"
									href="/"
								>
									Cancel
								</Button>
								<Button
									type="submit"
									aria-busy={!!updateProfile.pending}
								>
									{#if updateProfile.pending}
										Saving...
									{:else}
										Save Changes
									{/if}
								</Button>
							</div>
						</div>
					</form>
				{:catch error}
					<div class="py-8 text-destructive text-center">
						Failed to load profile. Please try again.
					</div>
				{/await}
			</Card.Content>
		</Card.Root>
	</div>
</div>

<style>
	/* Svelecte custom styling to match the design */
	:global(.svelecte) {
		--sv-border: 1px solid var(--border);
		--sv-border-radius: calc(var(--radius) - 2px);
		--sv-bg: var(--background);
		--sv-control-bg: var(--background);
		--sv-color: var(--foreground);
		--sv-placeholder-color: var(--muted-foreground);
		--sv-min-height: 2.5rem;
		--sv-font-size: 0.875rem;
	}

	:global(.svelecte:focus-within) {
		--sv-border: 2px solid hsl(var(--ring));
	}

	:global(.svelecte .sv-dropdown) {
		--sv-dropdown-bg: var(--popover);
		--sv-dropdown-border: 1px solid var(--border);
		--sv-dropdown-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
		--sv-dropdown-active-bg: var(--accent);
		--sv-dropdown-selected-bg: var(--primary);
	}

	:global(.svelecte .sv-item:hover) {
		--sv-dropdown-active-bg: var(--accent);
	}

	:global(.svelecte .sv-item.is-selected) {
		--sv-dropdown-selected-bg: var(--primary);
		color: var(--primary-foreground);
	}

	/* Styling for multiple selection chips */
	:global(.svelecte.is-multiple .sv-control) {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		padding: 0.25rem;
	}

	:global(.svelecte.is-multiple .sv-item-chip) {
		background: hsl(var(--primary));
		color: hsl(var(--primary-foreground));
		padding: 0.125rem 0.5rem;
		border-radius: calc(var(--radius) - 4px);
		font-size: 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	:global(.svelecte.is-multiple .sv-item-chip .sv-chip-remove) {
		cursor: pointer;
		opacity: 0.7;
	}

	:global(.svelecte.is-multiple .sv-item-chip .sv-chip-remove:hover) {
		opacity: 1;
	}
</style>
