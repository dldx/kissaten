<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import CheckIcon from "lucide-svelte/icons/check";
  import XIcon from "lucide-svelte/icons/x";
  import CheckCheckIcon from "lucide-svelte/icons/check-check";
  import PackageCheckIcon from "lucide-svelte/icons/package-check";
  import { api, type CoffeeBean } from "$lib/api";
  import {
    submitProductReview,
    listProductReviewDecisions,
    type ProductReviewDecision,
  } from "$lib/api/feedback.remote";
  import { formatPrice, slugify } from "$lib/utils";
  import { formatRelative, formatAbsolute } from "$lib/utils/history";
  import { onMount } from "svelte";
  import { toast } from "svelte-sonner";
  import BeanHoverCard from "./BeanHoverCard.svelte";

  // Flagged-for-review queue (tasting kits etc.). Loaded client-side via the
  // public search API using the admin-only `include_unreviewed` flag.
  let reviewItems = $state<CoffeeBean[]>([]);
  let decidedReviews = $state<
    Record<string, { decision: ProductReviewDecision; reviewedAt: string }>
  >({});
  let reviewLoading = $state(false);
  let reviewError = $state("");
  let reviewSubmitting = $state(false);
  let reviewInlineError = $state<Record<string, string>>({});

  // The entity path that a review decision is keyed on — must match exactly
  // what submitProductReview records as entityUrlPath so the decisions map
  // keys line up with the submitted values.
  function entityPathOf(item: CoffeeBean): string {
    return (
      item.bean_url_path ??
      `/roasters/${slugify(item.roaster)}/${item.clean_url_slug ?? item.name}`
    );
  }

  // Derived split: reviewItems stays the full API result (single source of
  // truth); pending/decided are computed from it + decidedReviews.
  const pendingReviewItems = $derived(
    reviewItems.filter((item) => !(entityPathOf(item) in decidedReviews)),
  );
  const decidedReviewItems = $derived(
    reviewItems
      .filter((item) => entityPathOf(item) in decidedReviews)
      .sort((a, b) => {
        const aAt = decidedReviews[entityPathOf(a)]?.reviewedAt ?? "";
        const bAt = decidedReviews[entityPathOf(b)]?.reviewedAt ?? "";
        return bAt.localeCompare(aAt);
      }),
  );

  async function loadReviewQueue() {
    reviewLoading = true;
    reviewError = "";
    try {
      const [res, decisions] = await Promise.all([
        api.search({
          requires_review: true,
          per_page: 50,
          sort_by: "date_added",
          sort_order: "desc",
        }),
        listProductReviewDecisions(),
      ]);
      if (res.success && res.data) {
        reviewItems = res.data;
      } else {
        reviewError = res.message || "Failed to load the review queue.";
      }
      const map: Record<string, { decision: ProductReviewDecision; reviewedAt: string }> =
        {};
      for (const d of decisions) {
        map[d.entityUrlPath] = {
          decision: d.decision,
          reviewedAt: new Date(d.decidedAt).toISOString(),
        };
      }
      decidedReviews = map;
    } catch (err) {
      reviewError =
        err instanceof Error
          ? err.message
          : "Failed to load the review queue.";
    } finally {
      reviewLoading = false;
    }
  }

  onMount(() => {
    loadReviewQueue();
  });

  async function decideReview(
    item: CoffeeBean,
    decision: ProductReviewDecision,
  ) {
    reviewSubmitting = true;
    const key = String(item.id);
    try {
      const entityUrlPath = entityPathOf(item);
      await submitProductReview({
        entityUrlPath,
        entitySlug: item.clean_url_slug ?? "",
        entityName: item.name,
        decision,
      });
      decidedReviews[entityUrlPath] = {
        decision,
        reviewedAt: new Date().toISOString(),
      };
      const { [key]: _removed, ...rest } = reviewInlineError;
      reviewInlineError = rest;
      toast.success(decision === "approved" ? "Approved." : "Rejected.");
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Could not record decision.";
      reviewInlineError = { ...reviewInlineError, [key]: msg };
    } finally {
      reviewSubmitting = false;
    }
  }
