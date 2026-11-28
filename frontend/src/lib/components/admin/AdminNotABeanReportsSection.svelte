<script lang="ts">
  import CheckIcon from "lucide-svelte/icons/check";
  import XIcon from "lucide-svelte/icons/x";
  import BanIcon from "lucide-svelte/icons/ban";
  import RotateCcwIcon from "lucide-svelte/icons/rotate-ccw";
  import DatabaseIcon from "lucide-svelte/icons/database";
  import { api, type SearchParams, type CoffeeBean } from "$lib/api";
  import {
    listNotABeanReports,
    resolveFeedback,
    submitProductReview,
    type NotABeanReportRow,
  } from "$lib/api/feedback.remote";
  import { parseBeanPath } from "$lib/utils/beanPath";
  import { formatRelative, formatAbsolute } from "$lib/utils/history";
  import { onMount } from "svelte";
  import { toast } from "svelte-sonner";
  import AdminFlagQueue from "./AdminFlagQueue.svelte";
  import AdminCachedPageViewer from "./AdminCachedPageViewer.svelte";
  import type {
    FlagQueueAction,
    FlagQueueBadge,
    FlagQueueItem,
  } from "./flagQueue";

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
    dismissed: boolean;
  }

  let reports = $state<NotABeanReportRow[]>([]);
  let restored = $state<Record<string, boolean>>({});
  // Locally-resolved groups (status = 'resolved' persisted on the report rows).
  let dismissed = $state<Record<string, boolean>>({});
  // Resolved bean data per entity path, so user-flag rows render with the
  // same thumbnail / price / source-link body as scraper-flag rows.
  let beanByPath = $state<Record<string, CoffeeBean>>({});
  let loading = $state(false);
  let loadError = $state("");
  let submitting = $state(false);

  // Cached-page viewer target (admin-only raw page cache).
  let cacheOpen = $state(false);
  let cacheTarget = $state<{
    roasterSlug: string;
    beanSlug: string;
    beanName: string;
  } | null>(null);

  function openCache(group: ReportGroup) {
    const parsed = parseBeanPath(group.entityUrlPath);
    if (!parsed) {
      toast.error("Could not resolve a roaster/bean path for this report.");
      return;
    }
    const bean = beanByPath[normalizePath(group.entityUrlPath)];
    cacheTarget = {
      roasterSlug: parsed.roasterSlug,
      beanSlug: parsed.beanSlug,
      beanName: bean?.name ?? group.entityName,
    };
    cacheOpen = true;
  }

  $effect(() => {
    if (!cacheOpen) cacheTarget = null;
  });

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
          dismissed: dismissed[r.entityUrlPath] ?? false,
        });
      }
    }
    return [...map.values()];
  });

  // Pending = untouched reports ('new', or 'triaged' by the classify-feedback
  // AI triage); priority heuristic: more reporters and fresher reports first
  // (higher report count = stronger signal).
  const pendingGroups = $derived(
    groups
      .filter(
        (g) =>
          (g.status === "new" || g.status === "triaged") &&
          !g.restored &&
          !g.dismissed,
      )
      .sort((a, b) => b.count - a.count || b.latestAt - a.latestAt),
  );
  const handledGroups = $derived(
    groups
      .filter(
        (g) =>
          (g.status !== "new" && g.status !== "triaged") ||
          g.restored ||
          g.dismissed,
      )
      .sort((a, b) => b.latestAt - a.latestAt),
  );

  // entityUrlPath is recorded from bean.bean_url_path (no "/roasters" prefix),
  // but strip it defensively in case a path ever comes through with it.
  function normalizePath(path: string): string {
    return path.startsWith("/roasters") ? path.slice("/roasters".length) : path;
  }

  async function loadReports() {
    loading = true;
    loadError = "";
    try {
      reports = await listNotABeanReports();

      const paths = [
        ...new Set(
          reports.map((r) => normalizePath(r.entityUrlPath)).filter(Boolean),
        ),
      ];
      if (paths.length > 0) {
        // Resolve full bean data via the backend by-paths endpoint so user-flag
        // rows render like scraper-flag rows. Unresolved (deleted / no longer
        // matching) paths fall back to the report's own entity name.
        const beans = await api.fetchAllBeansByPaths(paths, {
          include_unreviewed: true,
        } as SearchParams);
        const byPath: Record<string, CoffeeBean> = {};
        for (const bean of beans) {
          if (bean.bean_url_path) byPath[bean.bean_url_path] = bean;
        }
        beanByPath = byPath;
      }
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

  // Mark every report for this entity as resolved (valid report: product
  // stays hidden, no restore). Re-fetching report rows isn't needed — the
  // local `dismissed` map moves the group into the handled list immediately.
  async function dismissReport(group: ReportGroup) {
    submitting = true;
    try {
      await resolveFeedback({ entityUrlPath: group.entityUrlPath });
      dismissed[group.entityUrlPath] = true;
      toast.success("Report marked resolved.");
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Could not mark report resolved.",
      );
    } finally {
      submitting = false;
    }
  }

  // Map the report groups onto the shared flag-queue item model.
  const pendingQueueItems = $derived(
    pendingGroups.map((group) => toQueueItem(group, false)),
  );
  const handledQueueItems = $derived(
    handledGroups.map((group) => toQueueItem(group, true)),
  );

  function groupActions(
    group: ReportGroup,
    handled: boolean,
  ): FlagQueueAction[] {
    const actions: FlagQueueAction[] = [
      {
        label: "View cache",
        icon: DatabaseIcon,
        variant: "outline",
        onClick: () => openCache(group),
      },
    ];
    if (handled && (group.restored || group.dismissed)) return actions;
    actions.push({
      label: "Restore bean",
      icon: RotateCcwIcon,
      variant: "outline",
      disabled: submitting,
      onClick: () => restoreBean(group),
    });
    if (!handled) {
      actions.push({
        label: "Dismiss",
        icon: XIcon,
        variant: "ghost",
        disabled: submitting,
        onClick: () => dismissReport(group),
      });
    }
    return actions;
  }

  function toQueueItem(group: ReportGroup, handled: boolean): FlagQueueItem {
    const path = normalizePath(group.entityUrlPath);
    const bean = beanByPath[path] ?? null;

    const badges: FlagQueueBadge[] = [];
    if (bean) badges.push({ label: bean.roaster });
    if (group.count > 1) badges.push({ label: `${group.count} reports` });
    if (handled) {
      badges.push(
        group.restored
          ? { label: "restore recorded" }
          : group.dismissed
            ? { label: "resolved" }
            : { label: "hidden", variant: "outline" },
      );
    } else {
      badges.push({
        label: "awaiting review",
        variant: "outline",
        className: "text-destructive",
      });
    }

    return {
      id: `report-${group.entityUrlPath}`,
      bean,
      displayName: group.entityName,
      icon: BanIcon,
      pathLabel: bean?.bean_url_path ?? path,
      badges,
      caption: `reported ${formatRelative(new Date(group.latestAt).toISOString())}`,
      captionTitle: formatAbsolute(new Date(group.latestAt).toISOString()),
      actions: groupActions(group, handled),
    };
  }
</script>

<AdminFlagQueue
  sectionId="not-a-bean-reports"
  title="Not-a-bean reports"
  description="User reports that a product is not a coffee bean (equipment, merch, …). Reports never hide a product automatically — review them here and use Restore if the report was wrong."
  {loading}
  error={loadError}
  pendingItems={pendingQueueItems}
  handledItems={handledQueueItems}
  handledTitle="Previously handled"
  emptyIcon={BanIcon}
  emptyText="No not-a-bean reports. ✓"
  pendingEmptyIcon={CheckIcon}
  pendingEmptyText="No reports awaiting review. ✓"
/>

<AdminCachedPageViewer
  bind:open={cacheOpen}
  roasterSlug={cacheTarget?.roasterSlug ?? ""}
  beanSlug={cacheTarget?.beanSlug ?? ""}
  beanName={cacheTarget?.beanName ?? ""}
/>
