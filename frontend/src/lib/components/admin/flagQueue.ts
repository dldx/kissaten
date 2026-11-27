import type { SvelteComponentTyped } from "svelte";
import type { CoffeeBean } from "$lib/api";

/**
 * Any renderable icon component. lucide-svelte's per-icon exports are legacy
 * Svelte component classes (subclasses of `SvelteComponentTyped`), which the
 * runes `Component` type from "svelte" does not accept — use this instead.
 */
export type FlagQueueIcon = typeof SvelteComponentTyped<any, any, any>;

/** Badge rendered inline next to the flag item's name / roaster. */
export interface FlagQueueBadge {
  label: string;
  variant?: "default" | "secondary" | "destructive" | "outline";
  className?: string;
}

/** One action button rendered on an admin flag row (Approve / Reject / Restore bean). */
export interface FlagQueueAction {
  label: string;
  icon?: FlagQueueIcon;
  variant?:
    | "default"
    | "destructive"
    | "outline"
    | "secondary"
    | "ghost"
    | "link";
  disabled?: boolean;
  onClick: () => void;
}

/**
 * One row in an admin flag queue (scraper-flagged beans or user-reported
 * beans). The row body in `AdminFlagQueueRow` is fully driven by this model,
 * so every queue renders with identical markup. When `bean` is set the row
 * shows the bean's thumbnail, price and source link (and becomes a hover
 * card); otherwise it falls back to `displayName` + `icon`.
 */
export interface FlagQueueItem {
  /** Unique key for `{#each}`. */
  id: string;
  /** Resolved bean data driving thumbnail / price / source link + hover card. */
  bean?: CoffeeBean | null;
  /** Name used when no bean data is available. */
  displayName: string;
  /** Leading icon shown only when the bean has no thumbnail. */
  icon?: FlagQueueIcon;
  /** Entity path linked to the bean page (e.g. "/roaster/bean"). */
  pathLabel?: string;
  badges?: FlagQueueBadge[];
  /** Muted trailing text, e.g. "decided 3h ago". */
  caption?: string;
  /** Title (hover) for `caption`, typically the absolute date. */
  captionTitle?: string;
  inlineError?: string;
  actions: FlagQueueAction[];
}
