<script lang="ts">
    import { Globe, MapPin, Warehouse } from "lucide-svelte";
    import { normalizeRegionName, normalizeFarmName } from "$lib/utils.js";
    import * as Breadcrumb from "$lib/components/ui/breadcrumb";

    interface Props {
        countryCode?: string;
        countryName?: string;
        regionName?: string;
        farmName?: string;
    }

    let { countryCode, countryName, regionName, farmName }: Props = $props();

    // Computed slugs for navigation
    let regionSlug = $derived(
        regionName ? normalizeRegionName(regionName) : "",
    );
    let farmSlug = $derived(farmName ? normalizeFarmName(farmName) : "");
</script>

<Breadcrumb.Root class="mb-6">
    <Breadcrumb.List>
        <Breadcrumb.Item>
            <Breadcrumb.Link href="/origins">Origins</Breadcrumb.Link>
        </Breadcrumb.Item>

        {#if countryCode}
            <Breadcrumb.Separator />
            <Breadcrumb.Item>
                <Breadcrumb.Link href="/origins/{countryCode}">
                    {countryName || countryCode}
                </Breadcrumb.Link>
            </Breadcrumb.Item>
        {/if}

        {#if regionName}
            <Breadcrumb.Separator />
            <Breadcrumb.Item>
                <Breadcrumb.Link href="/origins/{countryCode}/{regionSlug}">
                    {regionName}
                </Breadcrumb.Link>
            </Breadcrumb.Item>
        {/if}

        {#if farmName}
            <Breadcrumb.Separator />
            <Breadcrumb.Item>
                <Breadcrumb.Page>
                    {farmName}
                </Breadcrumb.Page>
            </Breadcrumb.Item>
        {/if}
    </Breadcrumb.List>
</Breadcrumb.Root>
