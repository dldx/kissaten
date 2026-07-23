<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import {
    Coffee,
    Search,
    Lightbulb,
    ArrowUp,
    ExternalLink,
    MapPin,
  } from "lucide-svelte";
  import RoasterCard from "$lib/components/RoasterCard.svelte";
  import RoasterStickerWall from "$lib/components/RoasterStickerWall.svelte";
  import { type Roaster } from "$lib/api.js";
  import type { PageData } from "./$types";
  import { scale, fade } from "svelte/transition";
  import { LayoutGrid, Sticker } from "lucide-svelte";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { authClient } from "$lib/auth-client";
  import {
    submitRoasterSuggestion,
    upvoteRoasterSuggestion,
    updateVoteNotify,
    type RoasterSuggestion,
  } from "$lib/api/roaster_suggestions.remote";
  import { invalidateAll, goto } from "$app/navigation";
  import { untrack } from "svelte";
  import { toast } from "svelte-sonner";

  interface Props {
    data: PageData;
  }

  let { data }: Props = $props();

  let roasters: Roaster[] = $state(data.roasters);
  let suggestions: RoasterSuggestion[] = $state(data.suggestions);
  let searchQuery = $state("");
  let debouncedSearchQuery = $state("");
  let showStickerWall = $state(false);
  let debounceTimer: any;

  const session = authClient.useSession();

  let showSuggestDialog = $state(false);
  let typedName = $state("");
  let typedCountry = $state("");
  let typedWebsite = $state("");
  let notifyOnImplementation = $state(false);
  let upvoteNotify = $state(false);
  let dropdownOpen = $state(false);
  let nameFieldContainer: HTMLDivElement | null = $state(null);
  let upvotingId: string | null = $state(null);

  function handleSearchInput(e: Event & { currentTarget: HTMLInputElement }) {
    const value = e.currentTarget.value;
    searchQuery = value;

    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      debouncedSearchQuery = value;
    }, 300);
  }

  const filteredRoasters = $derived.by(() => {
    if (!searchQuery.trim()) {
      return roasters;
    } else {
      const query = searchQuery.toLowerCase();
      return roasters.filter(
        (roaster) =>
          roaster.name.toLowerCase().includes(query) ||
          (roaster.location && roaster.location.toLowerCase().includes(query)),
      );
    }
  });

  // --- Suggest-a-roaster helpers -------------------------------------------

  const normalizedTyped = $derived(typedName.trim().toLowerCase());

  const implementedMatch = $derived<Roaster | undefined>(
    normalizedTyped
      ? roasters.find((r) => r.name.trim().toLowerCase() === normalizedTyped)
      : undefined,
  );

  const suggestionMatch = $derived<RoasterSuggestion | undefined>(
    normalizedTyped
      ? suggestions.find((s) => s.nameNormalized === normalizedTyped)
      : undefined,
  );

  const isDuplicate = $derived(Boolean(implementedMatch || suggestionMatch));

  interface ComboboxItem {
    kind: "implemented" | "suggested";
    name: string;
    slug?: string;
    location?: string;
    id?: string;
    upvoteCount?: number;
    hasUpvoted?: boolean;
    country?: string | null;
    website?: string | null;
    notifyOnImplementation?: boolean | null;
  }

  const comboboxItems = $derived.by<ComboboxItem[]>(() => {
    if (!normalizedTyped) return [];
    const items: ComboboxItem[] = [];
    for (const r of roasters) {
      if (r.name.toLowerCase().includes(normalizedTyped)) {
        items.push({
          kind: "implemented",
          name: r.name,
          slug: r.slug,
          location: r.location,
        });
      }
      if (items.length >= 5) break;
    }
    for (const s of suggestions) {
      if (s.nameNormalized.includes(normalizedTyped)) {
        items.push({
          kind: "suggested",
          name: s.name,
          id: s.id,
          upvoteCount: s.upvoteCount,
          hasUpvoted: s.hasUpvoted,
          country: s.country,
          website: s.website,
          notifyOnImplementation: s.notifyOnImplementation,
        });
      }
      if (items.length >= 10) break;
    }
    return items;
  });

  function handleSelectItem(item: ComboboxItem) {
    typedName = item.name;
    if (item.kind === "suggested") {
      if (item.country) typedCountry = item.country;
      if (item.website) typedWebsite = item.website;
    }
    dropdownOpen = false;
  }

  $effect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        nameFieldContainer &&
        !nameFieldContainer.contains(e.target as Node)
      ) {
        dropdownOpen = false;
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  });

  $effect(() => {
    const result = submitRoasterSuggestion.result;
    if (!result) return;
    if (result.status === "created") {
      toast.success(
        `Suggested "${result.suggestion.name}"! Thanks for the recommendation.`,
      );
      // Optimistic update: prepend the new suggestion so it appears
      // immediately without waiting for `invalidateAll` to refetch.
      // `untrack` avoids reading `suggestions` reactively — otherwise
      // writing to it would retrigger this effect (infinite loop → crash).
      untrack(() => {
        suggestions = [result.suggestion, ...suggestions];
        resetSuggestForm();
        showSuggestDialog = false;
      });
      void invalidateAll();
    } else if (result.status === "exists") {
      toast.info(
        `"${result.suggestion.name}" was already suggested — upvote it instead.`,
      );
    }
  });

  function resetSuggestForm() {
    typedName = "";
    typedCountry = "";
    typedWebsite = "";
    notifyOnImplementation = false;
    dropdownOpen = false;
  }

  async function handleUpvote(suggestionId: string) {
    if (!$session.data) {
      goto("/login");
      return;
    }
    upvotingId = suggestionId;
    try {
      const result = await upvoteRoasterSuggestion({
        suggestionId,
        notifyOnImplementation: upvoteNotify,
      });
      if (result.status === "ok") {
        toast.success("Upvoted!");
        suggestions = suggestions.map((s) =>
          s.id === suggestionId
            ? {
                ...s,
                upvoteCount: result.upvoteCount,
                hasUpvoted: true,
                notifyOnImplementation: result.notifyOnImplementation,
              }
            : s,
        );
      } else if (result.status === "already_voted") {
        toast.info("You've already upvoted this suggestion.");
        suggestions = suggestions.map((s) =>
          s.id === suggestionId
            ? {
                ...s,
                upvoteCount: result.upvoteCount,
                hasUpvoted: true,
                notifyOnImplementation: result.notifyOnImplementation,
              }
            : s,
        );
      }
    } catch (err) {
      console.error("[roasters] upvote failed:", err);
      toast.error("Failed to upvote. Please try again.");
    } finally {
      upvotingId = null;
    }
  }

  async function handleToggleNotify(suggestionId: string, notify: boolean) {
    try {
      await updateVoteNotify({
        suggestionId,
        notifyOnImplementation: notify,
      });
      suggestions = suggestions.map((s) =>
        s.id === suggestionId
          ? { ...s, notifyOnImplementation: notify }
          : s,
      );
    } catch (err) {
      console.error("[roasters] notify toggle failed:", err);
      toast.error("Failed to update notification preference.");
    }
  }
