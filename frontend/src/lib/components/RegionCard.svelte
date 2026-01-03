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
        };
        countryCode: string;
    }

    let { region, countryCode }: Props = $props();
    let regionSlug = $derived(normalizeRegionName(region.region_name));
</script>

<Card
    class="flex flex-col bg-white dark:bg-slate-800/80 hover:shadow-lg dark:hover:shadow-emerald-500/20 border-gray-200 dark:border-slate-600 transition-shadow h-full"
>
    <CardHeader>
        <CardTitle
            class="flex items-center gap-2 font-semibold text-gray-900 dark:text-cyan-100 text-lg"
        >
            <MapPin class="w-5 h-5 text-orange-500 dark:text-emerald-500" />
            {region.region_name}
        </CardTitle>
    </CardHeader>
    <CardContent class="flex flex-col flex-1 pb-6">
        <div class="space-y-3 mb-6">
            <div
                class="flex items-center text-gray-600 dark:text-cyan-300/80 text-sm"
            >
                <Coffee class="mr-2 w-4 h-4" />
                <span
                    >{region.bean_count} Bean{region.bean_count === 1
                        ? ""
                        : "s"}</span
                >
            </div>
            <div
                class="flex items-center text-gray-600 dark:text-cyan-300/80 text-sm"
            >
                <Warehouse class="mr-2 w-4 h-4" />
                <span
                    >{region.farm_count} Farm{region.farm_count === 1
                        ? ""
                        : "s"}</span
                >
            </div>
        </div>

        <div class="mt-auto">
            <Button
                class="w-full"
                variant="outline"
                href={`/origins/${countryCode}/${regionSlug}`}
            >
                Explore Region
            </Button>
        </div>
    </CardContent>
</Card>
