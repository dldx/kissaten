<script lang="ts">
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { Separator } from "$lib/components/ui/separator/index.js";
  import ShieldCheckIcon from "lucide-svelte/icons/shield-check";
  import AdminStatsSection from "$lib/components/admin/AdminStatsSection.svelte";
  import AdminBetaInterestSection from "$lib/components/admin/AdminBetaInterestSection.svelte";
  import AdminRoasterSuggestionsSection from "$lib/components/admin/AdminRoasterSuggestionsSection.svelte";
  import AdminReviewQueueSection from "$lib/components/admin/AdminReviewQueueSection.svelte";
  import AdminUsersSection from "$lib/components/admin/AdminUsersSection.svelte";

  let { data } = $props();
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
        href="#flagged-review"
        class="hover:bg-muted px-3 py-1.5 rounded-md transition-colors"
      >
        Flagged for Review
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
    <AdminStatsSection />
    <Separator />
    <AdminBetaInterestSection />
    <Separator />
    <AdminRoasterSuggestionsSection roasters={data.allRoasters ?? []} />
    <Separator />
    <AdminReviewQueueSection />
    <Separator />
    <AdminUsersSection />
  </div>
</div>