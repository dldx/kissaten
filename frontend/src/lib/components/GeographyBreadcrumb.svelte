<script lang="ts">
    import {
        ChevronRight,
        Home,
        Globe,
        MapPin,
        Warehouse,
    } from "lucide-svelte";
    import { normalizeRegionName, normalizeFarmName } from "$lib/utils.js";

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

<nav class="flex mb-6 text-sm" aria-label="Breadcrumb">
    <ol class="flex items-center space-x-1 md:space-x-3">
        <li class="inline-flex items-center">
            <a
                href="/"
                class="inline-flex items-center text-gray-700 hover:text-orange-600 dark:text-gray-400 dark:hover:text-emerald-400"
            >
                <Home class="mr-2 w-4 h-4" />
                Home
            </a>
        </li>

        <li>
            <div class="flex items-center">
                <ChevronRight class="w-4 h-4 text-gray-400" />
                <a
                    href="/countries"
                    class="ml-1 md:ml-2 text-gray-700 hover:text-orange-600 dark:text-gray-400 dark:hover:text-emerald-400 font-medium"
                >
                    Origins
                </a>
            </div>
        </li>

        {#if countryCode}
            <li>
                <div class="flex items-center">
                    <ChevronRight class="w-4 h-4 text-gray-400" />
                    <a
                        href="/origins/{countryCode}"
                        class="ml-1 md:ml-2 text-gray-700 hover:text-orange-600 dark:text-gray-400 dark:hover:text-emerald-400 font-medium"
                    >
                        <Globe class="mr-1 inline-block w-3 h-3" />
                        {countryName || countryCode}
                    </a>
                </div>
            </li>
        {/if}

        {#if regionName}
            <li>
                <div class="flex items-center">
                    <ChevronRight class="w-4 h-4 text-gray-400" />
                    <a
                        href="/origins/{countryCode}/{regionSlug}"
                        class="ml-1 md:ml-2 text-gray-700 hover:text-orange-600 dark:text-gray-400 dark:hover:text-emerald-400 font-medium"
                    >
                        <MapPin class="mr-1 inline-block w-3 h-3" />
                        {regionName}
                    </a>
                </div>
            </li>
        {/if}

        {#if farmName}
            <li>
                <div class="flex items-center">
                    <ChevronRight class="w-4 h-4 text-gray-400" />
                    <span
                        class="ml-1 md:ml-2 text-gray-500 dark:text-gray-500 font-medium text-sm"
                    >
                        <Warehouse class="mr-1 inline-block w-3 h-3" />
                        {farmName}
                    </span>
                </div>
            </li>
        {/if}
    </ol>
</nav>
