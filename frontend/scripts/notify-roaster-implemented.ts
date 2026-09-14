/**
 * Agentic/CLI counterpart of the admin panel's "Mark implemented" action for
 * roaster suggestions (see markSuggestionImplemented in
 * src/lib/api/admin.remote.ts).
 *
 * Marks a roaster suggestion as implemented and emails every voter who opted
 * in to implementation notifications, exactly like the admin panel does. The
 * .env file is loaded by this script itself, so callers (e.g. coding agents)
 * never need to read SMTP credentials directly.
 *
 * Usage (run from the frontend/ directory):
 *
 *   # Dry run (default): no DB writes, no emails — prints what would happen
 *   bun run scripts/notify-roaster-implemented.ts <suggestionId> <roasterSlug>
 *
 *   # Real run: flips the suggestion to implemented and sends the emails
 *   bun run scripts/notify-roaster-implemented.ts <suggestionId> <roasterSlug> --send
 *
 * Options:
 *   --send            Actually update the DB and send emails (default: dry run)
 *   --db <url>        Override DATABASE_URL (e.g. file:local.db for testing)
 *   --site-url <url>  Base URL for the voter CTA link (default: https://kissaten.app)
 *   --help
 *
 * Safety rails:
 *   - Dry run by default; --send is required to touch the DB or send mail.
 *   - Hard-disabled when ADMIN_NOTIFICATIONS_ENABLED is explicitly "false"/"0".
 *   - Idempotent: refuses to re-notify a suggestion already marked implemented
 *     (mirrors the admin panel).
 *   - Validates the slug charset exactly like the admin panel form.
 *   - Respects the GDPR opt-in: only voters with notify_on_implementation = 1
 *     are emailed.
 *
 * Exit codes: 0 = success (or dry run), 1 = suggestion not found / invalid
 * input / hard-disabled, 2 = completed but one or more emails failed to send.
 */

import { config } from 'dotenv';
import { resolve } from 'path';

// Load .env from the frontend directory (this script reads it, not the caller).
config({ path: resolve(process.cwd(), '.env') });

import { and, eq } from 'drizzle-orm';
import { drizzle } from 'drizzle-orm/libsql';
import { createClient } from '@libsql/client/node';
import {
	roasterSuggestionVotes,
	roasterSuggestions,
	user
} from '../src/lib/server/database/schema';
import { sendEmail } from '../src/lib/server/email';
import {
	adminNotificationTemplate,
	roasterImplementedUserTemplate,
	ADMIN_NOTIFICATION_LOGO_ATTACHMENT,
	USER_EMAIL_LOGO_ATTACHMENT
} from '../src/lib/server/email-templates';

