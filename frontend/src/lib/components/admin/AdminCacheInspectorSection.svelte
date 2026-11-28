<script lang="ts">
  import * as Card from "$lib/components/ui/card/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import DatabaseIcon from "lucide-svelte/icons/database";
  import { parseBeanPath } from "$lib/utils/beanPath";
  import AdminCachedPageViewer from "./AdminCachedPageViewer.svelte";

  let pathInput = $state("");
  let roasterInput = $state("");
  let beanInput = $state("");
  let validationError = $state("");

  let cacheOpen = $state(false);
  let cacheTarget = $state<{
    roasterSlug: string;
    beanSlug: string;
    beanName: string;
  } | null>(null);

  $effect(() => {
    if (!cacheOpen) cacheTarget = null;
  });

  function openViewer() {
    validationError = "";

    const path = pathInput.trim();
    let parsed = path ? parseBeanPath(path) : null;

    // Fall back to the separate roaster/bean fields when no path is given.
    if (!path) {
      const roaster = roasterInput.trim();
      const bean = beanInput.trim();
      if (!roaster && !bean) {
        validationError =
          "Enter a bean path like /roaster/bean, or both slugs below.";
        return;
      }
      if (!roaster || !bean) {
        validationError = "Enter both the roaster slug and the bean slug.";
        return;
      }
      if (
        roaster.includes("/") ||
        bean.includes("/") ||
        /\s/.test(roaster) ||
        /\s/.test(bean)
      ) {
        validationError = "Slugs cannot contain slashes or spaces.";
        return;
      }
      parsed = {
        roasterSlug: roaster,
        beanSlug: bean,
        path: `/${roaster}/${bean}`,
      };
    }

    if (!parsed) {
      validationError =
        "Could not parse that path. Use the form /roaster/bean (a full Kissaten URL also works).";
      return;
    }

    cacheTarget = {
      roasterSlug: parsed.roasterSlug,
      beanSlug: parsed.beanSlug,
      beanName: "",
    };
    cacheOpen = true;
  }

  function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    openViewer();
  }
</script>

<section id="cache-inspector" class="space-y-3 scroll-mt-24">
  <div>
    <h2 class="font-semibold text-xl">Cache inspector</h2>
    <p class="text-muted-foreground text-sm">
      Open the raw cached page and screenshots for any bean, even when it is not
      currently in a review queue.
    </p>
  </div>

  <Card.Root>
    <Card.Content class="space-y-4 pt-6">
      <form class="space-y-4" onsubmit={handleSubmit}>
        <div class="space-y-1.5 max-w-xl">
          <label class="font-medium text-sm" for="cache-bean-path"
            >Bean path</label
          >
          <Input
            id="cache-bean-path"
            placeholder="/roaster/bean"
            bind:value={pathInput}
          />
          <p class="text-muted-foreground text-xs">
            Paste a <code>bean_url_path</code> like
            <code>/kaffer_ven/ethiopia-guji</code>. A full Kissaten URL also
            works.
          </p>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div class="space-y-1.5">
            <label class="font-medium text-sm" for="cache-roaster-slug"
              >Roaster slug</label
            >
            <Input
              id="cache-roaster-slug"
              placeholder="kaffer_ven"
              bind:value={roasterInput}
            />
          </div>
          <div class="space-y-1.5">
            <label class="font-medium text-sm" for="cache-bean-slug"
              >Bean slug</label
            >
            <Input
              id="cache-bean-slug"
              placeholder="ethiopia-guji"
              bind:value={beanInput}
            />
          </div>
          <Button type="submit" class="sm:mb-0">
            <DatabaseIcon class="mr-1 w-4 h-4" />
            Open cache viewer
          </Button>
        </div>

        {#if validationError}
          <p class="text-destructive text-sm">{validationError}</p>
        {/if}
      </form>
    </Card.Content>
  </Card.Root>
</section>

<AdminCachedPageViewer
  bind:open={cacheOpen}
  roasterSlug={cacheTarget?.roasterSlug ?? ""}
  beanSlug={cacheTarget?.beanSlug ?? ""}
  beanName={cacheTarget?.beanName ?? ""}
/>
