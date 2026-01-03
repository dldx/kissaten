<script lang="ts">
    import { Button } from "$lib/components/ui/button/index.js";
    import {
        Card,
        CardContent,
        CardHeader,
        CardTitle,
    } from "$lib/components/ui/card/index.js";
    import { Warehouse, User, Coffee, ArrowUpCircle } from "lucide-svelte";
    import { normalizeFarmName } from "$lib/utils.js";

    interface Props {
        farm: {
            farm_name: string;
            producer_name: string | null;
            bean_count: number;
            avg_elevation: number | null;
        };
        countryCode: string;
        regionSlug: string;
    }

    let { farm, countryCode, regionSlug }: Props = $props();
    let farmSlug = $derived(normalizeFarmName(farm.farm_name));
</script>

<Card
    class="flex flex-col bg-white dark:bg-slate-800/80 hover:shadow-lg dark:hover:shadow-emerald-500/20 border-gray-200 dark:border-slate-600 transition-shadow h-full"
>
    <CardHeader>
        <CardTitle
            class="flex items-center gap-2 font-semibold text-gray-900 dark:text-cyan-100 text-lg"
        >
            <Warehouse class="w-5 h-5 text-orange-500 dark:text-emerald-500" />
            {farm.farm_name}
        </CardTitle>
    </CardHeader>
    <CardContent class="flex flex-col flex-1 pb-6">
        <div class="space-y-3 mb-6">
            {#if farm.producer_name}
                <div
                    class="flex items-center text-gray-600 dark:text-cyan-300/80 text-sm"
                >
                    <User class="mr-2 w-4 h-4" />
                    <span class="line-clamp-1">{farm.producer_name}</span>
                </div>
            {/if}
            <div
                class="flex items-center text-gray-600 dark:text-cyan-300/80 text-sm"
            >
                <Coffee class="mr-2 w-4 h-4" />
                <span
                    >{farm.bean_count} Bean{farm.bean_count === 1
                        ? ""
                        : "s"}</span
                >
            </div>
            {#if farm.avg_elevation}
                <div
                    class="flex items-center text-gray-600 dark:text-cyan-300/80 text-sm"
                >
                    <ArrowUpCircle class="mr-2 w-4 h-4" />
                    <span>{Math.round(farm.avg_elevation)}m</span>
                </div>
            {/if}
        </div>

        <div class="mt-auto">
            <Button
                class="w-full"
                variant="outline"
                href={`/origins/${countryCode}/${regionSlug}/${farmSlug}`}
            >
                View Farm
            </Button>
        </div>
    </CardContent>
</Card>
