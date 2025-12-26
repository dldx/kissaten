<script lang="ts">
    import { Button } from "$lib/components/ui/button/index.js";
    import { Bookmark, BookmarkCheck } from "lucide-svelte";
    import {
        saveBean,
        unsaveBean,
        checkBeanSaved,
    } from "$lib/api/vault.remote";
    import { api } from "$lib/api";
    import "iconify-icon";

    interface Props {
        bean: any; // Using any for flexibility or specific CoffeeBean type if available
        class?: string;
    }

    let { bean, class: className = "" }: Props = $props();

    let isSaving = $state(false);
    const beanUrlPath = $derived(
        bean.bean_url_path || api.getBeanUrlPath(bean),
    );
    const savedStatusQuery = $derived(checkBeanSaved(beanUrlPath));

    async function handleSaveToggle() {
        if (isSaving) return;
        isSaving = true;

        try {
            const status = await savedStatusQuery;

            if (status.saved && status.savedBeanId) {
                await unsaveBean({ savedBeanId: status.savedBeanId });
            } else {
                await saveBean({
                    beanUrlPath,
                    notes: "",
                });
            }

            // Refresh the saved status query
            savedStatusQuery.refresh();
        } catch (error) {
            console.error("Failed to toggle save status:", error);
        } finally {
            // Small delay to prevent flicker and show the interaction
            setTimeout(() => {
                isSaving = false;
            }, 400);
        }
    }
</script>

{#await savedStatusQuery then status}
    <Button
        variant="ghost"
        size="icon"
        onclick={handleSaveToggle}
        disabled={isSaving}
        class={`relative group shrink-0 transition-all duration-300 hover:bg-cyan-500/10 ${className}`}
        title={status.saved ? "Remove from vault" : "Save to vault"}
    >
        <div class="relative flex items-center justify-center w-full h-full">
            {#if isSaving}
                <div
                    class="absolute inset-0 flex items-center justify-center animate-in fade-in scale-in duration-300"
                >
                    <iconify-icon
                        icon="line-md:loading-twotone-loop"
                        class="w-5 h-5 text-primary"
                    ></iconify-icon>
                </div>
            {/if}

            <div
                class={`transition-all duration-300 ${isSaving ? "opacity-0 scale-75" : "opacity-100 scale-100"}`}
            >
                {#if status.saved}
                    <BookmarkCheck
                        class="fill-primary text-primary w-5 h-5 transition-transform group-hover:scale-110 drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]"
                    />
                {:else}
                    <Bookmark
                        class="w-5 h-5 transition-transform group-hover:scale-110 group-hover:text-primary"
                    />
                {/if}
            </div>
        </div>
    </Button>
{:catch}
    <Button
        variant="ghost"
        size="icon"
        disabled
        class="text-red-500 opacity-50"
        title="Status unavailable"
    >
        <Bookmark class="w-5 h-5" />
    </Button>
{/await}

<style>
    /* Custom animations if needed beyond tailwind */
</style>