</script>

<svelte:head>
  <title>Coffee Roasters | Kissaten</title>
  <meta
    name="description"
    content="Browse coffee roasters from around the world"
  />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
  <!-- Header -->
  <div class="mb-12 text-center">
    <h1
      class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
    >
      Coffee Roasters
    </h1>
    <p
      class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl"
    >
      From small artisanal roasters to established coffee houses, each brings
      their own expertise and passion to the craft.
    </p>

    <!-- Continent Links -->
    <div class="flex flex-wrap justify-center gap-2 mx-auto mt-6 max-w-2xl">
      <a
        href="/roasted-in/africa"
        class="bg-white hover:bg-gray-50 dark:bg-slate-700/60 dark:hover:bg-slate-700 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg font-medium text-gray-700 dark:text-cyan-200 text-sm transition-colors"
      >
        Africa
      </a>
      <a
        href="/roasted-in/asia"
        class="bg-white hover:bg-gray-50 dark:bg-slate-700/60 dark:hover:bg-slate-700 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg font-medium text-gray-700 dark:text-cyan-200 text-sm transition-colors"
      >
        Asia
      </a>
      <a
        href="/roasted-in/europe"
        class="bg-white hover:bg-gray-50 dark:bg-slate-700/60 dark:hover:bg-slate-700 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg font-medium text-gray-700 dark:text-cyan-200 text-sm transition-colors"
      >
        Europe
      </a>
      <a
        href="/roasted-in/european-union"
        class="bg-white hover:bg-gray-50 dark:bg-slate-700/60 dark:hover:bg-slate-700 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg font-medium text-gray-700 dark:text-cyan-200 text-sm transition-colors"
      >
        EU
      </a>
      <a
        href="/roasted-in/north-america"
        class="bg-white hover:bg-gray-50 dark:bg-slate-700/60 dark:hover:bg-slate-700 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg font-medium text-gray-700 dark:text-cyan-200 text-sm transition-colors"
      >
        North America
      </a>
      <a
        href="/roasted-in/south-america"
        class="bg-white hover:bg-gray-50 dark:bg-slate-700/60 dark:hover:bg-slate-700 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg font-medium text-gray-700 dark:text-cyan-200 text-sm transition-colors"
      >
        South America
      </a>
      <a
        href="/roasted-in/oceania"
        class="bg-white hover:bg-gray-50 dark:bg-slate-700/60 dark:hover:bg-slate-700 px-4 py-2 border border-gray-200 dark:border-slate-600 rounded-lg font-medium text-gray-700 dark:text-cyan-200 text-sm transition-colors"
      >
        Oceania
      </a>
    </div>

    <!-- Suggest a Roaster button -->
    <div class="mt-6">
      <Button
        onclick={() => (showSuggestDialog = true)}
        variant="default"
        class="gap-2"
      >
        <Lightbulb class="w-4 h-4" />
        Suggest a Roaster
      </Button>
    </div>
  </div>

  <!-- Search Bar -->
  <div class="mx-auto mb-8 max-w-md">
    <div class="relative">
      <Search
        class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
      />
      <input
        value={searchQuery}
        oninput={handleSearchInput}
        placeholder="Search roasters by name or country..."
        class="bg-white dark:bg-slate-700/60 px-3 py-2 pl-10 border border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 rounded-md outline-none focus:ring-1 focus:ring-orange-500 dark:focus:ring-emerald-500/50 w-full h-10 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500 text-sm transition-all"
      />
    </div>
  </div>

  <!-- View Toggle -->
  <div class="flex justify-center mb-8">
    <div
      class="justify-center justify-self-center items-center grid grid-cols-2 bg-gray-100 dark:bg-slate-700/60 p-1 border border-gray-200 dark:border-slate-600 rounded-lg w-fit"
    >
      <button
        onclick={() => (showStickerWall = false)}
        class="px-4 py-2 text-sm flex flex-col items-center justify-center gap-2 font-medium rounded-md transition-all {!showStickerWall
          ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-cyan-100 shadow-sm'
          : 'text-gray-500 dark:text-cyan-400/60 hover:text-gray-900 dark:hover:text-cyan-100'}"
      >
        <LayoutGrid class="w-6 h-6" /> Grid
      </button>
      <button
        onclick={() => (showStickerWall = true)}
        class="px-4 py-2 text-sm flex flex-col items-center justify-center gap-2 font-medium rounded-md transition-all {showStickerWall
          ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-cyan-100 shadow-sm'
          : 'text-gray-500 dark:text-cyan-400/60 hover:text-gray-900 dark:hover:text-cyan-100'}"
      >
        <Sticker class="w-6 h-6" /> Stickers
      </button>
    </div>
  </div>

  <!-- Roasters Content -->
  {#if filteredRoasters && (filteredRoasters.length > 0 || !searchQuery)}
    <!-- Results Summary -->
    <div class="mb-4 text-gray-600 dark:text-cyan-400/80 text-sm text-right">
      {#if filteredRoasters.length === roasters.length}
        {roasters.length} roasters
      {:else}
        Showing {filteredRoasters.length} of {roasters.length} roasters
      {/if}
    </div>

    {#if showStickerWall}
      <div in:fade={{ duration: 300 }}>
        <RoasterStickerWall {roasters} {debouncedSearchQuery} />
      </div>
    {:else}
      <div
        class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
        in:fade={{ duration: 300 }}
      >
        {#each filteredRoasters as roaster, roaster_index (roaster.id)}
          <div in:scale|global={{ delay: 10 * roaster_index }}>
            <RoasterCard {roaster} />
          </div>
        {/each}
      </div>
    {/if}
  {/if}

  <!-- Empty State -->
  {#if filteredRoasters && filteredRoasters.length === 0 && searchQuery}
    <div class="py-12 text-center">
      <Coffee
        class="mx-auto mb-4 w-12 h-12 text-gray-500 dark:text-cyan-400/70"
      />
      <h3 class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl">
        No roasters found
      </h3>
      <p class="mb-4 text-gray-600 dark:text-cyan-300/80">
        Try searching with different keywords, or suggest a new roaster.
      </p>
      <div class="flex justify-center gap-3">
        <Button
          onclick={() => (searchQuery = "")}
          class="bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white"
          >Clear Search</Button
        >
        <Button
          onclick={() => {
            typedName = searchQuery;
            showSuggestDialog = true;
          }}
          variant="default"
          class="gap-2"
        >
          <Lightbulb class="w-4 h-4" />
          Suggest "{searchQuery}"
        </Button>
      </div>
    </div>
  {/if}
</div>

<!-- Suggest a Roaster Dialog -->
<Dialog.Root
  bind:open={showSuggestDialog}
  onOpenChange={(open) => {
    if (!open) resetSuggestForm();
  }}
>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title class="flex items-center gap-2">
        <Lightbulb class="w-5 h-5 text-orange-600 dark:text-cyan-400" />
        Suggest a Roaster
      </Dialog.Title>
      <Dialog.Description>
        Know a roaster we should add? Suggest them below.
      </Dialog.Description>
    </Dialog.Header>

    {#if $session.data}
      <form
        {...submitRoasterSuggestion.enhance(({ submit }) => submit())}
        class="space-y-4"
      >
		<!-- Roaster Name with autocomplete -->
			<div class="space-y-2">
				<Label for="roaster-name">Roaster name</Label>
				<div bind:this={nameFieldContainer}>
					<div class="relative">
						<Search
							class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 pointer-events-none transform"
						/>
						<input
							name="name"
							id="roaster-name"
							bind:value={typedName}
							onfocus={() => (dropdownOpen = true)}
							oninput={() => {
								dropdownOpen = true;
							}}
							placeholder="e.g. Onyx Coffee Lab"
							autocomplete="off"
							class="bg-white dark:bg-slate-700/60 px-3 py-2 pl-10 border border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 rounded-md outline-none focus:ring-1 focus:ring-orange-500 dark:focus:ring-emerald-500/50 w-full h-10 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500 text-sm transition-all"
						/>
					</div>
					{#if dropdownOpen && comboboxItems.length > 0}
						<div
							class="z-50 bg-white dark:bg-slate-800 shadow-lg mt-1 border border-gray-200 dark:border-slate-600 rounded-md max-h-60 overflow-y-auto"
							transition:fade={{ duration: 100 }}
						>
                {#each comboboxItems as item (item.kind + ":" + (item.slug || item.id))}
                  <div
                    class="flex justify-between items-center hover:bg-gray-50 dark:hover:bg-slate-700/60 border-gray-100 dark:border-slate-700 last:border-0 border-b w-full transition-colors"
                  >
                    <button
                      type="button"
                      onclick={() => handleSelectItem(item)}
                      class="flex flex-1 justify-between items-center px-3 py-2 min-w-0 text-sm text-left"
                    >
                      <div class="flex-1 min-w-0">
                        <div
                          class="font-medium text-gray-900 dark:text-cyan-100 truncate"
                        >
                          {item.name}
                        </div>
                        {#if item.location}
                          <div
                            class="text-gray-500 dark:text-cyan-400/70 text-xs truncate"
                          >
                            {item.location}
                          </div>
                        {:else if item.kind === "suggested" && item.country}
                          <div
                            class="text-gray-500 dark:text-cyan-400/70 text-xs truncate"
                          >
                            {item.country}
                          </div>
                        {/if}
                      </div>
                      <span
                        class="ml-2 px-2 py-0.5 rounded-full text-xs font-medium shrink-0 {item.kind ===
                        'implemented'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                          : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'}"
                      >
                        {item.kind === "implemented" ? "Listed" : "Suggested"}
                      </span>
                    </button>
                    {#if item.kind === "suggested" && item.id}
                      <button
                        type="button"
                        onclick={(e) => {
                          e.stopPropagation();
                          handleUpvote(item.id!);
                        }}
                        disabled={item.hasUpvoted || !$session.data || upvotingId === item.id}
                        title={item.hasUpvoted
                          ? "Already upvoted"
                          : !$session.data
                            ? "Sign in to upvote"
                            : "Upvote this suggestion"}
                        class="flex items-center gap-1 px-2.5 py-2 shrink-0 text-xs font-medium transition-colors {item.hasUpvoted
                          ? 'text-emerald-600 dark:text-emerald-400 cursor-default'
                          : 'text-gray-500 dark:text-cyan-400/70 hover:text-orange-600 dark:hover:text-cyan-200'}
                          disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {#if upvotingId === item.id}
                          <span
                            class="inline-block border-2 border-current border-t-transparent rounded-full w-3 h-3 animate-spin"
                          ></span>
                        {:else}
                          <ArrowUp class="w-3.5 h-3.5" />
                        {/if}
                        {item.upvoteCount ?? 0}
                      </button>
                      {#if item.hasUpvoted && item.notifyOnImplementation !== undefined}
                        <label
                          class="flex items-center gap-1 px-1.5 py-1 text-gray-500 dark:text-cyan-400/70 text-xs cursor-pointer select-none shrink-0"
                          title="Get notified when this roaster is added"
                          onclick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={item.notifyOnImplementation}
                            onchange={(e) => {
                              const checked = (e.currentTarget as HTMLInputElement).checked;
                              item.id && handleToggleNotify(item.id, checked);
                            }}
                            class="border-gray-300 dark:border-slate-500 rounded focus:ring-orange-500 dark:focus:ring-emerald-500 w-3 h-3 text-orange-600 dark:text-emerald-500"
                          />
                          <span class="hidden sm:inline">Notify</span>
                        </label>
                      {/if}
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </div>

        <!-- Inline duplicate messaging -->
        {#if implementedMatch}
          <div
            class="flex items-start gap-3 bg-emerald-50 dark:bg-emerald-950/20 px-4 py-3 border border-emerald-200 dark:border-emerald-900 rounded-md text-emerald-800 dark:text-emerald-200"
          >
            <MapPin class="mt-0.5 w-4 h-4 shrink-0" />
            <div class="text-sm">
              <p class="font-medium">Already in our catalogue</p>
              <p class="mt-1">
                <a
                  href="/roasters/{implementedMatch.slug}"
                  class="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-300 hover:underline"
                >
                  View {implementedMatch.name}
                  <ExternalLink class="w-3 h-3" />
                </a>
              </p>
            </div>
          </div>
        {:else if suggestionMatch && !suggestionMatch.hasUpvoted}
          <div
            class="flex items-start gap-3 bg-amber-50 dark:bg-amber-950/20 px-4 py-3 border border-amber-200 dark:border-amber-900 rounded-md text-amber-800 dark:text-amber-200"
          >
            <Lightbulb class="mt-0.5 w-4 h-4 shrink-0" />
            <div class="flex-1 text-sm">
              <p class="font-medium">Already suggested by the community</p>
              <p class="mt-1 text-amber-700 dark:text-amber-300/90">
                Upvote it to help it get added sooner.
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={upvotingId === suggestionMatch.id}
              onclick={() =>
                suggestionMatch.id && handleUpvote(suggestionMatch.id)}
              class="gap-1.5 shrink-0"
            >
              {#if upvotingId === suggestionMatch.id}
                <span
                  class="inline-block border-2 border-current border-t-transparent rounded-full w-3.5 h-3.5 animate-spin"
                ></span>
              {:else}
                <ArrowUp class="w-3.5 h-3.5" />
              {/if}
              {suggestionMatch.upvoteCount}
            </Button>
          </div>
        {:else if suggestionMatch && suggestionMatch.hasUpvoted}
          <div
            class="flex items-start gap-3 bg-amber-50 dark:bg-amber-950/20 px-4 py-3 border border-amber-200 dark:border-amber-900 rounded-md text-amber-800 dark:text-amber-200"
          >
            <Lightbulb class="mt-0.5 w-4 h-4 shrink-0" />
            <div class="flex-1 text-sm">
              <p class="font-medium">Already suggested by the community</p>
              <p class="mt-1 text-amber-700 dark:text-amber-300/90">
                You've upvoted this suggestion.
              </p>
              {#if suggestionMatch.notifyOnImplementation !== null}
                <label
                  class="flex items-center gap-2 mt-2 cursor-pointer select-none"
                >
                  <input
                    type="checkbox"
                    checked={suggestionMatch.notifyOnImplementation}
                    onchange={(e) => {
                      const checked = (e.currentTarget as HTMLInputElement).checked;
                      suggestionMatch.id && handleToggleNotify(suggestionMatch.id, checked);
                    }}
                    class="border-gray-300 dark:border-slate-500 rounded focus:ring-orange-500 dark:focus:ring-emerald-500 w-3.5 h-3.5 text-orange-600 dark:text-emerald-500"
                  />
                  <span class="text-amber-700 dark:text-amber-300/90">
                    Notify me when this roaster is added
                  </span>
                </label>
              {/if}
            </div>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled
              class="gap-1.5 shrink-0"
            >
              <ArrowUp class="w-3.5 h-3.5" />
              {suggestionMatch.upvoteCount}
            </Button>
          </div>
        {/if}

        <!-- Validation issues -->
        {#each submitRoasterSuggestion.fields.name.issues() ?? [] as issue}
          <p class="text-red-600 dark:text-red-400 text-sm">{issue.message}</p>
        {/each}
        {#each submitRoasterSuggestion.fields.website.issues() ?? [] as issue}
          <p class="text-red-600 dark:text-red-400 text-sm">{issue.message}</p>
        {/each}

        <!-- Optional fields (only once a non-duplicate name is typed) -->
        {#if !isDuplicate && typedName.trim()}
          <div class="space-y-2">
            <Label for="roaster-country">
              Country <span class="text-gray-400">(optional)</span>
            </Label>
            <Input
              id="roaster-country"
              name="country"
              bind:value={typedCountry}
              placeholder="e.g. United Kingdom"
              maxlength={100}
              class="bg-white dark:bg-slate-700/60 dark:text-cyan-200"
            />
          </div>

          <div class="space-y-2">
            <Label for="roaster-website">
              Website <span class="text-gray-400">(optional)</span>
            </Label>
            <Input
              id="roaster-website"
              name="website"
              type="url"
              bind:value={typedWebsite}
              placeholder="https://example.com"
              maxlength={500}
              class="bg-white dark:bg-slate-700/60 dark:text-cyan-200"
            />
          </div>

          <div class="flex items-start gap-2.5 pt-1">
            <input
              id="notify-on-implementation"
              type="checkbox"
              bind:checked={notifyOnImplementation}
              class="mt-0.5 border-gray-300 dark:border-slate-500 rounded focus:ring-orange-500 dark:focus:ring-emerald-500 w-4 h-4 text-orange-600 dark:text-emerald-500"
            />
            <Label for="notify-on-implementation" class="font-normal text-sm cursor-pointer">
              Notify me when this roaster is added
            </Label>
            <input
              type="hidden"
              name="notifyOnImplementation"
              value={notifyOnImplementation ? 'true' : 'false'}
            />
          </div>
        {/if}

        <Dialog.Footer>
          <Button
            type="button"
            variant="outline"
            onclick={() => {
              showSuggestDialog = false;
              resetSuggestForm();
            }}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isDuplicate ||
              !typedName.trim() ||
              submitRoasterSuggestion.pending}
            class="gap-2 bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white"
          >
            {#if submitRoasterSuggestion.pending}
              Submitting...
            {:else}
              <Lightbulb class="w-4 h-4" />
              Suggest Roaster
            {/if}
          </Button>
        </Dialog.Footer>
      </form>
    {:else}
      <div class="flex flex-col justify-center items-center gap-4 py-8">
        <div class="bg-orange-50 dark:bg-cyan-900/20 p-4 rounded-full">
          <Lightbulb class="w-8 h-8 text-orange-600 dark:text-cyan-400" />
        </div>
        <p class="px-4 text-gray-600 dark:text-cyan-300/80 text-sm text-center">
          Please sign in to suggest a roaster. This helps us keep spam out and
          lets you track your suggestions.
        </p>
        <Button href="/login" class="w-full sm:w-auto">
          Sign in to continue
        </Button>
      </div>
    {/if}
  </Dialog.Content>
</Dialog.Root>
