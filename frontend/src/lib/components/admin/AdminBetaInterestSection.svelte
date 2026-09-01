<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import * as Table from "$lib/components/ui/table/index.js";
  import CheckIcon from "lucide-svelte/icons/check";
  import XIcon from "lucide-svelte/icons/x";
  import CheckCheckIcon from "lucide-svelte/icons/check-check";
  import {
    listBetaInterest,
    approveBetaTester,
    declineBetaTester,
  } from "$lib/api/admin.remote";
  import { formatRelative, formatAbsolute } from "$lib/utils/history";
  import { toast } from "svelte-sonner";

  const betaInterest = $derived(listBetaInterest());

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
</script>

    <!-- ── Beta Interest queue ───────────────────────────────── -->
    <section id="beta-interest" class="space-y-3 scroll-mt-24">
      <div>
        <h2 class="font-semibold text-xl">Beta Program Interest</h2>
        <p class="text-muted-foreground text-sm">
          Users who asked to join the beta program. Approving flips
          <code class="bg-muted px-1 rounded">isBetaAllowed</code> on and clears their
          interest flag.
        </p>
      </div>

      {#await betaInterest}
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
                    <Table.Cell class="text-muted-foreground"
                      >{row.email}</Table.Cell
                    >
                    <Table.Cell>
                      <span title={formatAbsolute(row.updatedAt)}>
                        {formatRelative(row.updatedAt)}
                      </span>
                    </Table.Cell>
                    <Table.Cell class="text-end">
                      <div class="flex justify-end gap-2">
                        <form
                          {...declineBetaTester
                            .for(row.id)
                            .enhance(async ({ submit }) => {
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
                          {...approveBetaTester
                            .for(row.id)
                            .enhance(async ({ submit }) => {
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