const SLUG_REGEX = /^[a-z0-9&_\-éūëöáíóúñûē']+$/;

function usage(): never {
	console.log(`Usage:
  bun run scripts/notify-roaster-implemented.ts <suggestionId> <roasterSlug> [--send] [--db <url>] [--site-url <url>]

Examples:
  bun run scripts/notify-roaster-implemented.ts sug_abc123 "coffee-circle"
  bun run scripts/notify-roaster-implemented.ts sug_abc123 "coffee-circle" --send
  bun run scripts/notify-roaster-implemented.ts sug_abc123 "coffee-circle" --send --db file:local.db
`);
	process.exit(0);
}

function parseArgs(argv: string[]) {
	const positional: string[] = [];
	let send = false;
	let dbUrl: string | undefined;
	let siteUrl = 'https://kissaten.app';

	for (let i = 0; i < argv.length; i++) {
		const arg = argv[i];
		if (arg === '--help' || arg === '-h') usage();
		else if (arg === '--send') send = true;
		else if (arg === '--db') dbUrl = argv[++i];
		else if (arg === '--site-url') siteUrl = argv[++i].replace(/\/+$/, '');
		else if (arg.startsWith('--')) {
			console.error(`Unknown flag: ${arg}`);
			usage();
		} else positional.push(arg);
	}

	if (positional.length !== 2) {
		console.error('Exactly two positional arguments are required: <suggestionId> <roasterSlug>');
		usage();
	}
	return { suggestionId: positional[0], roasterSlug: positional[1], send, dbUrl, siteUrl };
}

async function main() {
	const { suggestionId, roasterSlug, send, dbUrl, siteUrl } = parseArgs(process.argv.slice(2));

	const databaseUrl = dbUrl ?? process.env.DATABASE_URL;
	if (!databaseUrl) {
		console.error('DATABASE_URL is not set. Pass --db <url> or configure it in .env.');
		process.exit(1);
	}

	// Hard kill-switch, matching admin-notifications.isEnabled().
	const rawEnabled = process.env.ADMIN_NOTIFICATIONS_ENABLED;
	if (rawEnabled === 'false' || rawEnabled === '0') {
		console.error('ADMIN_NOTIFICATIONS_ENABLED is explicitly disabled; refusing to run.');
		process.exit(1);
	}

	// Same slug charset validation as the admin panel form.
	if (!SLUG_REGEX.test(roasterSlug)) {
		console.error(`Invalid roaster slug: "${roasterSlug}"`);
		process.exit(1);
	}

	const db = drizzle(createClient({ url: databaseUrl }));

	const [suggestion] = await db
		.select({
			id: roasterSuggestions.id,
			name: roasterSuggestions.name,
			status: roasterSuggestions.status,
			implementedRoasterSlug: roasterSuggestions.implementedRoasterSlug,
			submittedByEmail: user.email
		})
		.from(roasterSuggestions)
		.leftJoin(user, eq(user.id, roasterSuggestions.userId))
		.where(eq(roasterSuggestions.id, suggestionId))
		.limit(1);

	if (!suggestion) {
		console.error(`Suggestion not found: ${suggestionId}`);
		process.exit(1);
	}

	console.log(`Suggestion : ${suggestion.name} (${suggestion.id})`);
	console.log(`Status     : ${suggestion.status}`);
	console.log(`Roaster    : ${roasterSlug}`);
	console.log(`Mode       : ${send ? 'SEND' : 'DRY RUN (no writes, no emails)'}`);
	console.log('');

	// Idempotency, mirroring the admin panel: never re-notify an implemented suggestion.
	if (suggestion.status === 'implemented') {
		if (suggestion.implementedRoasterSlug === roasterSlug) {
			console.log('Already implemented with this slug; nothing to do.');
			process.exit(0);
		}
		console.error(
			`Suggestion is already implemented with slug "${suggestion.implementedRoasterSlug}"; refusing to change it.`
		);
		process.exit(1);
	}

	const votingUsers = await db
		.select({ email: user.email, name: user.name })
		.from(roasterSuggestionVotes)
		.innerJoin(user, eq(user.id, roasterSuggestionVotes.userId))
		.where(
			and(
				eq(roasterSuggestionVotes.suggestionId, suggestionId),
				eq(roasterSuggestionVotes.notifyOnImplementation, true)
			)
		);

	const recipients = votingUsers.filter((r) => !!r.email);
	const roasterUrl = `${siteUrl}/roasters/${roasterSlug}`;
	const sampleRender = roasterImplementedUserTemplate({
		name: recipients[0]?.name ?? null,
		roasterName: suggestion.name,
		roasterUrl
	});

	console.log(`Opted-in voters to notify: ${recipients.length}`);
	for (const r of recipients) {
		console.log(`  - ${r.email}${r.name ? ` (${r.name})` : ''}`);
	}
	if (recipients.length > 0) {
		console.log('');
		console.log(`Subject: ${sampleRender.subject}`);
		console.log('--- text preview ---');
		console.log(sampleRender.text);
	}
	console.log('');

	if (!send) {
		console.log('Dry run complete. Re-run with --send to update the DB and send the emails.');
		process.exit(0);
	}

	// 1. Flip the suggestion to implemented (same as the admin panel action).
	await db
		.update(roasterSuggestions)
		.set({
			status: 'implemented',
			implementedRoasterSlug: roasterSlug,
			updatedAt: new Date()
		})
		.where(eq(roasterSuggestions.id, suggestionId));
	console.log('✅ Suggestion marked as implemented.');

	// 2. Email opted-in voters. Collect failures but keep going.
	let failures = 0;
	for (const recipient of recipients) {
		const rendered = roasterImplementedUserTemplate({
			name: recipient.name,
			roasterName: suggestion.name,
			roasterUrl
		});
		try {
			await sendEmail({
				to: recipient.email as string,
				subject: rendered.subject,
				text: rendered.text,
				html: rendered.html,
				attachments: [USER_EMAIL_LOGO_ATTACHMENT]
			});
			console.log(`📧 Sent to ${recipient.email}`);
		} catch (err) {
			failures++;
			console.error(`❌ Failed to send to ${recipient.email}:`, err);
		}
	}

	// 3. Notify admins (same template the admin panel uses).
	const admins = (
		await db.select({ email: user.email }).from(user).where(eq(user.role, 'admin'))
	)
		.map((r) => r.email)
		.filter((e) => !!e);
	const adminRendered = adminNotificationTemplate({
		kind: 'roaster-implemented',
		data: {
			email: suggestion.submittedByEmail ?? '',
			roasterName: suggestion.name,
			roasterSlug
		}
	});
	for (const adminEmail of admins) {
		try {
			await sendEmail({
				to: adminEmail as string,
				subject: adminRendered.subject,
				text: adminRendered.text,
				html: adminRendered.html,
				attachments: [ADMIN_NOTIFICATION_LOGO_ATTACHMENT]
			});
			console.log(`📧 Admin notified: ${adminEmail}`);
		} catch (err) {
			failures++;
			console.error(`❌ Failed to notify admin ${adminEmail}:`, err);
		}
	}

	console.log('');
	if (failures > 0) {
		console.error(`Done with ${failures} email failure(s). DB update was applied.`);
		process.exit(2);
	}
	console.log('Done: suggestion implemented, voters and admins notified.');
	process.exit(0);
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
