<script lang="ts">
  import CheckIcon from "lucide-svelte/icons/check";
  import XIcon from "lucide-svelte/icons/x";
  import PackageCheckIcon from "lucide-svelte/icons/package-check";
  import { api, type CoffeeBean } from "$lib/api";
  import {
    submitProductReview,
    listProductReviewDecisions,
    type ProductReviewDecision,
  } from "$lib/api/feedback.remote";
  import { slugify } from "$lib/utils";
  import { formatRelative, formatAbsolute } from "$lib/utils/history";
  import { onMount } from "svelte";
  import { toast } from "svelte-sonner";
  import AdminFlagQueue from "./AdminFlagQueue.svelte";
  import type { FlagQueueBadge, FlagQueueItem } from "./flagQueue";

  // Flagged-for-review queue (tasting kits etc.). Loaded client-side via the
  // public search API using the `requires_review` filter.
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
      const map: Record<
        string,
        { decision: ProductReviewDecision; reviewedAt: string }
      > = {};
      for (const d of decisions) {
        map[d.entityUrlPath] = {
          decision: d.decision,
          reviewedAt: new Date(d.decidedAt).toISOString(),
        };
      }
      decidedReviews = map;
    } catch (err) {
      reviewError =
        err instanceof Error ? err.message : "Failed to load the review queue.";
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

  // Map the review queue's bean rows onto the shared flag-queue item model.
  const pendingQueueItems = $derived(
    pendingReviewItems.map((item) => toQueueItem(item, false)),
  );
  const handledQueueItems = $derived(
    decidedReviewItems.map((item) => toQueueItem(item, true)),
  );

  function decisionBadge(decision: ProductReviewDecision): FlagQueueBadge {
    return {
      label: decision === "rejected" ? "Rejected" : "Approved",
      variant: decision === "rejected" ? "outline" : "default",
      className: decision === "rejected" ? "text-destructive" : "",
    };
  }

  function toQueueItem(item: CoffeeBean, handled: boolean): FlagQueueItem {
    const path = entityPathOf(item);
    const decision = decidedReviews[path]?.decision;
    return {
      id: `review-${item.id}`,
      bean: item,
      displayName: item.name,
      icon: PackageCheckIcon,
      pathLabel: item.bean_url_path ?? path,
      badges: [
        { label: item.roaster },
        ...(handled && decision ? [decisionBadge(decision)] : []),
      ],
      caption:
        handled && decision
          ? `decided ${formatRelative(decidedReviews[path].reviewedAt)}`
          : undefined,
      captionTitle:
        handled && decision
          ? formatAbsolute(decidedReviews[path].reviewedAt)
          : undefined,
      inlineError: reviewInlineError[String(item.id)],
      actions: [
        {
          label: "Reject",
          icon: XIcon,
          variant: "outline",
          disabled: reviewSubmitting,
          onClick: () => decideReview(item, "rejected"),
        },
        {
          label: "Approve",
          icon: CheckIcon,
          disabled: reviewSubmitting,
          onClick: () => decideReview(item, "approved"),
        },
      ],
    };
  }
</script>

<AdminFlagQueue
  sectionId="flagged-review"
  title="Flagged for review"
  description="Tasting kits and other products flagged as awaiting an admin decision. Approving or rejecting records your decision."
  loading={reviewLoading}
  error={reviewError}
  pendingItems={pendingQueueItems}
  handledItems={handledQueueItems}
  handledTitle="Previously decided"
/>
