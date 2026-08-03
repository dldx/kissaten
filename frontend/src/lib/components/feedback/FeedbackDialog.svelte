<script lang="ts">
  import { untrack } from "svelte";
  import { page } from "$app/state";
  import { authClient } from "$lib/auth-client";
  import { toast } from "svelte-sonner";
  import { slide } from "svelte/transition";
  import { Bug, ChevronLeft, ChevronDown, Check } from "lucide-svelte";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { Label } from "$lib/components/ui/label/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import * as Popover from "$lib/components/ui/popover/index.js";
  import * as Command from "$lib/components/ui/command/index.js";
  import { submitFeedback } from "$lib/api/feedback.remote";
  import { feedbackDialog, closeFeedbackDialog } from "$lib/stores/feedbackDialog.svelte";
  import SuggestionTagInput from "./SuggestionTagInput.svelte";
  import type { FeedbackContext, FeedbackFieldOption } from "$lib/types/feedback";
  const session = authClient.useSession();

  let selectedFields = $state<Record<string, boolean>>({});
  let suggestedValues = $state<Record<string, string>>({});
  let message = $state("");
  let reporterEmail = $state("");
  let website = $state(""); // honeypot
  let submitting = $state(false);
  let errorMessage = $state<string | null>(null);
  let mode = $state<"undecided" | "data-wrong" | "comment" | "not-a-bean">("undecided");
  let openPopover = $state<string | null>(null);

  function resetForm() {
    untrack(() => {
      selectedFields = {};
      suggestedValues = {};
      message = "";
      reporterEmail = "";
      website = "";
      errorMessage = null;
      mode = "undecided";
    });
  }

  // Close the dialog whenever the URL changes while the dialog is open.
  // Avoids stale "Reporting on: <old bean>" when the user navigates.
  // We track the pathname at the moment the dialog last opened; if the
  // pathname differs from that snapshot while still open, we close.
  let openPathname = $state<string | null>(null);
  $effect(() => {
    if (feedbackDialog.open && openPathname === null) {
      openPathname = page.url.pathname;
      return;
    }
    if (!feedbackDialog.open) {
      openPathname = null;
      return;
    }
    if (openPathname !== null && page.url.pathname !== openPathname) {
      closeFeedbackDialog();
    }
  });

  // Reset form whenever the dialog opens (fresh context, fresh selections).
  $effect(() => {
    if (feedbackDialog.open) {
      resetForm();
    }
  });

  const isLoggedIn = $derived(!!$session.data);
  const context = $derived<FeedbackContext | undefined>(page.data.feedbackContext);
  const fields = $derived<FeedbackFieldOption[]>(context?.fields ?? []);
  const groupedFields = $derived(groupByGroup(fields));
  const hasSelectedFields = $derived(
    Object.values(selectedFields).some(Boolean),
  );
  const messageValid = $derived(
    mode !== "undecided" &&
      (mode === "not-a-bean" ||
        hasSelectedFields ||
        message.trim().length >= 20),
  );
  const hasFields = $derived(fields.length > 0);
  const showFieldPicker = $derived(mode === "data-wrong" && hasFields);
  const title = $derived(
    mode === "data-wrong"
      ? "Which detail is wrong?"
      : mode === "comment"
        ? "Share a suggestion"
        : mode === "not-a-bean"
          ? "Not a coffee bean?"
          : "How can we help?",
  );
  const messageLabel = $derived(
    showFieldPicker
      ? "Anything else we should know?"
      : mode === "not-a-bean"
        ? "Any details to add?"
        : "Any suggestions?",
  );
  const messagePlaceholder = $derived(
    showFieldPicker
      ? "Optionally add a bit of context or a suggestion."
      : mode === "not-a-bean"
        ? "Optionally add a bit of context or a suggestion."
        : "What were you hoping to find? What can we improve?",
  );
  const submitLabel = $derived(showFieldPicker || mode === "not-a-bean" ? "Submit report" : "Submit feedback");

  function groupByGroup(items: FeedbackFieldOption[]) {
    const groups: Record<string, FeedbackFieldOption[]> = {};
    for (const f of items) {
      const g = f.group ?? "Fields";
      (groups[g] ??= []).push(f);
    }
    return groups;
  }

  function fieldKey(f: FeedbackFieldOption): string {
    return f.originIndex !== undefined ? `${f.group}::${f.originIndex}::${f.key}` : `${f.group}::${f.key}`;
  }

  function buildSelectedFields(): Array<{
    key: string;
    label: string;
    value?: string;
    suggestedValue?: string;
    group?: string;
    originIndex?: number;
  }> {
    const result: Array<{
      key: string;
      label: string;
      value?: string;
      suggestedValue?: string;
      group?: string;
      originIndex?: number;
    }> = [];
    for (const f of fields) {
      const id = fieldKey(f);
      if (selectedFields[id]) {
        const suggested = suggestedValues[id]?.trim();
        result.push({
          key: f.key,
          label: f.label,
          value: f.value,
          suggestedValue: suggested ? suggested : undefined,
          group: f.group,
          originIndex: f.originIndex,
        });
      }
    }
    return result;
  }

  async function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    if (submitting) return;
    errorMessage = null;
    submitting = true;

    try {
      const selected = buildSelectedFields();
      const ctx = context;
      const result = await submitFeedback({
        kind: mode === "not-a-bean" ? "not-a-bean" : (ctx?.kind ?? "general"),
        entitySlug: ctx?.entitySlug ?? "",
        entityUrlPath: ctx?.entityUrlPath ?? "",
        entityName: ctx?.entityName ?? "",
        pageUrl: typeof window !== "undefined" ? window.location.href : page.url.pathname,
        pageTitle: typeof document !== "undefined" ? document.title : "",
        fields: selected,
        message: message.trim(),
        reporterEmail: isLoggedIn ? "" : reporterEmail.trim(),
        website,
      });
      if (result.status === "submitted") {
        toast.success("Report submitted", {
          description: "Thanks — we'll look into it.",
        });
        closeFeedbackDialog();
      }
    } catch (err) {
      const messageText =
        err instanceof Error ? err.message : "Something went wrong. Please try again.";
      // Strip common "validation" prefix from zod issues.
      const cleaned = messageText.replace(/^Validation failed:.*?$/im, "").trim() || messageText;
      errorMessage = cleaned;
    } finally {
      submitting = false;
    }
  }

  const introText = $derived(
    mode === "undecided"
      ? ""
      : mode === "data-wrong"
        ? "Tick the details that look wrong"
        : mode === "comment"
          ? ""
          : "Please report it so it can be removed from the database",
  );
