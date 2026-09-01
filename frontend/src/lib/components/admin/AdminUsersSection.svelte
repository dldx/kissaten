<script lang="ts">
  import { Input } from "$lib/components/ui/input/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import * as Table from "$lib/components/ui/table/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import SearchIcon from "lucide-svelte/icons/search";
  import ShieldCheckIcon from "lucide-svelte/icons/shield-check";
  import FlaskConicalIcon from "lucide-svelte/icons/flask-conical";
  import MailIcon from "lucide-svelte/icons/mail";
  import InboxIcon from "lucide-svelte/icons/inbox";
  import { listAllUsers } from "$lib/api/admin.remote";
  import { formatRelative, formatAbsolute } from "$lib/utils/history";

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
              r.role.toLowerCase().includes(search),
          )
        : rows,
    );
  });
</script>

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
                    <Table.Cell class="text-muted-foreground"
                      >{row.email}</Table.Cell
                    >
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
                        <Badge class="" variant="secondary"
                          >Approved · off</Badge
                        >
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