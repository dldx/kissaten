<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { CheckIcon } from "lucide-svelte";
  import BanIcon from "lucide-svelte/icons/ban";
  import RotateCcwIcon from "lucide-svelte/icons/rotate-ccw";
  import {
    listNotABeanReports,
    submitProductReview,
    type NotABeanReportRow,
  } from "$lib/api/feedback.remote";
  import { formatRelative, formatAbsolute } from "$lib/utils/history";
  import { onMount } from "svelte";
  import { toast } from "svelte-sonner";

  // Not-a-bean user reports. Reports do NOT hide the reported product on
  // their own (apply-review-decisions ignores this kind), so this view is
  // where admins triage them: restore a wrongly-reported genuine coffee via
  // an approve decision, or leave it hidden if the report was valid.
  interface ReportGroup {
    entityUrlPath: string;
    entityName: string;
    count: number;
    latestAt: number;
    status: string;
    restored: boolean;
  }

  let reports = $state<NotABeanReportRow[]>([]);
  let restored = $state<Record<string, boolean>>({});
  let loading = $state(false);
  let loadError = $state("");
  let submitting = $state(false);

  const groups = $derived.by(() => {
    const map = new Map<string, ReportGroup>();
    for (const r of reports) {
      const existing = map.get(r.entityUrlPath);
      if (existing) {
        existing.count += 1;
        existing.latestAt = Math.max(existing.latestAt, r.createdAt);
        // A report only stays "new" while no run has acted on any of its rows.
        if (existing.status === "applied") existing.status = "applied";
      } else {
        map.set(r.entityUrlPath, {
          entityUrlPath: r.entityUrlPath,
          entityName: r.entityName || r.entityUrlPath,
          count: 1,
          latestAt: r.createdAt,
          status: r.status,
          restored: restored[r.entityUrlPath] ?? false,
        });
      }
    }
    return [...map.values()];
  });

  const pendingGroups = $derived(
    groups.filter((g) => g.status === "new" && !g.restored),
  );
  const handledGroups = $derived(
    groups
      .filter((g) => g.status !== "new" || g.restored)
      .sort((a, b) => b.latestAt - a.latestAt),
  );

  async function loadReports() {
    loading = true;
    loadError = "";
    try {
      reports = await listNotABeanReports();
    } catch (err) {
      loadError =
        err instanceof Error ? err.message : "Failed to load reports.";
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadReports();
  });

  // A reported product is hidden (requires_review=true). Restoring a genuine
  // coffee records an APPROVED product-review decision for the same entity;
  // `kissaten apply-review-decisions` then un-hides it as usual.
  async function restoreBean(group: ReportGroup) {
    submitting = true;
    try {
      const parts = group.entityUrlPath.split("/").filter(Boolean);
      await submitProductReview({
        entityUrlPath: group.entityUrlPath,
        entitySlug: parts[parts.length - 1] ?? "",
        entityName: group.entityName,
        decision: "approved",
      });
      restored[group.entityUrlPath] = true;
      toast.success(
        "Restore recorded. Run `kissaten apply-review-decisions --update-db` to publish.",
      );
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Could not record restore.",
      );
    } finally {
      submitting = false;
    }
  }
</script>

