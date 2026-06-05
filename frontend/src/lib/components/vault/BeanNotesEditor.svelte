<script lang="ts">
    import { updateBeanNotes } from "$lib/api/vault.remote";
    import { db } from "$lib/db/localdb";
    import { notifyUpdate } from "$lib/db/updates.svelte";
    import LoadingIcon from "virtual:icons/line-md/loading-twotone-loop";
    import ConfirmIcon from "virtual:icons/line-md/confirm";
    import AlertIcon from "virtual:icons/line-md/alert-circle";

    interface Props {
        savedBeanId: string;
        initialNotes?: string;
        id?: string;
        class?: string;
        textareaClass?: string;
        placeholder?: string;
        onNoteChange?: (notes: string) => void;
    }

    let {
        savedBeanId,
        initialNotes = "",
        id = "",
        class: className = "",
        textareaClass = "",
        placeholder = "Add your notes here...",
        onNoteChange,
    }: Props = $props();

    let currentNotes = $state(initialNotes);
    let isSaving = $state(false);
    let hasError = $state(false);
    let debounceTimer: any;

    // Update local state if initialNotes changes (e.g. from external data)
    $effect(() => {
        currentNotes = initialNotes;
    });

    function handleInput(e: Event & { currentTarget: HTMLTextAreaElement }) {
        const newNotes = e.currentTarget.value;
        currentNotes = newNotes;
        onNoteChange?.(newNotes);

        if (debounceTimer) clearTimeout(debounceTimer);

        debounceTimer = setTimeout(async () => {
            isSaving = true;
            hasError = false;
            try {
                // Local update first
                if (savedBeanId.startsWith("custom_")) {
                    // Custom beans store their data in beanData as JSON, but for now we don't have separate notes for them
                    // Since the UI doesn't allow editing custom bean "notes" yet (it uses beanData), this might not be reachable
                    // but we handle it just in case.
                } else {
                    await db.savedBeans.where("syncId").equals(savedBeanId).modify({
                        notes: newNotes,
                        updatedAt: Date.now()
                    });
                    notifyUpdate("savedBeans");
                }

                await updateBeanNotes({ savedBeanId, notes: newNotes });
            } catch (error) {
                console.error("Failed to save notes:", error);
                hasError = true;
            } finally {
                // Keep showing saving state for a brief moment for visual feedback
                setTimeout(() => {
                    isSaving = false;
                }, 500);
            }
        }, 500);
    }
</script>

<div class={`notes-editor ${className}`}>
    <textarea
        {id}
        value={currentNotes}
        oninput={handleInput}
        {placeholder}
        class={`w-full p-3 bg-white/50 dark:bg-slate-950/40 border border-gray-200 dark:border-cyan-500/20 focus:border-primary dark:focus:border-cyan-500/50 rounded-lg transition-all duration-300 focus:ring-1 focus:ring-primary/30 dark:focus:ring-cyan-500/30 outline-hidden resize-none placeholder:text-gray-400 dark:placeholder:text-cyan-400/30 text-gray-900 dark:text-cyan-100 text-sm ${textareaClass}`}
    ></textarea>

    <div class="flex items-center mt-1 h-4">
        {#if isSaving}
            <div
                class="flex items-center gap-1.5 text-orange-500 dark:text-emerald-400"
            >
                <LoadingIcon width="12" height="12" class="mr-1"></LoadingIcon>
                <span class="font-medium text-xs animate-pulse">Saving...</span>
            </div>
        {:else}
            <div
                class="flex items-center gap-1 {hasError
                    ? 'text-red-500 dark:text-red-400'
                    : 'text-gray-400 dark:text-cyan-500/40'}"
            >
                {#if hasError}
                    <AlertIcon width="12" height="12" class="mr-1"></AlertIcon>
                {:else}
                    <ConfirmIcon width="12" height="12" class="mr-1"
                    ></ConfirmIcon>
                {/if}
                <span class="text-xs">
                    {hasError ? "Failed to save" : currentNotes ? "Saved" : ""}
                </span>
            </div>
        {/if}
    </div>
</div>
