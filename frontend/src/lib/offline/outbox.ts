import { db, type OutboxEntry } from "$lib/db/localdb";

/**
 * Offline feedback/action outbox (Phase 3). While the network is down, writes
 * are queued in the Dexie `outbox` table instead of being dropped; `flushOutbox`
 * replays them when the connection returns (the same pattern as the sync
 * engine). Never throws — the app must not break just because queuing failed.
 */

/**
 * Queue a payload for later delivery. `payload` is JSON-sanitized so no Svelte
 * proxies or non-clonable values leak into IndexedDB.
 */
export async function enqueueOutbox(
  kind: string,
  payload: unknown,
): Promise<void> {
  try {
    await db.outbox.add({
      kind,
      payload: JSON.parse(JSON.stringify(payload)),
      createdAt: Date.now(),
    });
  } catch (error) {
    console.warn("[outbox] Failed to queue entry:", error);
  }
}

/**
 * Deliver a single queued entry. Returns true when the server accepted it
 * (entry deleted on success, kept on any failure).
 */
async function deliver(entry: OutboxEntry): Promise<boolean> {
  try {
    if (entry.kind === "ai-feedback") {
      const { query_hash, vote } = entry.payload as {
        query_hash?: string;
        vote?: "up" | "down";
      };
      // Same body shape as `KissatenAPI.submitSearchFeedback`.
      const res = await fetch("/api/v1/ai/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query_hash, vote }),
      });
      return res.ok;
    }
    // Unknown kinds are never delivered (and never block the others).
    return false;
  } catch (error) {
    console.warn("[outbox] Delivery failed, entry will be retried:", error);
    return false;
  }
}

/**
 * Replay every queued entry. Successfully delivered entries are removed from
 * the outbox; failures are kept for the next flush. Skips entirely while the
 * browser reports offline.
 */
export async function flushOutbox(): Promise<void> {
  if (typeof navigator !== "undefined" && !navigator.onLine) return;
  try {
    const entries = await db.outbox.toArray();
    if (entries.length === 0) return;
    for (const entry of entries) {
      if (entry.id === undefined) continue;
      if (await deliver(entry)) {
        await db.outbox.delete(entry.id);
      }
    }
  } catch (error) {
    console.warn("[outbox] Flush failed:", error);
  }
}
