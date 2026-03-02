<script lang="ts">
    import type { PageData } from "./$types";
    import LocationLayout from "$lib/components/LocationLayout.svelte";
    import { Button } from "$lib/components/ui/button";
    import { MapPin } from "lucide-svelte";

    let { data }: { data: PageData } = $props();
    const location = $derived(data.location);
</script>

<LocationLayout
    pageContext={data.pageContext}
    extraContent={location.location_type === "region" && location.countries?.length ? countriesSection : undefined}
/>

{#snippet countriesSection()}
    {#if location?.location_type === "region" && location.countries && location.countries.length > 0}
        <div class="mb-8">
            <div
                class="gap-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
            >
                {#each location.countries as country}
                    <a
                        href="/roasted-in/{location.location_slug}/{country.slug}"
                        class="flex flex-col bg-white dark:bg-slate-800/80 hover:shadow-lg dark:hover:shadow-blue-500/10 border border-gray-200 dark:border-slate-600 rounded-lg h-full transition-all"
                    >
                        <!-- Flag Section -->
                        <div
                            class="flex justify-center items-center bg-blue-50/50 dark:bg-blue-900/10 p-3 sm:p-4 rounded-t-lg w-full h-24 sm:h-32"
                        >
                            {#if country.country_code}
                                <iconify-icon
                                    icon={`circle-flags:${country.country_code.toLowerCase()}`}
                                    class="text-[48px] sm:text-[64px]"
                                ></iconify-icon>
                            {/if}
                        </div>

                        <!-- Country Name -->
                        <div class="p-3 sm:p-4 text-center">
                            <h3
                                class="mb-0.5 font-semibold text-gray-900 dark:text-cyan-100 text-sm sm:text-base"
                            >
                                {country.name}
                            </h3>
                            <p
                                class="text-[10px] text-gray-500 dark:text-cyan-400/60 sm:text-xs line-clamp-1"
                            >
                                {location.location_name}
                            </p>
                        </div>

                        <!-- Stats Section -->
                        <div
                            class="flex flex-col flex-1 justify-end p-3 sm:p-4 pt-0 sm:pt-0"
                        >
                            <div class="flex flex-row gap-2 mx-auto text-xs sm:text-sm">
                                <button
                                    onclick={(e) => {
                                        e.preventDefault();
                                        e.stopPropagation();
                                        window.location.href = `/search?roaster_location=${country.country_code}`;
                                    }}
                                    class="flex justify-between items-center hover:underline cursor-pointer"
                                >
                                    <span
                                        class="font-medium text-gray-900 dark:text-cyan-100"
                                    >
                                        {country.total_beans} Bean{country.total_beans !== 1 ? "s" : ""}
                                    </span>
                                </button><span class="text-sm">//</span>
                                <div class="flex justify-between items-center">

                                    <span
                                        class="font-medium text-blue-600 dark:text-cyan-400"
                                    >
                                        {country.roaster_count} Roaster{country.roaster_count !== 1 ? "s" : ""}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div
                            class="flex flex-col flex-1 mt-auto p-3 sm:p-4 pt-0 sm:pt-0"
                        >
                            <div
                                class="flex justify-center items-center gap-1 sm:gap-2 bg-background hover:bg-accent px-2 sm:px-4 border border-input rounded-md w-full h-8 sm:h-10 font-medium text-xs sm:text-sm transition-colors hover:text-accent-foreground"
                            >
                                <MapPin
                                    class="w-3 sm:w-4 h-3 sm:h-4"
                                />
                                <span class="hidden sm:inline"
                                    >Explore</span
                                >
                            </div>
                        </div>
                    </a>
                {/each}
            </div>
        </div>
    {/if}
{/snippet}

<svelte:head>
    <title>Coffee Roasters in {location?.location_name} - Kissaten</title>
    <meta
        name="description"
        content="Explore {location?.statistics
            .roaster_count} coffee roasters in {location?.location_name}. {location
            ?.statistics.available_beans} beans currently available."
    />
</svelte:head>
