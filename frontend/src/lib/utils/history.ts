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
