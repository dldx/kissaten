<script lang="ts">
    import { Button } from "$lib/components/ui/button/index.js";
    import { Bookmark, BookmarkCheck, Check, Trash2 } from "lucide-svelte";
    import LoadingIcon from "virtual:icons/line-md/loading-twotone-loop";
    import {
        saveBean,
        unsaveBean,
        checkBeanSaved,
    } from "$lib/api/vault.remote";
    import { deleteCustomBean } from "$lib/api/custom_beans.remote";
    import { api } from "$lib/api";
    import { db, generateUUID } from "$lib/db/localdb";
    import { notifyUpdate, dbUpdateTrigger } from "$lib/db/updates.svelte";
    import { runGlobalSync } from "$lib/sync/syncManager.svelte";
    import { toast } from "svelte-sonner";
    import { goto } from "$app/navigation";
    import { authClient } from "$lib/auth-client";

    interface Props {
        bean: any; // Using any for flexibility or specific CoffeeBean type if available
        notes?: string;
        class?: string;
        onSave?: () => void; // Callback when bean is saved
        onUnsave?: () => void; // Callback when bean is unsaved
        variant?: "icon" | "ribbon" | "ghost-unsave";
    }

    let {
        bean,
        notes,
        class: className = "",
        onSave,
        onUnsave,
        variant = "icon",
    }: Props = $props();

    let isSaving = $state(false);
    const session = authClient.useSession();
    const beanUrlPath = $derived(
        bean?.bean_url_path || api.getBeanUrlPath(bean),
    );

    // Local state for saved status (local-first)
    let localStatus = $state({
        saved: false,
        savedBeanId: null as string | null,
        notes: "",
        isLoading: true
    });

    $effect(() => {
        const url = beanUrlPath;
        const _s = dbUpdateTrigger.savedBeans;
        const _c = dbUpdateTrigger.customBeans;
        const userId = $session.data?.user.id;

        async function updateStatus() {
            if (!url) {
                return;
            }

            // Check savedBeans locally
            const saved = await db.savedBeans
                .where('beanUrlPath')
                .equals(url)
                .filter(b => !b.deletedAt && (b.ownerId === userId || !b.ownerId || !userId))
                .first();

            if (saved) {
                localStatus = {
                    saved: true,
                    savedBeanId: saved.syncId,
                    notes: saved.notes || "",
                    isLoading: false
                };
                return;
            }

            // Check customBeans locally
            const custom = await db.customBeans
                .where('beanUrlPath')
                .equals(url)
                .filter(b => !b.deletedAt && (b.ownerId === userId || !b.ownerId || !userId))
                .first();

            if (custom) {
                 localStatus = {
                    saved: true,
                    savedBeanId: custom.syncId,
                    notes: "",
                    isLoading: false
                };
                return;
            }

            localStatus = {
                saved: false,
                savedBeanId: null,
                notes: "",
                isLoading: false
            };
        }

        updateStatus();
    });

    async function performUnsave(savedBeanId: string) {
        if (!savedBeanId) {
            console.error("performUnsave called with null/undefined ID");
            return;
        }
        if (isSaving) {
            return;
        }
        isSaving = true;

        // Capture current notes for possible undo
        const notesToRestore = notes;
        let customRecordToRestore: any = null;

        try {
            // Local update first (local-first)
            if (savedBeanId.startsWith("custom_")) {
                try {
                    if (!db.isOpen()) {
                        await db.open();
                    }

                    const record = await db.customBeans.where("syncId").equals(savedBeanId).first();

                    if (record) {
                        await db.customBeans.delete(record.id!);
                    }
                } catch (dbErr) {
                    console.error("Database operation failed during custom bean unsave:", dbErr);
                }

                notifyUpdate("customBeans");

                deleteCustomBean(savedBeanId).catch(err => {
                    console.error("Background remote delete failed:", err);
                });

                toast.success("Custom bean permanently removed");
            } else {
                // Perform a local soft-delete first
                const record = await db.savedBeans.where("syncId").equals(savedBeanId).first();
                if (!record) return;

                await db.savedBeans.update(record.id!, {
                    deletedAt: Date.now(),
                    updatedAt: Date.now()
                });
                notifyUpdate("savedBeans");

                if (record.syncedAt) {
                    unsaveBean({ savedBeanId }).then(async () => {
                        await db.savedBeans.where("syncId").equals(savedBeanId).delete();
                        notifyUpdate("savedBeans");
                    }).catch(err => {
                        console.error("Background remote unsave failed (retaining soft-delete locally):", err);
                    });
                } else {
                    // Record was never synced, just delete it locally
                    await db.savedBeans.delete(record.id!);
                    notifyUpdate("savedBeans");
                }

                toast.success("Bean removed from vault", {
                    action: {
                        label: "Undo",
                        onClick: async () => {
                            try {
                                isSaving = true;
                                // Re-save regular bean via server
                                const result = await saveBean({
                                    beanUrlPath,
                                    notes: notesToRestore || "",
                                });

                                const newSyncId = result?.id || savedBeanId;
                                const existingLocally = await db.savedBeans.where("syncId").equals(savedBeanId).first();
                                if (existingLocally) {
                                    await db.savedBeans.update(existingLocally.id!, {
                                        syncId: newSyncId,
                                        deletedAt: null,
                                        syncedAt: Date.now(),
                                        updatedAt: Date.now(),
                                        notes: notesToRestore || null
                                    });
                                } else {
                                    await db.savedBeans.add({
                                        syncId: newSyncId,
                                        beanUrlPath,
                                        notes: notesToRestore || null,
                                        createdAt: Date.now(),
                                        updatedAt: Date.now(),
                                        deletedAt: null,
                                        syncedAt: Date.now(),
                                        ownerId: $session.data?.user.id || null,
                                        beanData: JSON.parse(JSON.stringify(bean))
                                    });
                                }
                                notifyUpdate("savedBeans");

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
            }
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

    async function handleSaveToggle(event: MouseEvent) {
        event.stopPropagation();
        event.preventDefault();
        if (isSaving) {
            return;
        }

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
            const status = localStatus;

            if (status.saved && status.savedBeanId) {
                const beanName = bean?.name || "this bean";
                // Warning for custom beans
                if (status.savedBeanId.startsWith("custom_")) {
                    toast(`Remove ${beanName}?`, {
                        description:
                            "This will permanently delete this custom bean from your collection.",
                        action: {
                            label: "Confirm Delete",
                            onClick: () => performUnsave(status.savedBeanId!),
                        },
                    });
                    return;
                }

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

                // Optimistic local save (offline-first)
                const tempSyncId = generateUUID();
                await db.savedBeans.add({
                    syncId: tempSyncId,
                    beanUrlPath,
                    notes: notes || null,
                    createdAt: Date.now(),
                    updatedAt: Date.now(),
                    deletedAt: null,
                    syncedAt: null, // Mark as unsynced for the sync engine
                    ownerId: $session.data?.user.id || null,
                    beanData: JSON.parse(JSON.stringify(bean))
                });

                notifyUpdate("savedBeans");

                toast.success("Bean saved to vault", {
                    action: {
                        label: "View in Vault",
                        onClick: () => goto("/vault"),
                    },
                });

                // Call the callback immediately
                if (onSave) {
                    onSave();
                }

                // Trigger background sync
                void runGlobalSync({ silent: true });

                setTimeout(() => {
                    isSaving = false;
                }, 400);
            }
        } catch (error) {
            console.error("handleSaveToggle error:", error);
            toast.error("An error occurred");
            isSaving = false;
        }
    }
</script>

{#if !localStatus.isLoading}
    {@const status = localStatus}
    {#if variant === "ribbon"}
        <div class="hidden sm:block top-0 right-4 absolute drop-shadow-md w-4 h-8 hover:h-12 overflow-visible transition-all duration-300">
            <button
                onclick={(e) => handleSaveToggle(e)}
                disabled={isSaving}
                class={`w-full h-full ${status.saved ? "bg-primary/95 dark:bg-primary/95" : "bg-primary dark:bg-primary grayscale-100 brightness-150 hover:grayscale-0 hover:brightness-100"} ${className} cursor-pointer transition-all`}
                style="clip-path: polygon(0% 0%, 100% 0%, 100% 100%, 50% 88%, 0% 100%);"
                title={status.saved ? "Remove from vault" : "Save to vault"}
            >
                <div class="flex justify-center items-center mt-3 w-full">
                    {#if isSaving}
                        <LoadingIcon
                            width="16"
                            height="16"
                            class="text-white animate-spin"
                        />
                    {:else if status.saved}
                        <Check
                            class="drop-shadow-[0_0_4px_rgba(34,211,238,0.8)] w-3 h-3 text-white"
                        />
                    {/if}
                </div>
            </button>
        </div>
    {:else if variant === "ghost-unsave"}
        {#if status.saved}
            <Button
                variant="ghost"
                size="sm"
                onclick={(e: MouseEvent) => handleSaveToggle(e)}
                disabled={isSaving}
                class={`dark:hover:bg-red-900/20 h-7 dark:hover:text-red-300 dark:text-red-400 text-xs ${className}`}
                title="Remove from your vault"
            >
                {#if isSaving}
                    <LoadingIcon
                        width="12"
                        height="12"
                        class="mr-1 text-red-500 animate-spin"
                    />
                    Unsaving...
                {:else}
                    <Trash2 class="mr-1 w-3 h-3" />
                    Unsave
                {/if}
            </Button>
        {/if}
    {:else}
        <Button
            variant="outline"
            size="icon-sm"
            onclick={(e: MouseEvent) => handleSaveToggle(e)}
            disabled={isSaving}
            class={`relative p-1 group shrink-0 transition-all duration-300 ${className}`}
            title={status.saved ? "Remove from your vault" : "Save to your vault"}
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
                    class={`transition-all flex  flex-row duration-300 ${isSaving ? "opacity-0 scale-75" : "opacity-100 scale-100"}`}
                >
                    {#if status.saved}
                        <BookmarkCheck
                            class="drop-shadow-[0_0_8px_rgba(34,211,238,0.5)] w-5 h-5 text-primary group-hover:scale-110 transition-transform"
                        /> In your vault
                    {:else}
                        <Bookmark
                            class="w-5 h-5 group-hover:scale-110 transition-transform"
                        /> Save to vault
                    {/if}
                </div>
            </div>
        </Button>
    {/if}
{:else}
    {#if variant === "ghost-unsave"}
        <Button
            variant="ghost"
            size="sm"
            disabled
            class="opacity-50 h-7 text-xs"
        >
            <LoadingIcon width="12" height="12" class="mr-1 animate-spin" />
            Unsave
        </Button>
    {:else}
        <Button
            variant="ghost"
            size="icon"
            disabled
            class="opacity-50"
            title="Loading status..."
        >
            <Bookmark class="w-5 h-5 animate-pulse" />
        </Button>
    {/if}
{/if}

<style>
    /* Custom animations if needed beyond tailwind */
</style>