</script>

<Dialog.Root
  bind:open={feedbackDialog.open}
  onOpenChange={(open) => {
    if (!open) closeFeedbackDialog();
  }}
>
  <Dialog.Content class="flex flex-col gap-0 p-0 sm:max-w-lg lg:max-w-2xl max-h-[90vh] overflow-hidden">
    <Dialog.Header class="space-y-2 p-4 border-b shrink-0">
      {#if mode !== "undecided"}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="justify-start self-start gap-2 pr-2 pl-0"
          onclick={() => (mode = "undecided")}
        >
          <ChevronLeft size={18} />
          Back
        </Button>
      {/if}
      <Dialog.Title class="flex items-center gap-2">
      {#if mode === "data-wrong"}🚨{:else if mode === "comment"}🧠{:else if mode === "not-a-bean"}🚫{/if}&nbsp;{title}
      </Dialog.Title>
      {#if mode === "not-a-bean"}
        <Dialog.Description>{introText}</Dialog.Description>
      {/if}
    </Dialog.Header>

    <form
      onsubmit={handleSubmit}
      class="flex flex-col flex-1 min-h-0"
    >
      <div class="flex-1 space-y-4 px-6 py-4 overflow-y-auto">
        {#if context?.entityName}
          <div class="bg-muted/40 px-3 py-1.5 rounded-md text-muted-foreground text-xs">
            <div class="font-medium text-foreground">Reporting on</div>
            <div class="truncate">
              {context.entityName}
            </div>
          </div>
        {/if}

        {#if mode === "undecided"}
          <div class="space-y-3">
            <div class="font-medium text-sm">How can we help?</div>
            <div class="gap-2 grid grid-cols-1 sm:grid-cols-3">
              <button
                type="button"
                onclick={() => (mode = hasFields ? "data-wrong" : "comment")}
                class="group flex flex-col justify-center items-center gap-1 sm:gap-2 hover:bg-muted/30 dark:bg-card dark:hover:bg-muted/10 p-3 sm:p-4 border-2 border-muted hover:border-muted-foreground/30 rounded-2xl text-center active:scale-95 transition-all duration-300"
              >
                <span class="text-2xl sm:text-3xl group-hover:scale-110 transition-transform duration-300">🚨</span>
                <span class="font-bold text-xs uppercase tracking-wider">
                  {hasFields ? "A detail is wrong" : "Something seems off"}
                </span>
                <span class="text-muted-foreground text-xs">
                  {hasFields
                    ? "Price, origin, roast, details…"
                    : "Report a data problem or bug"}
                </span>
              </button>
              <button
                type="button"
                onclick={() => (mode = "comment")}
                class="group flex flex-col justify-center items-center gap-1 sm:gap-2 hover:bg-muted/30 dark:bg-card dark:hover:bg-muted/10 p-3 sm:p-4 border-2 border-muted hover:border-muted-foreground/30 rounded-2xl text-center active:scale-95 transition-all duration-300"
              >
                <span class="text-2xl sm:text-3xl group-hover:scale-110 transition-transform duration-300">🧠</span>
                <span class="font-bold text-xs uppercase tracking-wider">
                  Just a comment
                </span>
                <span class="text-muted-foreground text-xs">
                  Share you thoughts...
                </span>
              </button>
              <button
                type="button"
                onclick={() => (mode = "not-a-bean")}
                class="group flex flex-col justify-center items-center gap-1 sm:gap-2 hover:bg-muted/30 dark:bg-card dark:hover:bg-muted/10 p-3 sm:p-4 border-2 border-muted hover:border-muted-foreground/30 rounded-2xl text-center active:scale-95 transition-all duration-300"
              >
                <span class="text-2xl sm:text-3xl group-hover:scale-110 transition-transform duration-300">🚫</span>
                <span class="font-bold text-xs uppercase tracking-wider">
                  Not a coffee bean
                </span>
                <span class="text-muted-foreground text-xs">
                  Only whole beans allowed
                </span>
              </button>
            </div>
          </div>
        {:else if showFieldPicker}
          <fieldset class="space-y-3">
            {#each Object.entries(groupedFields) as [groupName, groupFields] (groupName)}
              <div class="space-y-1">
                <div class="font-medium text-muted-foreground text-xs uppercase tracking-wide">
                  {groupName}
                </div>
                <div class="gap-1.5 grid grid-cols-1 sm:grid-cols-2">
                  {#each groupFields as field (fieldKey(field))}
                    {@const id = fieldKey(field)}
                    {@const isChecked = !!selectedFields[id]}
                    <div
                      class="hover:bg-muted/50 p-1.5 rounded-md text-sm"
                      class:bg-muted={isChecked}
                      class:sm:col-span-2={["textarea", "tags"].includes(field.input?.type ?? "")}
                    >
                      <label
                        for={id}
                        class="flex items-start gap-2 cursor-pointer"
                      >
                        <input
                          {id}
                          type="checkbox"
                          checked={isChecked}
                          onchange={(e) => {
                            const checked = (e.currentTarget as HTMLInputElement).checked;
                            if (checked) {
                              selectedFields[id] = true;
                              // Initialize to "" (not undefined) — the tag
                              // input's $bindable fallback can't bind to
                              // undefined. For free-text fields (e.g. the
                              // description) we prefill the current value so
                              // the reporter can just edit it.
                              if (suggestedValues[id] === undefined) {
                                suggestedValues[id] =
                                  field.input?.type === "textarea"
                                    ? (field.value ?? "")
                                    : "";
                              }
                            } else {
                              delete selectedFields[id];
                              delete suggestedValues[id];
                            }
                          }}
                          class="mt-1 border-border rounded focus:ring-2 focus:ring-ring w-4 h-4 text-primary accent-current"
                        />
                        <span class="flex flex-col flex-1 min-w-0">
                          <span class="font-medium">{field.label}</span>
                          {#if field.value}
                            <span
                              class="text-muted-foreground text-xs truncate"
                              title={field.value}
                            >
                              {field.value}
                            </span>
                          {/if}
                        </span>
                      </label>
                      {#if isChecked}
                        <div
                          transition:slide={{ duration: 180 }}
                          class="mt-1.5 pl-6"
                        >
                          <div class="mt-1">
                            {#if field.input?.type === "textarea"}
                              <Textarea
                                id={`${id}-suggestion`}
                                bind:value={suggestedValues[id]}
                                placeholder="Suggest the correct value"
                                disabled={submitting}
                                maxlength={8000}
                                rows={field.input.rows ?? 3}
                                class="bg-background/60 min-h-[80px] text-sm"
                              />
                            {:else if field.input?.type === "number"}
                              <Input
                                id={`${id}-suggestion`}
                                type="number"
                                bind:value={suggestedValues[id]}
                                placeholder="Suggest the correct value"
                                disabled={submitting}
                                min={field.input.min}
                                max={field.input.max}
                                step={field.input.step}
                                maxlength={500}
                                class="h-8 text-sm"
                              />
                            {:else if field.input?.type === "month"}
                              <Input
                                id={`${id}-suggestion`}
                                type="month"
                                bind:value={suggestedValues[id]}
                                disabled={submitting}
                                class="h-8 text-sm"
                              />
                            {:else if field.input?.type === "tags"}
                              <SuggestionTagInput
                                bind:value={suggestedValues[id]}
                                disabled={submitting}
                                placeholder="Type a note, then Enter or ,"
                              />
                            {:else if field.input?.type === "select"}
                              <Popover.Root
                                open={openPopover === id}
                                onOpenChange={(o) => { openPopover = o ? id : null; }}
                              >
                                <Popover.Trigger
                                  type="button"
                                  disabled={submitting}
                                  class="flex justify-between items-center disabled:opacity-50 px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring w-full h-8 text-sm"
                                >
                                  <span class="truncate" class:text-muted-foreground={!suggestedValues[id]}>{suggestedValues[id] || "—"}</span>
                                  <ChevronDown class="opacity-50 ml-2 w-4 h-4 shrink-0" />
                                </Popover.Trigger>
                                <Popover.Content class="p-0 max-w-xs" align="start">
                                  <Command.Root>
                                    <Command.Input placeholder="Search an option..." class="h-9" />
                                    <Command.Empty>No option found.</Command.Empty>
                                    <Command.List class="max-h-[200px] overflow-y-auto no-scrollbar">
                                      <Command.Group>
                                        {#each field.input.options as opt (opt)}
                                          <Command.Item
                                            value={opt}
                                            onSelect={() => {
                                              suggestedValues[id] = opt;
                                              openPopover = null;
                                            }}
                                            class="flex justify-between items-center"
                                          >
                                            <span>{opt}</span>
                                            {#if suggestedValues[id] === opt}
                                              <Check class="ml-2 w-4 h-4 shrink-0" />
                                            {/if}
                                          </Command.Item>
                                        {/each}
                                      </Command.Group>
                                    </Command.List>
                                  </Command.Root>
                                </Popover.Content>
                              </Popover.Root>
                            {:else}
                              <Input
                                id={`${id}-suggestion`}
                                type="text"
                                bind:value={suggestedValues[id]}
                                placeholder="Suggest the correct value"
                                disabled={submitting}
                                maxlength={500}
                                class="h-8 text-sm"
                              />
                            {/if}
                          </div>
                        </div>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </fieldset>
        {/if}

        <div class="space-y-2">
          <Label for="feedback-message">
          {#if mode === "data-wrong"}

            {messageLabel}
            {/if}
          </Label>
          <Textarea
            id="feedback-message"
            bind:value={message}
            placeholder={messagePlaceholder}
            rows={4}
            maxlength={2000}
            disabled={submitting}
            class="bg-background/60 min-h-[90px]"
          />
          <div class="text-muted-foreground text-xs">
            {message.length} / 2000
            {#if hasSelectedFields}
              · optional
            {/if}
          </div>
        </div>

        {#if !isLoggedIn}
          <div class="space-y-2">
            <Label for="feedback-email">Email (optional)</Label>
            <Input
              id="feedback-email"
              type="email"
              bind:value={reporterEmail}
              placeholder="you@example.com"
              disabled={submitting}
              maxlength={200}
            />
            <p class="text-muted-foreground text-xs">
              Only used if we need to follow up on your report.
            </p>
          </div>
        {/if}

        <!-- Honeypot: hidden from real users, bots auto-fill anything that looks required. -->
        <div class="hidden" aria-hidden="true">
          <Label for="feedback-website">Website</Label>
          <Input
            id="feedback-website"
            type="text"
            bind:value={website}
            tabindex={-1}
            autocomplete="off"
          />
        </div>

        {#if errorMessage}
          <div class="text-destructive text-sm" role="alert">
            {errorMessage}
          </div>
        {/if}
      </div>

      <Dialog.Footer
        class="gap-2 bg-background/95 supports-backdrop-filter:bg-background/80 backdrop-blur px-6 py-4 border-t shrink-0"
      >
        <div class="sm:flex-1 text-muted-foreground text-xs">
          {#if isLoggedIn}
            Signed in as {$session.data?.user?.email ?? "you"} · page data sent automatically
          {:else}
            Anonymous submission · page data sent automatically
          {/if}
        </div>
        <Button
          type="button"
          variant="outline"
          onclick={() => closeFeedbackDialog()}
          disabled={submitting}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={submitting || !messageValid}>
          {#if submitting}
            Submitting…
          {:else}
            {submitLabel}
          {/if}
        </Button>
      </Dialog.Footer>
    </form>
  </Dialog.Content>
</Dialog.Root>
