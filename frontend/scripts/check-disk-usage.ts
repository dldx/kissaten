/**
 * Disk usage alert for the data drive — checks the filesystem containing a
 * target path and emails the recipient from ALERT_EMAIL_TO in frontend/.env
 * (or --to) when usage crosses an escalating threshold. Uses the existing
 * nodemailer email client (src/lib/server/email.ts); SMTP credentials and the
 * recipient come from frontend/.env, which this script loads itself so
 * callers (e.g. cron) never need them.
 *
 * Usage (run from the frontend/ directory):
 *
 *   # Dry run (default): prints status, never sends email or writes state
 *   bun run scripts/check-disk-usage.ts
 *
 *   # Real run: sends email and records state (intended for cron)
 *   bun run scripts/check-disk-usage.ts --send
 *
 * Options:
 *   --send          Actually send email and update state (default: dry run)
 *   --path <p>      Path whose filesystem to check (default: /home/ubuntu/kissaten/data)
 *   --to <email>    Recipient (default: ALERT_EMAIL_TO from frontend/.env)
 *   --state <file>  State file (default: ../logs/disk-usage-state.json)
 *   --help
 *
 * Alert levels: 85% → 90% → 95% → 99%. Each new higher level sends one email.
 * A "recovered" email is sent once usage falls 5 points below the last alerted
 * threshold (hysteresis), and the level resets. A failed send never advances
 * state, so the next cron run retries.
 *
 * Exit codes: 0 = ok / dry run, 1 = error, 2 = email(s) failed to send.
 */

import { config } from 'dotenv';
import { resolve } from 'path';
import { statfs } from 'fs/promises';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';

// Load .env from the frontend directory (this script reads it, not the caller).
config({ path: resolve(process.cwd(), '.env') });

import { sendEmail } from '../src/lib/server/email';

const DEFAULT_PATH = '/home/ubuntu/kissaten/data';
const THRESHOLDS = [85, 90, 95, 99];
const RECOVERY_MARGIN = 5;

interface State {
	level: number; // index into THRESHOLDS of the last alerted threshold
	updatedAt: string;
}

function parseArgs(argv: string[], defaultTo: string) {
	const args: { send: boolean; path: string; to: string; state: string } = {
		send: false,
		path: DEFAULT_PATH,
		to: defaultTo,
		state: resolve(process.cwd(), '../logs/disk-usage-state.json')
	};
	for (let i = 2; i < argv.length; i++) {
		const a = argv[i];
		if (a === '--send') args.send = true;
		else if (a === '--path') args.path = argv[++i];
		else if (a === '--to') args.to = argv[++i];
		else if (a === '--state') args.state = argv[++i];
		else if (a === '--help') {
			console.log('Usage: bun run scripts/check-disk-usage.ts [--send] [--path <p>] [--to <email>] [--state <file>]');
			process.exit(0);
		} else {
			console.error(`Unknown argument: ${a}`);
			process.exit(1);
		}
	}
	return args;
}

function loadState(file: string): State {
	try {
		if (existsSync(file)) return JSON.parse(readFileSync(file, 'utf8')) as State;
	} catch {
		// Corrupt state file — treat as fresh.
	}
	return { level: 0, updatedAt: new Date().toISOString() };
}

function saveState(file: string, state: State) {
	mkdirSync(resolve(file, '..'), { recursive: true });
	writeFileSync(file, JSON.stringify(state, null, 2) + '\n');
}

function pct(bytes: number): string {
	return (bytes / 1024 ** 3).toFixed(1) + ' GB';
}

function fmt(device: string, mount: string, used: number, total: number, free: number, usage: number): string {
	return [
		`Filesystem:  ${device}`,
		`Mount:       ${mount}`,
		`Usage:       ${usage}%`,
		`Used:        ${pct(used)} of ${pct(total)}`,
		`Free:        ${pct(free)}`
	].join('\n');
}

/** Longest mount point in /proc/mounts that contains path → its device. */
function findMount(path: string): { device: string; mount: string } {
	let best = { device: '?', mount: '/' };
	try {
		for (const line of readFileSync('/proc/mounts', 'utf8').split('\n')) {
			const [device, mount] = line.split(' ');
			if (!device || !mount) continue;
			if ((path === mount || path.startsWith(mount === '/' ? '/' : mount + '/')) && mount.length >= best.mount.length) {
				best = { device, mount };
			}
		}
	} catch {
		// /proc/mounts unavailable — fall back to defaults above.
	}
	return best;
}

async function main() {
	const defaultTo = process.env.ALERT_EMAIL_TO;
	if (!defaultTo) {
		console.error('❌ ALERT_EMAIL_TO is not set — add it to frontend/.env (recipient for disk usage alerts).');
		process.exit(1);
	}

	const args = parseArgs(process.argv, defaultTo);

	const stats = await statfs(args.path);
	const total = stats.blocks * stats.bsize;
	const free = stats.bavail * stats.bsize;
	const used = total - free;
	const usage = Math.round((used / total) * 100);

	const state = loadState(args.state);
	const currentLevel = THRESHOLDS.filter((t) => usage >= t).length;

	const alerted = THRESHOLDS[state.level - 1];
	const recovery = state.level > 0 && usage < alerted - RECOVERY_MARGIN;
	const shouldAlert = currentLevel > state.level;
	const shouldRecover = recovery && !shouldAlert;

	const { device, mount } = findMount(args.path);
	console.log(fmt(device, mount, used, total, free, usage));
	console.log(`Alert level: ${state.level}/${THRESHOLDS.length}, current usage level: ${currentLevel}/${THRESHOLDS.length}`);

	if (!shouldAlert && !shouldRecover) {
		console.log('Nothing to do.');
		return;
	}

	const host = process.env.HOSTNAME ?? 'kissaten';
	const subject = shouldAlert
		? `⚠️ ${host}: data drive at ${usage}% (${THRESHOLDS[currentLevel - 1]}% threshold)`
		: `✅ ${host}: data drive recovered — now at ${usage}%`;

	const text = shouldAlert
		? `The data drive on ${host} is filling up.\n\n${fmt(device, mount, used, total, free, usage)}\n\nOnce it is full, scrapers and the database will start failing.\nConsider pruning old sessions in data/roasters/ or expanding the volume.`
		: `Disk usage on ${host} has recovered.\n\n${fmt(device, mount, used, total, free, usage)}`;

	if (!args.send) {
		console.log(`Dry run — would send to ${args.to}:\n${subject}\n`);
		console.log(text);
		return;
	}

	try {
		await sendEmail({
			to: args.to,
			subject,
			text,
			html: `<pre style="font:13px ui-monospace,monospace">${text}</pre>`
		});
		console.log(`📧 Sent to ${args.to}: ${subject}`);
	} catch (err) {
		console.error('❌ Failed to send alert email:', err);
		process.exit(2);
	}

	saveState(args.state, { level: currentLevel, updatedAt: new Date().toISOString() });
	console.log(`State saved: level ${currentLevel} → ${args.state}`);
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
