import type { FeedbackFieldValue } from "$lib/types/feedback";

/** Serialize a suggested field value to the string form the feedback API
 *  expects. Returns `undefined` for absent, empty, or whitespace-only values. */
export function toSuggestedValue(raw: FeedbackFieldValue | undefined): string | undefined {
  if (raw === null || raw === undefined) return undefined;
  if (typeof raw === "number" && !Number.isFinite(raw)) return undefined;
  const value = String(raw).trim();
  return value.length > 0 ? value : undefined;
}
