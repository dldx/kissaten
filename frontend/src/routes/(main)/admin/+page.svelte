<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import * as Table from "$lib/components/ui/table/index.js";
	import * as Dialog from "$lib/components/ui/dialog/index.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import { Separator } from "$lib/components/ui/separator/index.js";
	import UsersIcon from "lucide-svelte/icons/users";
	import FlaskConicalIcon from "lucide-svelte/icons/flask-conical";
	import MailIcon from "lucide-svelte/icons/mail";
	import CoffeeIcon from "lucide-svelte/icons/coffee";
	import SearchIcon from "lucide-svelte/icons/search";
	import CheckIcon from "lucide-svelte/icons/check";
	import XIcon from "lucide-svelte/icons/x";
	import CheckCheckIcon from "lucide-svelte/icons/check-check";
	import ShieldCheckIcon from "lucide-svelte/icons/shield-check";
	import InboxIcon from "lucide-svelte/icons/inbox";
	import {
		getAdminStats,
		listBetaInterest,
		listAllUsers,
		listAllRoasterSuggestions,
		approveBetaTester,
		declineBetaTester,
		approveSuggestion,
		rejectSuggestion,
		markSuggestionImplemented,
		type RoasterSuggestionStatusFilter
	} from "$lib/api/admin.remote";
	import { toast } from "svelte-sonner";

	let { data } = $props();

	const stats = $derived(getAdminStats());
	const betaInterest = $derived(listBetaInterest());

	let userSearch = $state("");
	const allUsers = $derived(listAllUsers());
	const filteredUsers = $derived.by(() => {
		const search = userSearch.trim().toLowerCase();
		return allUsers.then((rows) =>
			search
				? rows.filter(
						(r) =>
							r.email.toLowerCase().includes(search) ||
							r.name.toLowerCase().includes(search) ||
							r.role.toLowerCase().includes(search)
					)
				: rows
		);
	});

	let suggestionTab = $state<RoasterSuggestionStatusFilter>("pending");
	const allSuggestions = $derived(listAllRoasterSuggestions());
	const filteredSuggestions = $derived.by(() => {
		const tab = suggestionTab;
		return allSuggestions.then((rows) => rows.filter((r) => r.status === tab));
	});

	let rejectDialogOpen = $state(false);
	let rejectTargetId = $state<string | null>(null);
	let rejectTargetName = $state<string>("");

	let implementDialogOpen = $state(false);
	let implementTargetId = $state<string | null>(null);
	let implementTargetName = $state<string>("");
	let implementSlug = $state<string>("");

	function formatRelative(date: Date | string | number): string {
		const d = new Date(date);
		const diffMs = Date.now() - d.getTime();
		const sec = Math.floor(diffMs / 1000);
		if (sec < 60) return "just now";
		const min = Math.floor(sec / 60);
		if (min < 60) return `${min}m ago`;
		const hr = Math.floor(min / 60);
		if (hr < 24) return `${hr}h ago`;
		const day = Math.floor(hr / 24);
		if (day < 30) return `${day}d ago`;
		return d.toLocaleDateString();
	}

	function formatAbsolute(date: Date | string | number): string {
		return new Date(date).toLocaleString();
	}

	function openRejectDialog(id: string, name: string) {
		rejectTargetId = id;
		rejectTargetName = name;
		rejectDialogOpen = true;
	}

	function openImplementDialog(id: string, name: string, slug: string) {
		implementTargetId = id;
		implementTargetName = name;
		implementSlug = slug;
		implementDialogOpen = true;
	}

	function slugify(s: string): string {
		return s
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9]+/g, "-")
			.replace(/^-+|-+$/g, "");
	}

	$effect(() => {
		if (approveBetaTester.result?.success) {
			toast.success("Approved — user can now enable beta features.");
		}
	});
	$effect(() => {
		if (declineBetaTester.result?.success) {
			toast.success("Declined — interest removed.");
		}
	});
	$effect(() => {
		if (approveSuggestion.result?.success) {
			toast.success("Suggestion approved.");
		}
	});
	$effect(() => {
		if (rejectSuggestion.result?.success) {
			toast.success("Suggestion rejected.");
		}
	});
	$effect(() => {
		if (markSuggestionImplemented.result?.success) {
			toast.success("Marked as implemented.");
		}
	});
