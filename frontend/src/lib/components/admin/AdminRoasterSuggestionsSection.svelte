<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Popover from "$lib/components/ui/popover/index.js";
  import * as Command from "$lib/components/ui/command/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import ChevronDownIcon from "lucide-svelte/icons/chevron-down";
  import CheckIcon from "lucide-svelte/icons/check";
  import XIcon from "lucide-svelte/icons/x";
  import CheckCheckIcon from "lucide-svelte/icons/check-check";
  import InboxIcon from "lucide-svelte/icons/inbox";
  import CoffeeIcon from "lucide-svelte/icons/coffee";
  import {
    listAllRoasterSuggestions,
    approveSuggestion,
    rejectSuggestion,
    markSuggestionImplemented,
    type RoasterSuggestionStatusFilter,
  } from "$lib/api/admin.remote";
  import { formatRelative, formatAbsolute } from "$lib/utils/history";
  import { slugify } from "$lib/utils";
  import { toast } from "svelte-sonner";

  let { roasters }: { roasters: { slug: string; name: string }[] } = $props();

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
  let slugOpen = $state(false);

  // Roasters pulled in by the (main) layout — used to pick/validate the slug
  // the admin selects actually corresponds to a real roaster in the catalogue.
  const roasterOptions = $derived(
    (roasters ?? [])
      .map((r) => ({ slug: r.slug, name: r.name }))
      .sort((a, b) => a.name.localeCompare(b.name)),
  );
  const knownRoasterSlugs = $derived(
    new Set(roasterOptions.map((r) => r.slug)),
  );
  const selectedRoaster = $derived(
    roasterOptions.find((r) => r.slug === implementSlug.trim()),
  );
  const slugMissing = $derived(
    // If the roaster list failed to load (empty), don't block the admin.
    implementSlug.trim() !== "" &&
      knownRoasterSlugs.size > 0 &&
      !knownRoasterSlugs.has(implementSlug.trim()),
  );
  const slugValid = $derived(implementSlug.trim() !== "" && !slugMissing);
  const slugDisplay = $derived(
    selectedRoaster
      ? selectedRoaster.name
      : implementSlug.trim() || "Select a roaster…",
  );

  function handleRoasterSelect(slug: string) {
    implementSlug = slug;
    slugOpen = false;
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
            onclick={() =>
              (suggestionTab = tab as RoasterSuggestionStatusFilter)}
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
        <div class="py-8 text-muted-foreground text-center text-sm">
          Loading…
        </div>
      {:then rows}
        {#if rows.length === 0}
          <Card.Root>
            <Card.Content class="py-12">
              <div
                class="flex flex-col items-center gap-3 text-muted-foreground"
              >
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
                  <div
                    class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
                  >
                    <div class="flex-1 min-w-0 space-y-1">
                      <div class="flex items-center gap-2">
                        <CoffeeIcon
                          class="w-4 h-4 text-muted-foreground shrink-0"
                        />
                        <p class="font-semibold truncate">{row.name}</p>
                        {#if row.country}
                          <Badge class="" variant="secondary"
                            >{row.country}</Badge
                          >
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
                        {row.upvoteCount} upvote{row.upvoteCount === 1
                          ? ""
                          : "s"} · submitted by
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

                    <div
                      class="flex flex-wrap gap-2 sm:shrink-0 sm:justify-end"
                    >
                      {#if row.status === "pending"}
                        <Button
                          size="sm"
                          variant="outline"
                          class="flex-1 min-w-[7.5rem] sm:flex-none sm:min-w-0"
                          onclick={() => openRejectDialog(row.id, row.name)}
                        >
                          <XIcon class="mr-1 w-3.5 h-3.5" />
                          Reject
                        </Button>
                        <form
                          {...approveSuggestion
                            .for(row.id)
                            .enhance(async ({ submit }) => {
                              await submit();
                            })}
                          class="flex-1 min-w-[7.5rem] sm:flex-none sm:min-w-0"
                        >
                          <input
                            type="hidden"
                            name="suggestionId"
                            value={row.id}
                          />
                          <Button type="submit" size="sm" class="w-full">
                            <CheckIcon class="mr-1 w-3.5 h-3.5" />
                            Approve
                          </Button>
                        </form>
                        <Button
                          size="sm"
                          variant="outline"
                          class="flex-1 min-w-[7.5rem] sm:flex-none sm:min-w-0"
                          onclick={() =>
                            openImplementDialog(
                              row.id,
                              row.name,
                              row.implementedRoasterSlug ?? slugify(row.name),
                            )}
                        >
                          <CheckCheckIcon class="mr-1 w-3.5 h-3.5" />
                          Implemented
                        </Button>
                      {:else if row.status === "rejected"}
                        <form
                          {...approveSuggestion
                            .for(row.id)
                            .enhance(async ({ submit }) => {
                              await submit();
                            })}
                          class="flex-1 min-w-[7.5rem] sm:flex-none sm:min-w-0"
                        >
                          <input
                            type="hidden"
                            name="suggestionId"
                            value={row.id}
                          />
                          <Button type="submit" size="sm" class="w-full">
                            <CheckIcon class="mr-1 w-3.5 h-3.5" />
                            Approve
                          </Button>
                        </form>
                      {:else if row.status === "approved"}
                        <form
                          {...rejectSuggestion
                            .for(row.id)
                            .enhance(async ({ submit }) => {
                              await submit();
                            })}
                          class="flex-1 min-w-[7.5rem] sm:flex-none sm:min-w-0"
                        >
                          <input
                            type="hidden"
                            name="suggestionId"
                            value={row.id}
                          />
                          <Button
                            type="submit"
                            size="sm"
                            variant="outline"
                            class="flex-1 min-w-[7.5rem] sm:flex-none sm:min-w-0 w-full"
                          >
                            <XIcon class="mr-1 w-3.5 h-3.5" />
                            Reject
                          </Button>
                        </form>
                        <Button
                          size="sm"
                          variant="outline"
                          class="flex-1 min-w-[7.5rem] sm:flex-none sm:min-w-0"
                          onclick={() =>
                            openImplementDialog(
                              row.id,
                              row.name,
                              row.implementedRoasterSlug ?? slugify(row.name),
                            )}
                        >
                          <CheckCheckIcon class="mr-1 w-3.5 h-3.5" />
                          Implemented
                        </Button>
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

<!-- Reject suggestion confirmation -->
<Dialog.Root bind:open={rejectDialogOpen}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title>Reject this suggestion?</Dialog.Title>
      <Dialog.Description>
        "{rejectTargetName}" will be marked as rejected. Voters who opted in to
        notifications will be informed.
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
        Confirm the roaster slug for "{implementTargetName}". Voters who opted
        in to notifications will be told.
      </Dialog.Description>
    </Dialog.Header>
    <div class="space-y-2">
      <Label for="roaster-slug">Roaster</Label>
      <Popover.Root bind:open={slugOpen}>
        <Popover.Trigger
          id="roaster-slug"
          role="combobox"
          aria-expanded={slugOpen}
          aria-invalid={slugMissing}
          class="flex justify-between items-center bg-background shadow-sm px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring ring-offset-background w-full h-9 text-sm whitespace-nowrap disabled:cursor-not-allowed"
        >
          <span class="truncate {slugMissing ? 'text-destructive' : ''}">
            {slugDisplay}
          </span>
          <ChevronDownIcon class="opacity-50 ml-2 w-4 h-4 shrink-0" />
        </Popover.Trigger>
        <Popover.Content class="p-0 w-[280px]" align="start">
          <Command.Root>
            <Command.Input placeholder="Search roasters…" class="h-9" />
            <Command.Empty>No roaster found.</Command.Empty>
            <Command.List class="max-h-[240px] overflow-y-scroll no-scrollbar">
              <Command.Group>
                {#each roasterOptions as roaster (roaster.slug)}
                  <Command.Item
                    value={`${roaster.name} ${roaster.slug}`}
                    onSelect={() => handleRoasterSelect(roaster.slug)}
                    class="flex justify-between items-center group"
                  >
                    <span class="min-w-0">
                      <span
                        class="block truncate text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black"
                      >
                        {roaster.name}
                      </span>
                      <span
                        class="block truncate text-muted-foreground text-xs"
                      >
                        /roasters/{roaster.slug}
                      </span>
                    </span>
                    {#if implementSlug.trim() === roaster.slug}
                      <CheckIcon
                        class="ml-2 w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black"
                      />
                    {/if}
                  </Command.Item>
                {/each}
              </Command.Group>
            </Command.List>
          </Command.Root>
        </Popover.Content>
      </Popover.Root>
      {#if slugMissing}
        <p class="text-destructive text-sm">
          No known roaster with this slug. Pick one from the list.
        </p>
      {:else if slugValid}
        <p class="text-muted-foreground text-xs">
          Will notify opted-in voters and link to /roasters/{implementSlug.trim()}.
        </p>
      {/if}
    </div>
    <Dialog.Footer>
      <Button variant="outline" onclick={() => (implementDialogOpen = false)}>
        Cancel
      </Button>
      <form
        class="w-full"
        {...markSuggestionImplemented.enhance(async ({ submit }) => {
          await submit();
          implementDialogOpen = false;
        })}
      >
        <input
          type="hidden"
          name="suggestionId"
          value={implementTargetId ?? ""}
        />
        <input type="hidden" name="roasterSlug" value={implementSlug.trim()} />
        <Button type="submit" disabled={!slugValid} class="w-full sm:w-auto">
          <CheckCheckIcon class="mr-2 w-4 h-4" />
          Mark implemented
        </Button>
      </form>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
