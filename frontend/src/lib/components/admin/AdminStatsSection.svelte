<script lang="ts">
  import * as Card from "$lib/components/ui/card/index.js";
  import UsersIcon from "lucide-svelte/icons/users";
  import FlaskConicalIcon from "lucide-svelte/icons/flask-conical";
  import MailIcon from "lucide-svelte/icons/mail";
  import CoffeeIcon from "lucide-svelte/icons/coffee";
  import { getAdminStats } from "$lib/api/admin.remote";

  const stats = $derived(getAdminStats());
</script>

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
          {s.activeBetaTesters.toLocaleString()} active beta tester{s.activeBetaTesters ===
          1
            ? ""
            : "s"} (isBetaAllowed + betaEnabled).
        </p>
      {:catch}
        <div class="py-8 text-destructive text-center text-sm">
          Failed to load stats.
        </div>
      {/await}
    </section>