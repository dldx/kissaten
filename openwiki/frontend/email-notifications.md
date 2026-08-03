---
type: "Reference"
title: "Email Notifications"
description: "Kissaten email system: nodemailer SMTP transporter, the single branded email shell in email-templates.ts, admin digest notifications, and user-facing transactional emails (magic-link OTP, beta approval, roaster-implemented to opted-in voters)."
---

# Email Notifications

Kissaten sends two categories of email, all rendered through one branded shell
and delivered by a single nodemailer SMTP transporter:

- **Admin digests** — convenience notifications to every user with the `admin`
  role, triggered by community activity (sign-ups, suggestions, feedback, etc.).
- **User-facing emails** — transactional emails to individual users themselves
  (sign-in, beta approval, roaster-implemented).

All mail code lives in `frontend/src/lib/server/`.

## Files

| File | Responsibility |
|---|---|
| `email.ts` | SMTP transporter factory (`createEmailTransporter`) and `sendEmail` wrapper (nodemailer) |
| `email-templates.ts` | `kissatenEmailTemplate` branded shell, the admin notification `meta` registry, and user-facing templates |
| `admin-notifications.ts` | Notification functions that resolve recipients and fire `sendEmail` |
| `test-email.ts` | Standalone script to verify the SMTP connection and send a test message (`bun run src/lib/server/test-email.ts` from `frontend/`) |

## SMTP Configuration (`email.ts`)

`createEmailTransporter` reads, and requires, these environment variables
(it throws if the host, username, or password is missing):

- `SMTP_HOST` — SMTP server hostname (e.g. `smtp.gmail.com`)
- `SMTP_PORT` — port (`587` TLS / `465` SSL; `secure` is inferred from a 465 port)
- `SMTP_USER` — SMTP authentication username
- `SMTP_PASS` — SMTP authentication password
- `SMTP_FROM` — default sender address (required by `sendEmail`)

The transporter is created fresh on every `sendEmail` call. Sending logs the
SMTP stream ID (`info.messageId`) on success and rethrows on failure.

## The Branded Shell (`kissatenEmailTemplate`)

Every email — admin and user — renders through `kissatenEmailTemplate` in
`email-templates.ts`. It produces plain-text and HTML bodies from a shared
`KissatenEmailData` shape (subject, accent colour, header title, greeting,
paragraphs, optional monospace `details` block, `When:` timestamp, CTA button,
and footer). Points to note:

- Untrusted free-text (roaster names, feedback messages) is sanitised: `cleanText`
  strips control characters and collapses whitespace so it is safe to embed in a
  Subject line, and `escapeHtml` escapes all HTML in the body/template.
- All user-controlled values that end up in HTML are escaped; URLs in CTA links
  are escaped as attribute values.
- A Kissaten logo is attached as a CID image (`cid:logo@kissaten.app`) via the
  `*_LOGO_ATTACHMENT` constants for both admin (`ADMIN_NOTIFICATION_LOGO_ATTACHMENT`)
  and user (`USER_EMAIL_LOGO_ATTACHMENT`) mail.

## Admin Digests (`admin-notifications.ts`)

`broadcast()` resolves the recipient list by querying every user whose role is
`admin`, then sends the same rendered digest to each. Recipient addresses and
the actor's identity are resolved from the database at runtime — nothing PII is
hard-coded in the codebase.

### Enable switch

`isEnabled()` is the global gate:

- `ADMIN_NOTIFICATIONS_ENABLED` explicitly set to `true`/`1` → enabled
- `ADMIN_NOTIFICATIONS_ENABLED` unset → enabled only when `NODE_ENV === "production"`
- anything else → disabled

All notification functions no-op (or skip) when disabled, or when no admin
users exist (a warning is logged in that case).

### Notification kinds

Each kind is defined in the `meta` registry in `email-templates.ts` with a
subject, title, accent colour, emoji, summary, `details` block, and a CTA that
links to `https://kissaten.app/admin`. The admin digest subject also carries
the acting user's email and an ISO timestamp.

| Kind | Trigger | Payload gleaned from | Files |
|---|---|---|---|
| `new-signup` | A new user account is created | the created user's email/name | better-auth `databaseHooks.user.create.after` in `server/auth.ts` |
| `beta-request` | A user expresses beta interest without approval | the user's email/name | `notifyAdminBetaRequest` in `profile.remote.ts` |
| `roaster-suggestion` | A community member submits a new roaster suggestion | submitter's email/name, suggested roaster name, country, website | `notifyAdminRoasterSuggestion` in `roaster_suggestions.remote.ts` |
| `roaster-implemented` | An admin marks a suggestion implemented | suggested roaster name + slug, submitter's email | `notifyAdminSuggestionImplemented` in `admin.remote.ts` |
| `page-feedback` | A user files page feedback | reporter's email/name, page/entity, kind, field changes, free-text message | `notifyAdminPageFeedback` in `feedback.remote.ts` |
| `newsletter-subscribed` / `newsletter-unsubscribed` | A user toggles the newsletter preference | the user's email/name and the action | `notifyAdminNewsletterChange` in `profile.remote.ts` |

Because the digest contains the acting user's email address and any message
body, admin notifications are strictly internal — they are only ever sent to
admin-role users, never broadcast to the public.

## User-Facing Emails

Sent to a single recipient (the user themselves).

- **Magic-link / OTP sign-in** (`server/auth.ts` `sendMagicLink`) — sends the
  one-time verification code plus a link to `/login/verify`. Triggered by every
  magic-link sign-in attempt.
- **Beta approved** (`notifyUserBetaApproved`) — sent when an admin approves a
  beta applicant (`approveBetaTester` in `admin.remote.ts`). Greets the user by
  name and links to `/profile` to enable beta features.
- **Roaster implemented to voters** (`notifyVotersSuggestionImplemented`) — sent
  to every voter who cast a vote with `notifyOnImplementation = true` when the
  suggestion is marked implemented. See below.

## The Roaster-Implemented Flow

Both the admin digest and the opted-in voter emails fire from
`markSuggestionImplemented` in `admin.remote.ts`:

1. The suggestion is updated to `status: "implemented"` with
   `implementedRoasterSlug`.
2. **Idempotency guard** — if the suggestion was already `implemented`, the
   action returns early and re-notifies nobody (a re-save never re-sends).
3. `notifyAdminSuggestionImplemented` broadcasts the digest to admins.
4. Voters who opted in are queried (`roasterSuggestionVotes` joined to `user`
   where `notifyOnImplementation = true`), then each is emailed individually.

### Voter email content (and what it does NOT say)

The voter template (`roasterImplementedUserTemplate`) is deliberately
community-flavoured:

- Subject: `A roaster you requested is now on Kissaten — <roaster name>`
- Body greets the recipient by **their own** name and says the roaster was
  "requested by the community" — it never names the submitter, and the CTA links
  to the roaster page (`/roasters/<slug>`).

The receiving voter's name and email come from their own `user` row at send
time. The suggestion's submitter identity is only ever surfaced inside the
**admin** digest (`roaster-implemented` → "Submitted by: …"), so opted-in voters
are never told who submitted the suggestion.

## Testing

- `bun run src/lib/server/test-email.ts` from `frontend/` verifies the SMTP
  connection and sends a test message (requires `SMTP_*` in `frontend/.env`).
- Notifications are fire-and-forget (`void …`); per-recipient send errors are
  caught and logged (`[admin-notifications] …`) without failing the request.
- Sending is deferred/bulk-auditable via Sentry/Logfire logging from the
  `sendEmail` wrapper's console output; there is no dedicated email queue — all
  sends are synchronous within the request lifecycle (fire-and-forget).
