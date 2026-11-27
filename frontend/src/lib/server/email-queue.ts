/**
 * Batched email outbox for user-facing notifications.
 *
 * Notifications that would otherwise spam users (a roaster they voted for got
 * added, a report they filed was resolved, beta access approved, …) are
 * enqueued here as `email_queue` rows instead of being sent immediately.
 * `flushEmailQueue` then groups pending rows per recipient and sends AT MOST
 * ONE digest email per person per flush — single-item recipients get their
 * normal per-kind template, multi-item recipients get the aggregated
 * `userDigestTemplate`.
 *
 * Admin notifications intentionally bypass this queue and stay immediate.
 *
 * Failure semantics: a SEND failure leaves the recipient's rows `pending` so
 * the next flush retries them (self-healing when SMTP is temporarily down);
 * a render failure (bad payload) is deterministic and marks the rows `failed`.
 *
 * The module deliberately uses relative imports (no `$lib`) so the standalone
 * flush script (scripts/flush-email-queue.ts, run with bund) can reuse it.
 */
import { and, eq, inArray } from "drizzle-orm";
import { nanoid } from "nanoid";
import type { LibSQLDatabase } from "drizzle-orm/libsql";
import { emailQueue } from "./database/schema";
import { sendEmail } from "./email";
import {
  betaApprovedUserTemplate,
  roasterImplementedUserTemplate,
  userDigestTemplate,
  USER_EMAIL_LOGO_ATTACHMENT,
  type UserDigestItem,
} from "./email-templates";
import type { EmailRendered } from "./email-templates";

// Any drizzle/libsql instance works: the queue functions only touch the
// emailQueue table object, so both the schema-configured SvelteKit db and the
// bare drizzle client used by standalone scripts satisfy this.
export type QueueDb = LibSQLDatabase<any>;

export type QueueEmailKind = UserDigestItem["kind"];

const QUEUE_ROW_STATUS = ["pending", "sent", "failed"] as const;
type QueueRowStatus = (typeof QUEUE_ROW_STATUS)[number];

/** Insert a single notification into the outbox. Sends nothing. */
export async function enqueueEmail(
  db: QueueDb,
  input: {
    to: string;
    name?: string | null;
    kind: QueueEmailKind;
    data: UserDigestItem;
  },
): Promise<void> {
  await db.insert(emailQueue).values({
    id: `eml_${nanoid()}`,
    recipientEmail: input.to,
    recipientName: input.name ?? null,
    kind: input.kind,
    data: input.data,
    status: "pending",
    createdAt: new Date(),
  });
}

/**
 * Send one aggregated digest email per recipient for all pending rows, then
 * mark the rows sent. Never throws: per-recipient send errors are caught and
 * logged, and those rows are left `pending` so a later flush retries them.
 */
export async function flushEmailQueue(
  db: QueueDb,
): Promise<{ sent: number; failed: number }> {
  const rows = await db
    .select()
    .from(emailQueue)
    .where(eq(emailQueue.status, "pending"))
    .orderBy(emailQueue.createdAt);

  if (rows.length === 0) return { sent: 0, failed: 0 };

  // One email per recipient, oldest items first.
  const buckets = new Map<string, typeof rows>();
  for (const row of rows) {
    const bucket = buckets.get(row.recipientEmail) ?? [];
    bucket.push(row);
    buckets.set(row.recipientEmail, bucket);
  }

  let sent = 0;
  let failed = 0;
  for (const [email, rowsForUser] of buckets) {
    const name = rowsForUser[0]?.recipientName ?? null;
    const items = rowsForUser.map((r) => r.data as UserDigestItem);

    let rendered: EmailRendered;
    try {
      rendered =
        items.length === 1
          ? renderSingle(items[0])
          : userDigestTemplate({ name, items });
    } catch (err) {
      console.error(`[email-queue] Could not render digest for ${email}:`, err);
      await markRows(db, rowsForUser, "failed");
      failed++;
      continue;
    }

    try {
      await sendEmail({
        to: email,
        subject: rendered.subject,
        text: rendered.text,
        html: rendered.html,
        attachments: [USER_EMAIL_LOGO_ATTACHMENT],
      });
      await markRows(db, rowsForUser, "sent");
      sent++;
    } catch (err) {
      // Leave the rows pending so the next flush retries them.
      console.error(`[email-queue] Failed to send digest to ${email}:`, err);
      failed++;
    }
  }

  return { sent, failed };
}

/** Render a single-item notification with its dedicated template. */
export function renderSingle(item: UserDigestItem): EmailRendered {
  switch (item.kind) {
    case "roaster-implemented":
      return roasterImplementedUserTemplate({
        name: item.name,
        roasterName: item.roasterName,
        roasterUrl: item.roasterUrl,
      });
    case "beta-approved":
      return betaApprovedUserTemplate({ name: item.name });
    case "report-resolved":
      // No dedicated template yet (report lifecycle is a later slice) — a
      // one-item digest is plenty.
      return userDigestTemplate({ name: item.name, items: [item] });
  }
}

type QueueRow = typeof emailQueue.$inferSelect;

async function markRows(
  db: QueueDb,
  rows: QueueRow[],
  status: QueueRowStatus,
): Promise<void> {
  const ids = rows.map((r) => r.id);
  await db
    .update(emailQueue)
    .set({
      status,
      ...(status === "sent" ? { sentAt: new Date() } : {}),
    })
    .where(and(inArray(emailQueue.id, ids), eq(emailQueue.status, "pending")));
}
