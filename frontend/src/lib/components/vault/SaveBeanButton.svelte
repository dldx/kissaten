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
    import { db } from "$lib/db/localdb";
    import { notifyUpdate, dbUpdateTrigger } from "$lib/db/updates.svelte";
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

        console.log(`[SaveBeanButton] Effect triggered for ${url}`);

        async function updateStatus() {
            if (!url) {
                console.log("[SaveBeanButton] No URL for updateStatus");
                return;
            }

            console.log(`[SaveBeanButton] Updating status for: ${url}`);

            // Check savedBeans locally
            const saved = await db.savedBeans
                .where('beanUrlPath')
                .equals(url)
                .filter(b => !b.deletedAt && (b.ownerId === userId || !b.ownerId || !userId))
                .first();

            if (saved) {
                console.log("[SaveBeanButton] Found in savedBeans:", saved.syncId);
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
                 console.log("[SaveBeanButton] Found in customBeans:", custom.syncId);
                 localStatus = {
                    saved: true,
                    savedBeanId: custom.syncId,
                    notes: "",
                    isLoading: false
                };
                return;
            }

            console.log("[SaveBeanButton] Not found in either store (or deleted)");
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
            console.error("[SaveBeanButton] performUnsave called with null/undefined ID");
            return;
        }
        if (isSaving) {
            console.log("[SaveBeanButton] Already saving/unsaving, ignoring...");
            return;
        }
        console.log(`[SaveBeanButton] Starting performUnsave for ID: "${savedBeanId}"`);
        isSaving = true;

        // Capture current notes for possible undo
        const notesToRestore = notes;
        let customRecordToRestore: any = null;

        try {
            // Local update first (local-first)
            if (savedBeanId.startsWith("custom_")) {
                console.log("[SaveBeanButton] Processing as custom bean...");

                try {
                    if (!db.isOpen()) {
                        console.log("[SaveBeanButton] DB is closed, opening...");
                        await db.open();
                    }

                    console.log("[SaveBeanButton] Direct query for deletion target...");
                    const record = await db.customBeans.where("syncId").equals(savedBeanId).first();

                    if (record) {
                        await db.customBeans.delete(record.id!);
                        console.log("[SaveBeanButton] Local hard-delete success.");
                    } else {
                        console.warn("[SaveBeanButton] No records found to delete locally for:", savedBeanId);
                    }
                } catch (dbErr) {
                    console.error("[SaveBeanButton] Database operation failed during custom bean unsave:", dbErr);
                }

                notifyUpdate("customBeans");

                console.log("[SaveBeanButton] Triggering remote delete non-blocking...");
                deleteCustomBean(savedBeanId).then(res => {
                    console.log("[SaveBeanButton] Background remote delete response:", res);
                }).catch(err => {
                    console.error("[SaveBeanButton] Background remote delete failed:", err);
                });

                console.log("[SaveBeanButton] Success, showing direct toast (no undo for custom beans)...");
                toast.success("Custom bean permanently removed");
            } else {
                console.log("[SaveBeanButton] Processing as saved bean...");
                const count = await db.savedBeans.where("syncId").equals(savedBeanId).delete();
                console.log(`[SaveBeanButton] Local delete complete. Deleted ${count} records.`);
                notifyUpdate("savedBeans");

                console.log("[SaveBeanButton] Triggering remote unsave non-blocking...");
                unsaveBean({ savedBeanId }).then(res => {
                    console.log("[SaveBeanButton] Background remote unsave response:", res);
                }).catch(err => {
                    console.error("[SaveBeanButton] Background remote unsave failed:", err);
                });

                console.log("[SaveBeanButton] Success, showing undo toast for public bean...");
                toast.success("Bean removed from vault", {
                    action: {
                        label: "Undo",
                        onClick: async () => {
                            console.log("[SaveBeanButton] Undo clicked");
                            try {
                                isSaving = true;
                                console.log("[SaveBeanButton] Undoing bean unsave...");
                                // Re-save regular bean via server
                                const result = await saveBean({
                                    beanUrlPath,
                                    notes: notesToRestore || "",
                                });

                                const newSyncId = result?.id || savedBeanId;
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
                                notifyUpdate("savedBeans");

                                onSave?.(); // Call callback
                                toast.success("Restored bean and notes");
                            } catch (e) {
                                console.error("[SaveBeanButton] Failed to restore bean:", e);
                                toast.error("Failed to restore bean");
                            } finally {
                                isSaving = false;
                            }
                        },
                    },
                });
            }
            console.log("[SaveBeanButton] Calling onUnsave callback...");
            onUnsave?.(); // Call callback
        } catch (error) {
            console.error("[SaveBeanButton] Failed to unsave bean:", error);
            toast.error("Failed to remove bean");
        } finally {
            console.log("[SaveBeanButton] performUnsave finally block reached");
            setTimeout(() => {
                isSaving = false;
                console.log("[SaveBeanButton] isSaving set to false after delay");
            }, 400);
        }
    }

    async function handleSaveToggle(event: MouseEvent) {
        event.stopPropagation();
        event.preventDefault();
        console.log("[SaveBeanButton] handleSaveToggle clicked");
        if (isSaving) {
            console.log("[SaveBeanButton] isSaving is true, ignoring click");
            return;
        }

        // Check if user is authenticated
        if (!$session.data) {
            console.log("[SaveBeanButton] No session, redirecting to login...");
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
            console.log("[SaveBeanButton] Current status:", JSON.parse(JSON.stringify(status)));

            if (status.saved && status.savedBeanId) {
                const beanName = bean?.name || "this bean";
                // Warning for custom beans
                if (status.savedBeanId.startsWith("custom_")) {
                    console.log("[SaveBeanButton] Confirming deletion for custom bean...");
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
                    console.log("[SaveBeanButton] Showing unsave confirmation toast due to notes...");
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
                console.log("[SaveBeanButton] Saving new bean...");
                isSaving = true;
                const result = await saveBean({
                    beanUrlPath,
                    notes: notes || "",
                });
                console.log("[SaveBeanButton] saveBean response:", result);

                // Update local DB immediately
                const newSyncId = result?.id;
                if (newSyncId) {
                    console.log("[SaveBeanButton] Adding to local database...");
                    await db.savedBeans.add({
                        syncId: newSyncId,
                        beanUrlPath,
                        notes: notes || null,
                        createdAt: Date.now(),
                        updatedAt: Date.now(),
                        deletedAt: null,
                        syncedAt: Date.now(),
                        ownerId: $session.data?.user.id || null,
                        beanData: JSON.parse(JSON.stringify(bean))
                    });
                    notifyUpdate("savedBeans");
                }

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
            console.error("[SaveBeanButton] handleSaveToggle error:", error);
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