<!-- ── Not-a-bean reports ──────────────────────────────── -->
<section id="not-a-bean-reports" class="space-y-3 scroll-mt-24">
  <div>
    <h2 class="font-semibold text-xl">Not-a-bean reports</h2>
    <p class="text-muted-foreground text-sm">
      User reports that a product is not a coffee bean (equipment, merch, …).
      Reports never hide a product automatically — review them here and use
      <em>Restore</em> if the report was wrong.
    </p>
  </div>

  {#if loading}
    <div class="py-8 text-muted-foreground text-center text-sm">
      Loading…
    </div>
  {:else if loadError}
    <div class="py-8 text-destructive text-center text-sm">{loadError}</div>
  {:else if groups.length === 0}
    <Card.Root>
      <Card.Content class="py-12">
        <div class="flex flex-col items-center gap-3 text-muted-foreground">
          <BanIcon class="w-10 h-10" />
          <p class="font-medium">No not-a-bean reports. ✓</p>
        </div>
      </Card.Content>
    </Card.Root>
  {:else}
    {#if pendingGroups.length > 0}
      <div class="space-y-2">
        {#each pendingGroups as group (group.entityUrlPath)}
          <Card.Root>
            <Card.Content class="pt-6">
              <div
                class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
              >
                <div class="min-w-0 flex-1 space-y-1">
                  <div class="flex items-center gap-2">
                    <BanIcon class="w-4 h-4 shrink-0 text-muted-foreground" />
                    <p class="truncate font-semibold">{group.entityName}</p>
                    {#if group.count > 1}
                      <Badge class="" variant="secondary">{group.count} reports</Badge>
                    {/if}
                    <Badge variant="outline" class="text-destructive">
                      awaiting review
                    </Badge>
                  </div>
                  <div
                    class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground"
                  >
                    <a
                      href={"/roasters" + group.entityUrlPath}
                      class="hover:underline"
                    >
                      {group.entityUrlPath}
                    </a>
                    <span
                      title={formatAbsolute(new Date(group.latestAt).toISOString())}
                    >
                      reported {formatRelative(new Date(group.latestAt).toISOString())}
                    </span>
                  </div>
                </div>
                <div class="flex shrink-0 flex-wrap gap-2 sm:justify-end">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={submitting}
                    onclick={() => restoreBean(group)}
                  >
                    <RotateCcwIcon class="mr-1 h-3.5 w-3.5" />
                    Restore bean
                  </Button>
                </div>
              </div>
            </Card.Content>
          </Card.Root>
        {/each}
      </div>
    {:else}
      <Card.Root>
        <Card.Content class="py-12">
          <div class="flex flex-col items-center gap-3 text-muted-foreground">
            <CheckIcon class="h-10 w-10" />
            <p class="font-medium">No reports awaiting review. ✓</p>
          </div>
        </Card.Content>
      </Card.Root>
    {/if}

    {#if handledGroups.length > 0}
      <div class="space-y-2 pt-2">
        <h3 class="text-sm font-medium text-muted-foreground">
          Previously handled
        </h3>
        {#each handledGroups as group (group.entityUrlPath)}
          <Card.Root class="opacity-75">
            <Card.Content class="pt-6">
              <div
                class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
              >
                <div class="min-w-0 flex-1 space-y-1">
                  <div class="flex items-center gap-2">
                    <BanIcon class="w-4 h-4 shrink-0 text-muted-foreground" />
                    <p class="truncate font-semibold">{group.entityName}</p>
                    {#if group.count > 1}
                      <Badge class="" variant="secondary">{group.count} reports</Badge>
                    {/if}
                    {#if group.restored}
                      <Badge class="">restore recorded</Badge>
                    {:else}
                      <Badge class="" variant="outline">hidden</Badge>
                    {/if}
                  </div>
                  <div
                    class="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground"
                  >
                    <a
                      href={"/roasters" + group.entityUrlPath}
                      class="hover:underline"
                    >
                      {group.entityUrlPath}
                    </a>
                    <span
                      title={formatAbsolute(new Date(group.latestAt).toISOString())}
                    >
                      reported {formatRelative(new Date(group.latestAt).toISOString())}
                    </span>
                  </div>
                </div>
                {#if !group.restored}
                  <div class="flex shrink-0 flex-wrap gap-2 sm:justify-end">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={submitting}
                      onclick={() => restoreBean(group)}
                    >
                      <RotateCcwIcon class="mr-1 h-3.5 w-3.5" />
                      Restore bean
                    </Button>
                  </div>
                {/if}
              </div>
            </Card.Content>
          </Card.Root>
        {/each}
      </div>
    {/if}
  {/if}
</section>
