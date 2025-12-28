<script lang="ts">
    import { pwaState } from "$lib/pwa-install.svelte";
    import { Button } from "$lib/components/ui/button";
    import { X, Download } from "lucide-svelte";
    import { fade, slide } from "svelte/transition";
    import { toast } from "svelte-sonner";

    let { onDismiss }: { onDismiss: () => void } = $props();

    function handleInstall() {
        pwaState.install();
        onDismiss();
    }

    function handleDismiss() {
        pwaState.reject();
        onDismiss();
        toast.info(
            "No problem! You can still install Kissaten later from the menu.",
            {
                duration: 5000,
            },
        );
    }
</script>

{#if pwaState.isInstallable && !pwaState.isRejected}
    <div
        transition:slide={{ axis: "y" }}
        class="fixed bottom-4 left-4 right-4 z-[100] sm:hidden"
    >
        <div
            class="bg-card text-card-foreground border shadow-lg rounded-xl p-4 flex flex-col gap-3"
        >
            <div class="flex justify-between items-start">
                <div class="flex items-center gap-3">
                    <div class="bg-primary/10 p-2 rounded-lg text-primary">
                        <Download class="w-6 h-6" />
                    </div>
                    <div>
                        <h3 class="font-bold text-lg">Add to Home Screen</h3>
                        <p class="text-sm text-muted-foreground">
                            Install Kissaten for a better experience
                        </p>
                    </div>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onclick={handleDismiss}
                    class="-mr-2 -mt-2"
                >
                    <X class="w-5 h-5" />
                </Button>
            </div>

            <div class="flex gap-2 w-full">
                <Button class="flex-1" onclick={handleInstall}>
                    Install Now
                </Button>
                <Button
                    variant="outline"
                    class="flex-1"
                    onclick={handleDismiss}
                >
                    Maybe Later
                </Button>
            </div>
        </div>
    </div>
{/if}