</script>

    <!-- ── Flagged for review ───────────────────────────────── -->
    <section id="flagged-review" class="space-y-3 scroll-mt-24">
      <div>
        <h2 class="font-semibold text-xl">Flagged for review</h2>
        <p class="text-muted-foreground text-sm">
          Tasting kits and other products flagged as awaiting an admin decision.
          Approving or rejecting records your decision.
        </p>
      </div>

      {#if reviewLoading}
        <div class="py-8 text-muted-foreground text-center text-sm">
          Loading…
        </div>
      {:else if reviewError}
        <div class="py-8 text-destructive text-center text-sm">
          {reviewError}
        </div>
      {:else if pendingReviewItems.length === 0 && decidedReviewItems.length === 0}
        <Card.Root>
          <Card.Content class="py-12">
            <div
              class="flex flex-col items-center gap-3 text-muted-foreground"
            >
              <CheckCheckIcon class="w-10 h-10" />
              <p class="font-medium">Nothing awaiting review. ✓</p>
            </div>
          </Card.Content>
        </Card.Root>
      {:else}
        {#if pendingReviewItems.length > 0}
          <div class="space-y-2">
            {#each pendingReviewItems as item (item.id)}
              <BeanHoverCard bean={item}>
                {#snippet children({ props })}
                  <Card.Root {...props}>
                    <Card.Content class="pt-6">
                      <div
                        class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
                      >
                        <div class="flex-1 min-w-0 space-y-1">
                          <div class="flex items-center gap-2">
                            {#if item.image_url}
                              <img
                                src={item.image_url}
                                alt=""
                                class="bg-muted w-10 h-10 rounded object-cover shrink-0"
                              />
                            {/if}
                            <PackageCheckIcon
                              class="w-4 h-4 text-muted-foreground shrink-0"
                            />
                            <p class="font-semibold truncate">{item.name}</p>
                            <Badge class="" variant="secondary"
                              >{item.roaster}</Badge
                            >
                          </div>
                          {#if item.price != null}
                            <p class="text-muted-foreground text-sm">
                              {formatPrice(item.price, item.currency)}
                            </p>
                          {/if}
                          <div
                            class="flex flex-wrap gap-x-3 gap-y-0.5 text-muted-foreground text-xs"
                          >
                            {#if item.bean_url_path}
                              <a
                                href={"/roasters" + item.bean_url_path}
                                class="hover:underline"
                              >
                                {item.bean_url_path}
                              </a>
                            {/if}
                            {#if item.url}
                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                class="hover:underline"
                              >
                                Source ↗
                              </a>
                            {/if}
                          </div>
                        </div>

                        <div
                          class="flex flex-wrap gap-2 sm:shrink-0 sm:justify-end"
                        >
                          {#if reviewInlineError[String(item.id)]}
                            <p
                              class="w-full text-destructive text-xs text-end"
                            >
                              {reviewInlineError[String(item.id)]}
                            </p>
                          {/if}
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={reviewSubmitting}
                            onclick={() => decideReview(item, "rejected")}
                          >
                            <XIcon class="mr-1 w-3.5 h-3.5" />
                            Reject
                          </Button>
                          <Button
                            size="sm"
                            disabled={reviewSubmitting}
                            onclick={() => decideReview(item, "approved")}
                          >
                            <CheckIcon class="mr-1 w-3.5 h-3.5" />
                            Approve
                          </Button>
                        </div>
                      </div>
                    </Card.Content>
                  </Card.Root>
                {/snippet}
              </BeanHoverCard>
            {/each}
          </div>
        {:else}
          <Card.Root>
            <Card.Content class="py-12">
              <div
                class="flex flex-col items-center gap-3 text-muted-foreground"
              >
                <CheckCheckIcon class="w-10 h-10" />
                <p class="font-medium">Nothing awaiting review. ✓</p>
              </div>
            </Card.Content>
          </Card.Root>
        {/if}

        {#if decidedReviewItems.length > 0}
          <div class="space-y-2 pt-2">
            <h3 class="font-medium text-sm text-muted-foreground">
              Previously decided
            </h3>
            {#each decidedReviewItems as item (item.id)}
              {#if decidedReviews[entityPathOf(item)]}
                <BeanHoverCard bean={item}>
                  {#snippet children({ props })}
                    <Card.Root {...props} class="opacity-75">
                      <Card.Content class="pt-6">
                        <div
                          class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
                        >
                          <div class="flex-1 min-w-0 space-y-1">
                            <div class="flex items-center gap-2">
                              {#if item.image_url}
                                <img
                                  src={item.image_url}
                                  alt=""
                                  class="bg-muted w-10 h-10 rounded object-cover shrink-0"
                                />
                              {/if}
                              <PackageCheckIcon
                                class="w-4 h-4 text-muted-foreground shrink-0"
                              />
                              <p class="font-semibold truncate">{item.name}</p>
                              <Badge class="" variant="secondary"
                                >{item.roaster}</Badge
                              >
                              <Badge
                                variant={decidedReviews[entityPathOf(item)].decision ===
                                "rejected"
                                  ? "outline"
                                  : "default"}
                                class={
                                  decidedReviews[entityPathOf(item)].decision ===
                                  "rejected"
                                    ? "text-destructive"
                                    : ""
                                }
                              >
                                {decidedReviews[entityPathOf(item)].decision ===
                                "rejected"
                                  ? "Rejected"
                                  : "Approved"}
                              </Badge>
                            </div>
                            {#if item.price != null}
                              <p class="text-muted-foreground text-sm">
                                {formatPrice(item.price, item.currency)}
                              </p>
                            {/if}
                            <div
                              class="flex flex-wrap gap-x-3 gap-y-0.5 text-muted-foreground text-xs"
                            >
                              {#if item.bean_url_path}
                                <a
                                  href={"/roasters" + item.bean_url_path}
                                  class="hover:underline"
                                >
                                  {item.bean_url_path}
                                </a>
                              {/if}
                              {#if item.url}
                                <a
                                  href={item.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  class="hover:underline"
                                >
                                  Source ↗
                                </a>
                              {/if}
                              <span
                                title={formatAbsolute(
                                  decidedReviews[entityPathOf(item)].reviewedAt,
                                )}
                              >
                                decided
                                {formatRelative(
                                  decidedReviews[entityPathOf(item)].reviewedAt,
                                )}
                              </span>
                            </div>
                          </div>

                          <div
                            class="flex flex-wrap gap-2 sm:shrink-0 sm:justify-end"
                          >
                            {#if reviewInlineError[String(item.id)]}
                              <p
                                class="w-full text-destructive text-xs text-end"
                              >
                                {reviewInlineError[String(item.id)]}
                              </p>
                            {/if}
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={reviewSubmitting}
                              onclick={() => decideReview(item, "rejected")}
                            >
                              <XIcon class="mr-1 w-3.5 h-3.5" />
                              Reject
                            </Button>
                            <Button
                              size="sm"
                              disabled={reviewSubmitting}
                              onclick={() => decideReview(item, "approved")}
                            >
                              <CheckIcon class="mr-1 w-3.5 h-3.5" />
                              Approve
                            </Button>
                          </div>
                        </div>
                      </Card.Content>
                    </Card.Root>
                  {/snippet}
                </BeanHoverCard>
              {/if}
            {/each}
          </div>
        {/if}
      {/if}
    </section>