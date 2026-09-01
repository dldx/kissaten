import type { TastingSession } from "$lib/db/localdb";

export interface SessionGroup {
	label: string;
	sessions: TastingSession[];
}

/**
 * Group sessions into month buckets for chunking (Miller's Law).
 * Assumes input is already sorted newest-first; the returned groups
 * preserve that ordering. Sessions without a parseable date fall into
 * an "Earlier" bucket at the end.
 */
export function groupSessionsByMonth(sessions: TastingSession[]): SessionGroup[] {
	const groups: SessionGroup[] = [];
	const index = new Map<string, SessionGroup>();

	for (const session of sessions) {
		const date = session.date ? new Date(session.date) : null;
		const valid = date && !isNaN(date.getTime());
		const label = valid
			? date.toLocaleDateString("en-GB", { month: "long", year: "numeric" })
			: "Earlier";

		let group = index.get(label);
		if (!group) {
			group = { label, sessions: [] };
			index.set(label, group);
			groups.push(group);
		}
		group.sessions.push(session);
	}

	return groups;
}

export function formatShortDate(date: Date | undefined | null): string {
	if (!date) return "Date unknown";
	const d = date instanceof Date ? date : new Date(date);
	if (isNaN(d.getTime())) return "Date unknown";
	return d.toLocaleDateString("en-GB", {
		day: "numeric",
		month: "short",
		year: "numeric",
	});
}

/**
 * Compact relative time label for a millisecond timestamp:
 * "just now" (<2 min), "Xm ago" (<60 min), "Xh ago" (<24 h), "Xd ago" (<30 d),
 * then falls back to an absolute short date.
 */
export function formatRelativeAge(timestampMs: number): string {
	if (!timestampMs || isNaN(timestampMs)) {
		return formatShortDate(new Date(timestampMs));
	}
	const diffMs = Date.now() - timestampMs;
	const minutes = Math.floor(diffMs / 60_000);
	if (minutes < 2) return "just now";
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	if (days < 30) return `${days}d ago`;
	return formatShortDate(new Date(timestampMs));
}

export function formatRelative(date: Date | string | number): string {
	const d = new Date(date);
	const diffMs = Date.now() - d.getTime();
	const sec = Math.floor(diffMs / 1000);
	if (sec < 60) return "just now";
	const min = Math.floor(sec / 60);
	if (min < 60) return `${min}m ago`;
	const hr = Math.floor(min / 60);
	if (hr < 24) return `${hr}h ago`;
	const day = Math.floor(hr / 24);
	if (day < 30) return `${day}d ago`;
	return d.toLocaleDateString();
}

export function formatAbsolute(date: Date | string | number): string {
	return new Date(date).toLocaleString();
}
