---
type: "Reference"
title: "Roaster-Implemented Notifier Script"
description: "CLI/agentic counterpart of the admin panel's 'Mark implemented' action: flips a roaster suggestion to implemented and emails opted-in voters, with dry-run default, idempotency guard, and hard kill-switch."
---

# Roaster-Implemented Notifier Script

`frontend/scripts/notify-roaster-implemented.ts` is the CLI counterpart of the
admin panel's **Mark implemented** action
(`markSuggestionImplemented` in `src/lib/api/admin.remote.ts`). It exists so
the notification flow can be triggered agentically or from a terminal — without
a browser session or admin login.

Running it does two things, in the same order as the admin panel:

1. Flips the suggestion to `status: "implemented"` and stamps
   `implemented_roaster_slug`.
2. Emails every voter who opted in (`notify_on_implementation = 1`), plus an
   admin digest (kind `roaster-implemented`) to every admin-role user.

Emails use the same templates and SMTP transport as the app — see
[Email Notifications](email-notifications.md).

## Usage

Run from the `frontend/` directory:

```sh
# Dry run (default): no DB writes, no emails — prints exactly what would happen
bun run scripts/notify-roaster-implemented.ts <suggestionId> <roasterSlug>

# Real run: updates the DB and sends the emails
bun run scripts/notify-roaster-implemented.ts <suggestionId> <roasterSlug> --send
```

| Flag | Purpose |
|---|---|
| `--send` | Actually update the DB and send emails (default is dry run) |
| `--db <url>` | Override `DATABASE_URL` (e.g. `file:/tmp/test-copy.db` for testing) |
| `--site-url <url>` | Base URL for the voter CTA link (default `https://kissaten.app`) |
| `--help` | Show usage |

The suggestion ID is the `roaster_suggestions.id` (`sug_…`); find candidates
with:

```sh
sqlite3 "file:frontend/local.db?mode=ro" \
  "SELECT id, name, status FROM roaster_suggestions WHERE status='pending';"
```

## Safety rails

- **Dry run by default.** Nothing is written and nothing is sent unless
  `--send` is passed.
- **Hard kill-switch.** Refuses to run when `ADMIN_NOTIFICATIONS_ENABLED` is
  explicitly `"false"`/`"0"` (exit 1), matching the gate in
  `admin-notifications.ts`.
- **Idempotent.** Re-running against an already-implemented suggestion with the
  same slug is a no-op (exit 0, no re-notification). A *different* slug is
  refused (exit 1) rather than silently changed.
- **Slug validation.** The slug must match the same charset as the admin panel
  form (`/^[a-z0-9&_\-éūëöáíóúñûē']+$/`).
- **GDPR opt-in respected.** Only voters with `notify_on_implementation = 1`
  are emailed; other voters of the same suggestion are never contacted.
- **Graceful failure.** Per-recipient SMTP errors are collected and reported;
  the run completes and exits 2 rather than crashing mid-batch. The DB update
  is applied before sends are attempted (same as the admin panel).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success, dry run, or already-implemented no-op |
| 1 | Suggestion not found, invalid slug/args, DB URL missing, or hard-disabled |
| 2 | Completed, but one or more emails failed to send |

## Behaviour verified (2026 session, test copy of `local.db`)

All of the following were observed in real runs against a throwaway copy with
fixture data (2 opted-in voters, 1 non-opted) and SMTP pointed at a dead local
port so no mail could leave the machine:

- Dry run listed only the 2 opted-in voters (non-opted correctly excluded),
  rendered the subject/body preview, and left the DB untouched (exit 0).
- `--send` flipped the suggestion to `implemented` with the slug, attempted all
  sends, collected the failures, and exited 2.
- Re-run with the same slug: no-op (exit 0). Different slug: refused (exit 1).
- Unknown suggestion ID: exit 1.
- `ADMIN_NOTIFICATIONS_ENABLED=0`: refused (exit 1).

## Operational notes

- **`--db` in tests is not optional.** The script reads `DATABASE_URL` from the
  environment (shell or `.env`, loaded by the script itself via dotenv — the
  caller never needs to read credentials). If `DATABASE_URL` points at a remote
  DB, omitting `--db` during testing would run against *that* DB — always pass
  `--db file:<copy>` when practising.
- **SMTP must be configured** for `--send` to succeed: `SMTP_HOST`, `SMTP_PORT`,
  `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` (see
  [Email Notifications](email-notifications.md)). Without them, sends fail and
  the script exits 2 with the DB update already applied.
- To smoke-test the mail path end-to-end without real recipients, point SMTP at
  a dead port (`SMTP_HOST=127.0.0.1 SMTP_PORT=59999`) and confirm exit code 2
  with per-recipient `ECONNREFUSED` errors — this exercises the full render +
  send + failure-collection path safely.
- Admin digests go to every `user` with `role='admin'`; voter emails greet each
  recipient by their own name and never reveal the suggestion's submitter
  (same privacy property as the admin-panel flow).
