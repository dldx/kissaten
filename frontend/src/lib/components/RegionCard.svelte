<script lang="ts">
    import { Button } from "$lib/components/ui/button/index.js";
    import {
        Card,
        CardContent,
        CardHeader,
        CardTitle,
    } from "$lib/components/ui/card/index.js";
    import { MapPin, Warehouse, Coffee } from "lucide-svelte";
    import { normalizeRegionName } from "$lib/utils.js";

    interface Props {
        region: {
            region_name: string;
            bean_count: number;
            farm_count: number;
            is_geocoded: boolean;
        };
        countryCode: string;
    }

    let { region, countryCode }: Props = $props();
    let regionSlug = $derived(normalizeRegionName(region.region_name));
    let displayName = $derived(
        region.is_geocoded ? region.region_name : `${region.region_name} (?)`,
    );
</script>

<Card
    class="flex flex-col bg-white dark:bg-slate-800/80 hover:shadow-lg dark:hover:shadow-emerald-500/20 border-gray-200 dark:border-slate-600 h-full transition-shadow"
>
    <CardHeader class="p-3 sm:p-6 pb-2 sm:pb-3">
        <CardTitle
            class="flex items-center gap-1.5 sm:gap-2 font-semibold text-gray-900 dark:text-cyan-100 text-sm sm:text-lg"
        >
            <MapPin
                class="w-4 h-4 sm:w-5 sm:h-5 inline-block text-orange-500 dark:text-emerald-500"
            />
            {displayName}
        </CardTitle>
    </CardHeader>
    <CardContent
        class="flex flex-col flex-1 p-3 sm:p-6 pt-0 sm:pt-0 pb-3 sm:pb-6"
    >
        <div class="space-y-1.5 sm:space-y-3 mb-3 sm:mb-6">
            <div
                class="flex items-center text-gray-600 dark:text-cyan-300/80 text-[10px] sm:text-sm"
            >
                <Coffee class="mr-1.5 sm:mr-2 w-3 h-3 sm:w-4 sm:h-4" />
                <span
                    >{region.bean_count} Bean{region.bean_count === 1
                        ? ""
                        : "s"}</span
                >
            </div>
            <div
                class="flex items-center text-gray-600 dark:text-cyan-300/80 text-[10px] sm:text-sm"
            >
                <Warehouse class="mr-1.5 sm:mr-2 w-3 h-3 sm:w-4 sm:h-4" />
                <span
                    >{region.farm_count} Farm{region.farm_count === 1
                        ? ""
                        : "s"}</span
                >
            </div>
        </div>

        <div class="mt-auto">
            <Button
                class="w-full h-8 sm:h-10 text-xs sm:text-sm px-2 sm:px-4"
                variant="outline"
                href={`/origins/${countryCode}/${regionSlug}`}
            >
                Explore<span class="hidden sm:inline">&nbsp;Region</span>
            </Button>
        </div>
    </CardContent>
</Card>
