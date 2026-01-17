<script lang="ts">
    import { Button } from "$lib/components/ui/button/index.js";
    import {
        Card,
        CardContent,
        CardHeader,
        CardTitle,
    } from "$lib/components/ui/card/index.js";
    import { MapPin, Warehouse, Users } from "lucide-svelte";
    import type { OriginSearchResult } from "$lib/originsApi.js";
    import "iconify-icon";

    interface Props {
        result: OriginSearchResult;
    }

    let { result }: Props = $props();

    function getHref() {
        if (result.type === "country") {
            return `/origins/${result.country_code}`;
        } else if (result.type === "region") {
            const region = result.region_slug || "unknown-region";
            return `/origins/${result.country_code}/${region}`;
        } else {
            const region = result.region_slug || "unknown-region";
            return `/origins/${result.country_code}/${region}/${result.farm_slug}`;
        }
    }
</script>

<Card
    class="flex flex-col bg-white dark:bg-slate-800/80 hover:shadow-lg transition-all h-full border
    {result.type === 'country'
        ? ' border-gray-200 dark:border-slate-600 dark:hover:shadow-blue-500/10'
        : result.type === 'region'
          ? ' border-gray-200 dark:border-slate-600 dark:hover:shadow-red-500/10'
          : ' border-gray-200 dark:border-slate-600 dark:hover:shadow-amber-500/10'}"
>
    <CardHeader class="p-0">
        <div
            class="flex justify-center items-center p-3 sm:p-4 rounded-t-lg w-full h-24 sm:h-32 relative
            {result.type === 'country'
                ? 'bg-blue-50/50 dark:bg-blue-900/10'
                : result.type === 'region'
                  ? 'bg-red-50/50 dark:bg-red-900/10'
                  : 'bg-amber-50/50 dark:bg-amber-900/10'}"
        >
            <iconify-icon
                icon={`circle-flags:${result.country_code.toLowerCase()}`}
                class="text-[48px] sm:text-[64px]"
            ></iconify-icon>

            {#if result.type !== "country"}
                <div
                    class="top-1 sm:top-2 right-1 sm:right-2 absolute px-1.5 sm:px-2 py-0.5 sm:py-1 rounded font-medium text-[9px] sm:text-xs uppercase tracking-wider
                {result.type === 'region'
                        ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                        : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'}"
                >
                    {result.type}
                </div>
            {/if}
        </div>

        <div class="p-3 sm:p-4 text-center">
            <CardTitle
                class="mb-0.5 font-semibold text-gray-900 dark:text-cyan-100 text-sm sm:text-base"
            >
                {result.name}
            </CardTitle>
            <p
                class="text-gray-500 dark:text-cyan-400/60 text-[10px] sm:text-xs line-clamp-1"
            >
                {result.type === "country"
                    ? result.country_code
                    : result.type === "region"
                      ? result.country_name
                      : `${result.region_name}${result.region_name ? ", " : ""}${result.country_name}`}
            </p>
        </div>
    </CardHeader>
    <CardContent class="flex flex-col flex-1 p-3 sm:p-4 pt-0 sm:pt-0">
        <div class="mt-auto">
            <Button
                class="w-full h-8 sm:h-10 text-xs sm:text-sm px-2 sm:px-4"
                variant="outline"
                href={getHref()}
            >
                {#if result.type === "country"}
                    <MapPin class="mr-1 sm:mr-2 w-3 h-3 sm:w-4 sm:h-4" />
                {:else if result.type === "region"}
                    <Warehouse class="mr-1 sm:mr-2 w-3 h-3 sm:w-4 sm:h-4" />
                {:else}
                    <Users class="mr-1 sm:mr-2 w-3 h-3 sm:w-4 sm:h-4" />
                {/if}
                <span class="hidden sm:inline">Explore&nbsp;</span>
                {result.bean_count} Bean{result.bean_count === 1 ? "" : "s"}
            </Button>
        </div>
    </CardContent>
</Card>
