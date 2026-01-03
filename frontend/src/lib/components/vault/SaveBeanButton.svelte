<script lang="ts">
    import { Button } from "$lib/components/ui/button/index.js";
    import { Bookmark, BookmarkCheck } from "lucide-svelte";
    import LoadingIcon from "virtual:icons/line-md/loading-twotone-loop";
    import {
        saveBean,
        unsaveBean,
        checkBeanSaved,
    } from "$lib/api/vault.remote";
    import { api } from "$lib/api";
    import { toast } from "svelte-sonner";
    import { goto } from "$app/navigation";
    import { authClient } from "$lib/auth-client";

    interface Props {
        bean: any; // Using any for flexibility or specific CoffeeBean type if available
        notes?: string;
        class?: string;
        onSave?: () => void; // Callback when bean is saved
        onUnsave?: () => void; // Callback when bean is unsaved
    }

    let { bean, notes, class: className = "", onSave, onUnsave }: Props = $props();

    let isSaving = $state(false);
    const session = authClient.useSession();
    const beanUrlPath = $derived(
        bean?.bean_url_path || api.getBeanUrlPath(bean),
    );
    const savedStatusQuery = $derived(checkBeanSaved(beanUrlPath));

    async function performUnsave(savedBeanId: string) {
        if (isSaving) return;
        isSaving = true;

        // Capture current notes for possible undo
        const notesToRestore = notes;

        try {
            await unsaveBean({ savedBeanId });
            savedStatusQuery.refresh();
            toast.success("Bean removed from vault", {
                action: {
                    label: "Undo",
                    onClick: async () => {
                        try {
                            isSaving = true;
                            await saveBean({
                                beanUrlPath,
                                notes: notesToRestore || "",
                            });
                            savedStatusQuery.refresh();
                            onSave?.(); // Call callback
                            toast.success("Restored bean and notes");
                        } catch (e) {
                            console.error("Failed to restore bean:", e);
                            toast.error("Failed to restore bean");
                        } finally {
                            isSaving = false;
                        }
                    },
                },
            });
            onUnsave?.(); // Call callback
        } catch (error) {
            console.error("Failed to unsave bean:", error);
            toast.error("Failed to remove bean");
        } finally {
            setTimeout(() => {
                isSaving = false;
            }, 400);
        }
    }

    async function handleSaveToggle() {
        if (isSaving) return;

        // Check if user is authenticated
        if (!$session.data) {
            toast.info("Sign in to save beans", {
                description: "Create an account or log in to save beans to your vault.",
                action: {
                    label: "Sign In",
                    onClick: () => goto("/login"),
                },
            });
            return;
        }

        try {
            const status = await savedStatusQuery;

            if (status.saved && status.savedBeanId) {
                // Use the notes prop if provided, fallback to the status from the query
                const currentNotes = notes !== undefined ? notes : status.notes;

                if (currentNotes && currentNotes.trim()) {
                    toast("Unsave Bean?", {
                        description:
                            "This bean has personal notes. Unsaving will remove them.",
                        action: {
                            label: "Confirm Unsave",
                            onClick: () => performUnsave(status.savedBeanId!),
                        },
                    });
                } else {
                    await performUnsave(status.savedBeanId);
                }
            } else {
                isSaving = true;
                await saveBean({
                    beanUrlPath,
                    notes: "",
                });
                await savedStatusQuery.refresh();
                toast.success("Bean saved to vault", {
                    action: {
                        label: "View in Vault",
                        onClick: () => goto("/vault"),
                    },
                });

                // Call the callback after everything is done
                if (onSave) {
                    await onSave();
                }

                setTimeout(() => {
                    isSaving = false;
                }, 400);
            }
        } catch (error) {
            console.error("Failed to toggle save status:", error);
            toast.error("An error occurred");
            isSaving = false;
        }
    }
</script>

{#await savedStatusQuery then status}
    <Button
        variant="ghost"
        size="icon-sm"
        onclick={handleSaveToggle}
        disabled={isSaving}
        class={`relative group shrink-0 transition-all duration-300 hover:bg-cyan-500/10 ${className}`}
        title={status.saved ? "Remove from vault" : "Save to vault"}
    >
        <div class="relative flex justify-center items-center w-full h-full">
            {#if isSaving}
                <div
                    class="absolute inset-0 flex justify-center items-center scale-in animate-in duration-300 fade-in"
                >
                    <LoadingIcon width="20" height="20" class="mr-1"
                    ></LoadingIcon>
                </div>
            {/if}

            <div
                class={`transition-all duration-300 ${isSaving ? "opacity-0 scale-75" : "opacity-100 scale-100"}`}
            >
                {#if status.saved}
                    <BookmarkCheck
                        class="drop-shadow-[0_0_8px_rgba(34,211,238,0.5)] fill-primary w-5 h-5 text-primary group-hover:scale-110 transition-transform"
                    />
                {:else}
                    <Bookmark
                        class="w-5 h-5 group-hover:text-primary group-hover:scale-110 transition-transform"
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
        class="opacity-50 text-red-500"
        title="Status unavailable"
    >
        <Bookmark class="w-5 h-5" />
    </Button>
{/await}

<style>
    /* Custom animations if needed beyond tailwind */
</style>