</script>

<svelte:head>
	<title>Admin | Kissaten</title>
	<meta name="robots" content="noindex,nofollow" />
</svelte:head>

<div class="mx-auto px-4 py-8 container max-w-6xl">
	<!-- Header -->
	<div class="space-y-1 mb-2">
		<div class="flex items-center gap-2">
			<ShieldCheckIcon class="w-7 h-7 text-primary" />
			<h1 class="font-bold text-3xl">Admin</h1>
			<Badge class="" variant="secondary">{data.currentAdmin.email}</Badge>
		</div>
		<p class="text-muted-foreground">
			Overview, beta program, newsletter, and roaster suggestion queues.
		</p>
	</div>

	<!-- In-page section nav -->
	<nav
		class="top-14 z-30 sticky bg-background/80 supports-backdrop-filter:bg-background/60 backdrop-blur -mx-4 px-4 py-2 mb-6 border-b"
	>
		<div class="flex gap-1 font-medium text-sm">
			<a
				href="#stats"
				class="hover:bg-muted px-3 py-1.5 rounded-md transition-colors"
			>
				Stats
			</a>
			<a
				href="#beta-interest"
				class="hover:bg-muted px-3 py-1.5 rounded-md transition-colors"
			>
				Beta Interest
			</a>
			<a
				href="#roaster-suggestions"
				class="hover:bg-muted px-3 py-1.5 rounded-md transition-colors"
			>
				Roaster Suggestions
			</a>
			<a
				href="#newsletter"
				class="hover:bg-muted px-3 py-1.5 rounded-md transition-colors"
			>
				Users
			</a>
		</div>
	</nav>

	<div class="space-y-10">
		<!-- ── KPI cards ──────────────────────────────────────────── -->
		<section id="stats" class="space-y-3 scroll-mt-24">
			<h2 class="font-semibold text-xl">Overview</h2>
			{#await stats}
				<div class="py-8 text-muted-foreground text-center text-sm">
					Loading stats…
				</div>
			{:then s}
				<div class="gap-4 grid grid-cols-2 lg:grid-cols-4">
					<Card.Root>
						<Card.Content class="pt-6">
							<div
								class="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-wider"
							>
								<UsersIcon class="w-3.5 h-3.5" />
								Total users
							</div>
							<p class="mt-1 font-bold text-3xl tabular-nums">
								{s.totalUsers.toLocaleString()}
							</p>
						</Card.Content>
					</Card.Root>

					<Card.Root>
						<Card.Content class="pt-6">
							<div
								class="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-wider"
							>
								<FlaskConicalIcon class="w-3.5 h-3.5" />
								Beta interest (pending)
							</div>
							<p class="mt-1 font-bold text-3xl tabular-nums">
								{s.pendingBetaInterest.toLocaleString()}
							</p>
						</Card.Content>
					</Card.Root>

					<Card.Root>
						<Card.Content class="pt-6">
							<div
								class="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-wider"
							>
								<MailIcon class="w-3.5 h-3.5" />
								Newsletter
							</div>
							<p class="mt-1 font-bold text-3xl tabular-nums">
								{s.newsletterSubscribers.toLocaleString()}
							</p>
						</Card.Content>
					</Card.Root>

					<Card.Root>
						<Card.Content class="pt-6">
							<div
								class="flex items-center gap-2 text-muted-foreground text-xs uppercase tracking-wider"
							>
								<CoffeeIcon class="w-3.5 h-3.5" />
								Pending suggestions
							</div>
							<p class="mt-1 font-bold text-3xl tabular-nums">
								{s.pendingRoasterSuggestions.toLocaleString()}
							</p>
						</Card.Content>
					</Card.Root>
				</div>

				<p class="text-muted-foreground text-xs">
					{s.activeBetaTesters.toLocaleString()} active beta tester{s.activeBetaTesters === 1
						? ""
						: "s"} (isBetaAllowed + betaEnabled).
				</p>
			{:catch}
				<div class="py-8 text-destructive text-center text-sm">
					Failed to load stats.
				</div>
			{/await}
		</section>

		<Separator />

		<!-- ── Beta Interest queue ───────────────────────────────── -->
		<section id="beta-interest" class="space-y-3 scroll-mt-24">
			<div>
				<h2 class="font-semibold text-xl">Beta Program Interest</h2>
				<p class="text-muted-foreground text-sm">
					Users who asked to join the beta program. Approving flips
					<code class="bg-muted px-1 rounded">isBetaAllowed</code> on and clears
					their interest flag.
				</p>
			</div>

			{#await betaInterest}
				<div class="py-8 text-muted-foreground text-center text-sm">Loading…</div>
			{:then rows}
				{#if rows.length === 0}
					<Card.Root>
						<Card.Content class="py-12">
							<div class="flex flex-col items-center gap-3 text-muted-foreground">
								<CheckCheckIcon class="w-10 h-10" />
								<p class="font-medium">No pending beta requests.</p>
								<p class="text-sm">You're all caught up.</p>
							</div>
						</Card.Content>
					</Card.Root>
				{:else}
					<Card.Root>
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>User</Table.Head>
									<Table.Head>Email</Table.Head>
									<Table.Head>Asked</Table.Head>
									<Table.Head class="text-end">Actions</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each rows as row (row.id)}
									<Table.Row>
										<Table.Cell class="font-medium">{row.name}</Table.Cell>
										<Table.Cell class="text-muted-foreground">{row.email}</Table.Cell>
										<Table.Cell>
											<span title={formatAbsolute(row.updatedAt)}>
												{formatRelative(row.updatedAt)}
											</span>
										</Table.Cell>
										<Table.Cell class="text-end">
											<div class="flex justify-end gap-2">
												<form
													{...declineBetaTester.for(row.id).enhance(async ({ submit }) => {
														await submit();
													})}
												>
													<input type="hidden" name="userId" value={row.id} />
													<Button type="submit" variant="outline" size="sm">
														<XIcon class="mr-1 w-3.5 h-3.5" />
														Decline
													</Button>
												</form>
												<form
													{...approveBetaTester.for(row.id).enhance(async ({ submit }) => {
														await submit();
													})}
												>
													<input type="hidden" name="userId" value={row.id} />
													<Button type="submit" size="sm">
														<CheckIcon class="mr-1 w-3.5 h-3.5" />
														Approve
													</Button>
												</form>
											</div>
										</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</Card.Root>
				{/if}
			{:catch}
				<div class="py-8 text-destructive text-center text-sm">
					Failed to load beta interest queue.
				</div>
			{/await}
		</section>

		<Separator />

		<!-- ── Roaster Suggestions queue ─────────────────────────── -->
		<section id="roaster-suggestions" class="space-y-3 scroll-mt-24">
			<div>
				<h2 class="font-semibold text-xl">Roaster Suggestions</h2>
				<p class="text-muted-foreground text-sm">
					User-submitted roaster requests. Upvote count is from public votes.
				</p>
			</div>

			<!-- Status tab strip -->
			<div class="flex flex-wrap gap-1 border-b">
				{#each ["pending", "approved", "rejected", "implemented"] as tab (tab)}
					<button
						type="button"
						onclick={() => (suggestionTab = tab as RoasterSuggestionStatusFilter)}
						class="relative px-3 py-2 font-medium text-sm transition-colors {suggestionTab ===
						tab
							? 'text-foreground'
							: 'text-muted-foreground hover:text-foreground'}"
					>
						{tab.charAt(0).toUpperCase() + tab.slice(1)}
						{#if suggestionTab === tab}
							<span
								class="bottom-0 left-2 right-2 absolute bg-primary rounded-full h-0.5"
							></span>
						{/if}
					</button>
				{/each}
			</div>

			{#await filteredSuggestions}
				<div class="py-8 text-muted-foreground text-center text-sm">Loading…</div>
			{:then rows}
				{#if rows.length === 0}
					<Card.Root>
						<Card.Content class="py-12">
							<div class="flex flex-col items-center gap-3 text-muted-foreground">
								<InboxIcon class="w-10 h-10" />
								<p class="font-medium">Nothing here.</p>
								<p class="text-sm">No {suggestionTab} roaster suggestions.</p>
							</div>
						</Card.Content>
					</Card.Root>
				{:else}
					<div class="space-y-2">
						{#each rows as row (row.id)}
							<Card.Root>
								<Card.Content class="pt-6">
									<div class="flex justify-between items-start gap-4">
										<div class="flex-1 min-w-0 space-y-1">
											<div class="flex items-center gap-2">
												<CoffeeIcon class="w-4 h-4 text-muted-foreground shrink-0" />
												<p class="font-semibold truncate">{row.name}</p>
												{#if row.country}
													<Badge class="" variant="secondary">{row.country}</Badge>
												{/if}
											</div>
											{#if row.website}
												<a
													href={row.website}
													target="_blank"
													rel="noopener noreferrer"
													class="block text-muted-foreground text-sm truncate hover:underline"
												>
													{row.website}
												</a>
											{/if}
											<p class="text-muted-foreground text-xs">
												{row.upvoteCount} upvote{row.upvoteCount === 1 ? "" : "s"} ·
												submitted by
												{row.suggesterName ?? row.suggesterEmail ?? "anon"}
												<span title={formatAbsolute(row.createdAt)}>
													· {formatRelative(row.createdAt)}
												</span>
												{#if row.status === "implemented" && row.implementedRoasterSlug}
													· slug
													<code class="bg-muted px-1 rounded"
														>{row.implementedRoasterSlug}</code
													>
												{/if}
											</p>
										</div>

										<div class="flex shrink-0 gap-2">
											{#if row.status === "pending"}
												<Button
													size="sm"
													variant="outline"
													onclick={() => openRejectDialog(row.id, row.name)}
												>
													<XIcon class="mr-1 w-3.5 h-3.5" />
													Reject
												</Button>
												<Button
													size="sm"
													variant="outline"
													onclick={() =>
														openImplementDialog(
															row.id,
															row.name,
															row.implementedRoasterSlug ?? slugify(row.name)
														)}
												>
													<CheckCheckIcon class="mr-1 w-3.5 h-3.5" />
													Implemented
												</Button>
											<form
												{...approveSuggestion.for(row.id).enhance(async ({ submit }) => {
													await submit();
												})}
											>
												<input type="hidden" name="suggestionId" value={row.id} />
												<Button type="submit" size="sm">
													<CheckIcon class="mr-1 w-3.5 h-3.5" />
													Approve
												</Button>
											</form>
										{:else if row.status === "rejected"}
											<form
												{...approveSuggestion.for(row.id).enhance(async ({ submit }) => {
													await submit();
												})}
											>
													<input type="hidden" name="suggestionId" value={row.id} />
													<Button type="submit" size="sm">
														<CheckIcon class="mr-1 w-3.5 h-3.5" />
														Approve
													</Button>
												</form>
											{:else if row.status === "approved"}
											<form
												{...rejectSuggestion.for(row.id).enhance(async ({ submit }) => {
													await submit();
												})}
											>
												<input type="hidden" name="suggestionId" value={row.id} />
												<Button type="submit" size="sm" variant="outline">
														<XIcon class="mr-1 w-3.5 h-3.5" />
														Reject
													</Button>
												</form>
											{/if}
										</div>
									</div>
								</Card.Content>
							</Card.Root>
						{/each}
					</div>
				{/if}
			{:catch}
				<div class="py-8 text-destructive text-center text-sm">
					Failed to load suggestions.
				</div>
			{/await}
		</section>

		<Separator />

		<!-- ── All Users ──────────────────────────────────────── -->
		<section id="newsletter" class="space-y-3 scroll-mt-24">
			<div>
				<h2 class="font-semibold text-xl">All Users</h2>
				<p class="text-muted-foreground text-sm">
					Everyone signed in to Kissaten, with role and beta status.
				</p>
			</div>

			<div class="relative max-w-sm">
				<SearchIcon
					class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2"
				/>
				<Input
					type="search"
					placeholder="Search by name, email, or role…"
					class="pl-9"
					bind:value={userSearch}
				/>
			</div>

			{#await filteredUsers}
				<div class="py-8 text-muted-foreground text-center text-sm">Loading…</div>
			{:then rows}
				{#if rows.length === 0}
					<Card.Root>
						<Card.Content class="py-12">
							<div class="flex flex-col items-center gap-3 text-muted-foreground">
								<InboxIcon class="w-10 h-10" />
								<p class="font-medium">
									{userSearch.trim() ? "No matches." : "No users yet."}
								</p>
							</div>
						</Card.Content>
					</Card.Root>
				{:else}
					<Card.Root>
						<Table.Root>
							<Table.Header>
								<Table.Row>
									<Table.Head>Name</Table.Head>
									<Table.Head>Email</Table.Head>
									<Table.Head>Role</Table.Head>
									<Table.Head>Beta status</Table.Head>
									<Table.Head>Newsletter</Table.Head>
									<Table.Head>Joined</Table.Head>
								</Table.Row>
							</Table.Header>
							<Table.Body>
								{#each rows as row (row.id)}
									<Table.Row>
										<Table.Cell class="font-medium">{row.name}</Table.Cell>
										<Table.Cell class="text-muted-foreground">{row.email}</Table.Cell>
										<Table.Cell>
											{#if row.role === "admin"}
												<Badge class="" variant="default">
													<ShieldCheckIcon class="mr-1 w-3 h-3" />
													Admin
												</Badge>
											{:else}
												<span class="text-muted-foreground text-sm">User</span>
											{/if}
										</Table.Cell>
										<Table.Cell>
											{#if row.isBetaAllowed && row.betaEnabled}
												<Badge class="" variant="default">Active</Badge>
											{:else if row.isBetaAllowed}
												<Badge class="" variant="secondary">Approved · off</Badge>
											{:else if row.betaInterest}
												<Badge class="" variant="outline">
													<FlaskConicalIcon class="mr-1 w-3 h-3" />
													Waitlisted
												</Badge>
											{:else}
												<span class="text-muted-foreground text-sm">—</span>
											{/if}
										</Table.Cell>
										<Table.Cell>
											{#if row.newsletterSubscribed}
												<Badge class="" variant="secondary">
													<MailIcon class="mr-1 w-3 h-3" />
													Subscribed
												</Badge>
											{:else}
												<span class="text-muted-foreground text-sm">—</span>
											{/if}
										</Table.Cell>
										<Table.Cell>
											<span title={formatAbsolute(row.createdAt)}>
												{formatRelative(row.createdAt)}
											</span>
										</Table.Cell>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</Card.Root>
				{/if}
			{:catch}
				<div class="py-8 text-destructive text-center text-sm">
					Failed to load users.
				</div>
			{/await}
		</section>
	</div>
</div>

<!-- Reject suggestion confirmation -->
<Dialog.Root bind:open={rejectDialogOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Reject this suggestion?</Dialog.Title>
			<Dialog.Description>
				"{rejectTargetName}" will be marked as rejected. Voters who opted in
				to notifications will be informed.
			</Dialog.Description>
		</Dialog.Header>
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (rejectDialogOpen = false)}>
				Cancel
			</Button>
			<form
				{...rejectSuggestion.enhance(async ({ submit }) => {
					await submit();
					rejectDialogOpen = false;
				})}
			>
				<input type="hidden" name="suggestionId" value={rejectTargetId ?? ""} />
				<Button type="submit" variant="outline">
					<XIcon class="mr-2 w-4 h-4" />
					Reject
				</Button>
			</form>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<!-- Mark implemented dialog -->
<Dialog.Root bind:open={implementDialogOpen}>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title>Mark as implemented</Dialog.Title>
			<Dialog.Description>
				Confirm the roaster slug for "{implementTargetName}". Voters who
				opted in to notifications will be told.
			</Dialog.Description>
		</Dialog.Header>
		<div class="space-y-2">
			<Label for="roaster-slug">Roaster slug</Label>
			<Input
				id="roaster-slug"
				bind:value={implementSlug}
				placeholder="e.g. northern-coffee-works"
			/>
		</div>
		<Dialog.Footer>
			<Button variant="outline" onclick={() => (implementDialogOpen = false)}>
				Cancel
			</Button>
			<form
				{...markSuggestionImplemented.enhance(async ({ submit }) => {
					await submit();
					implementDialogOpen = false;
				})}
			>
				<input type="hidden" name="suggestionId" value={implementTargetId ?? ""} />
				<input type="hidden" name="roasterSlug" value={implementSlug} />
				<Button type="submit" disabled={!implementSlug.trim()}>
					<CheckCheckIcon class="mr-2 w-4 h-4" />
					Mark implemented
				</Button>
			</form>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
