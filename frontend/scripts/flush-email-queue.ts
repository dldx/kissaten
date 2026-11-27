/**
 * Flush the batched email outbox: group all pending user notifications per
 * recipient and send ONE aggregated digest email per person (multi-item
 * senders get the digest template, single-item senders get their normal
 * per-kind template).
 *
 * Usage (run from the frontend/ directory):
 *
 *   # Dry run (default): prints what would be sent, sends nothing
 *   bun run scripts/flush-email-queue.ts
 *
 *   # Real run: sends pending digests and marks the queue rows
 *   bun run scripts/flush-email-queue.ts --send
 *
 * Options:
 *   --send            Actually send and flip queue rows (default: dry run)
 *   --db <url>        Override DATABASE_URL (e.g. file:local.db for testing)
 *   --help
 *
 * Safety rails:
 *   - Dry run by default; --send required to send mail or touch the DB.
 *   - A failed send leaves that recipient's rows pending so the next flush
 *     retries them; other recipients still get their digest.
 *
 * Exit codes: 0 = success (or dry run), 1 = error, 2 = sent but some failed.
 */

import { config } from "dotenv";
import { resolve } from "path";

// Load .env from the frontend directory (this script reads it, not the caller).
config({ path: resolve(process.cwd(), ".env") });

import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/libsql";
import { createClient } from "@libsql/client/node";
import { emailQueue } from "../src/lib/server/database/schema";
import {
  flushEmailQueue,
  renderSingle,
  type QueueDb,
} from "../src/lib/server/email-queue";
import { userDigestTemplate } from "../src/lib/server/email-templates";

function usage(): never {
  console.log(`Usage:
  bun run scripts/flush-email-queue.ts [--send] [--db <url>]

Examples:
  bun run scripts/flush-email-queue.ts                # dry run
  bun run scripts/flush-email-queue.ts --send        # send pending digests
  bun run scripts/flush-email-queue.ts --send --db file:local.db
`);
  process.exit(0);
}

function parseArgs(argv: string[]) {
  let send = false;
  let dbUrl: string | undefined;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") usage();
    else if (arg === "--send") send = true;
    else if (arg === "--db") dbUrl = argv[++i];
    else if (arg.startsWith("--")) {
      console.error(`Unknown flag: ${arg}`);
      usage();
    }
  }
  return { send, dbUrl };
}

async function previewPending(db: QueueDb): Promise<number> {
  const rows = await db
    .select()
    .from(emailQueue)
    .where(eq(emailQueue.status, "pending"))
    .orderBy(emailQueue.createdAt);

  if (rows.length === 0) {
    console.log("No pending emails in the queue.");
    return 0;
  }

  const itemsPerRecipient = new Map<string, typeof rows>();
  for (const row of rows) {
    const bucket = itemsPerRecipient.get(row.recipientEmail) ?? [];
    bucket.push(row);
    itemsPerRecipient.set(row.recipientEmail, bucket);
  }

  for (const [email, rowsForUser] of itemsPerRecipient) {
    const items = rowsForUser.map(
      (r) =>
        r.data as Parameters<typeof userDigestTemplate>[0]["items"][number],
    );
    const subject =
      items.length === 1
        ? renderSingle(items[0]).subject
        : userDigestTemplate({ name: rowsForUser[0]?.recipientName, items })
            .subject;
    console.log(`\n📧 ${email} — ${items.length} item(s)`);
    console.log(`   Subject: ${subject}`);
    for (const r of rowsForUser) {
      console.log(`   · ${r.kind} (queued ${r.createdAt.toISOString()})`);
    }
  }

  return rows.length;
}

async function main() {
  const { send, dbUrl } = parseArgs(process.argv.slice(2));

  const databaseUrl = dbUrl ?? process.env.DATABASE_URL;
  if (!databaseUrl) {
    console.error(
      "DATABASE_URL is not set. Pass --db <url> or configure it in .env.",
    );
    process.exit(1);
  }

  const db = drizzle(createClient({ url: databaseUrl })) as QueueDb;

  if (!send) {
    await previewPending(db);
    console.log(
      "\nDry run complete. Re-run with --send to actually send the digests.",
    );
    process.exit(0);
  }

  const { sent, failed } = await flushEmailQueue(db);
  console.log(`\nSent ${sent} digest email(s), ${failed} failed.`);
  process.exit(failed > 0 ? 2 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
