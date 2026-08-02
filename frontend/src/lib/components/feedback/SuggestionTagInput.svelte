<script lang="ts">
  import { X } from "lucide-svelte";

  interface Props {
    /** Comma-joined current value (bound two-way by the parent). This is
     *  the single source of truth — tags are derived from it, and writes go
     *  straight back into it. */
    value?: string;
    disabled?: boolean;
    placeholder?: string;
    maxTags?: number;
  }

  let {
    value = $bindable(""),
    disabled = false,
    placeholder = "Type a note and press Enter or comma",
    maxTags = 30,
  }: Props = $props();

  let draft = $state("");

  // `tags` is derived directly from `value`, so it can never drift out of
  // sync (and there's no competing effect to reset it after you add a tag).
  const tags = $derived(
    (value ?? "")
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean),
  );

  function addTag() {
    const t = draft.trim();
    if (!t) {
      draft = "";
      return;
    }
    const next = tags.includes(t) ? tags : [...tags, t].slice(0, maxTags);
    value = next.join(", ");
    draft = "";
  }

  function removeTag(t: string) {
    value = tags.filter((x) => x !== t).join(", ");
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "," || e.key === "Enter") {
      e.preventDefault();
      addTag();
    } else if (e.key === "Backspace" && draft === "" && tags.length > 0) {
      e.preventDefault();
      value = tags.slice(0, -1).join(", ");
    }
  }

  function onInput(e: Event) {
    // Handle pasted content that may contain commas.
    const input = e.currentTarget as HTMLInputElement;
    if (!input.value.includes(",")) return;
    const [head, ...rest] = input.value.split(",");
    draft = head;
    addTag();
    const extra = rest
      .map((s) => s.trim())
      .filter((s) => s && !tags.includes(s))
      .slice(0, Math.max(0, maxTags - tags.length));
    value = [...tags, ...extra].join(", ");
    draft = "";
  }
</script>

<div
  class="border-input dark:bg-input/30 focus-within:border-ring focus-within:ring-ring/50 rounded-md border bg-transparent focus-within:ring-3"
>
  <div class="flex flex-wrap items-center gap-1.5 p-2">
    {#each tags as tag (tag)}
      <span
        class="inline-flex items-center rounded-full border bg-gray-100 px-2 py-0.5 text-xs text-gray-800 transition-all duration-200 dark:bg-gray-900/30 dark:text-gray-300 dark:shadow-[0_0_6px_rgba(34,211,238,0.2)]"
      >
        {tag}
        {#if !disabled}
          <button
            type="button"
            aria-label={`Remove ${tag}`}
            onclick={() => removeTag(tag)}
            class="rounded-full hover:bg-muted-foreground/20 p-0.5"
          >
            <X class="w-3 h-3" />
          </button>
        {/if}
      </span>
    {/each}
    <input
      bind:value={draft}
      type="text"
      {placeholder}
      {disabled}
      maxlength={100}
      onkeydown={onKeydown}
      onblur={addTag}
      oninput={onInput}
      class="flex-1 bg-transparent min-w-[120px] text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
    />
  </div>
</div>
