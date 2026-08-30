import { describe, expect, it } from "vitest";
import type { TastingSession } from "$lib/db/localdb";
import { groupSessionsByMonth, formatShortDate, formatRelativeAge } from "./history";

function session(date: string | Date, name: string): TastingSession {
	return { date: date instanceof Date ? date : new Date(date), name, selectedNotes: [] };
}

describe("groupSessionsByMonth", () => {
	it("groups sessions by month label, preserving input order", () => {
		const groups = groupSessionsByMonth([
			session("2026-08-12T09:00:00", "Aug session"),
			session("2026-08-01T09:00:00", "Earlier Aug"),
			session("2026-07-20T09:00:00", "July session"),
		]);

		expect(groups.map((g) => g.label)).toEqual(["August 2026", "July 2026"]);
		expect(groups[0].sessions.map((s) => s.name)).toEqual([
			"Aug session",
			"Earlier Aug",
		]);
		expect(groups[1].sessions.map((s) => s.name)).toEqual(["July session"]);
	});

	it("returns an empty array for no sessions", () => {
		expect(groupSessionsByMonth([])).toEqual([]);
	});

	it("collects sessions with invalid dates into an 'Earlier' bucket", () => {
		const groups = groupSessionsByMonth([
			session("not-a-date", "Bad date"),
			session("2026-08-12T09:00:00", "Good date"),
		]);
		// Order of first appearance is preserved, so the bad-date session
		// keeps its original leading position.
		expect(groups.map((g) => g.label)).toEqual(["Earlier", "August 2026"]);
	});
});

describe("formatShortDate", () => {
	it("formats a valid date in en-GB short form", () => {
		expect(formatShortDate(new Date("2026-08-12T09:00:00"))).toMatch(
			/^\d{1,2} Aug 2026$/,
		);
	});

	it("handles null and invalid dates gracefully", () => {
		expect(formatShortDate(null)).toBe("Date unknown");
		expect(formatShortDate(new Date("garbage"))).toBe("Date unknown");
	});
});

describe("formatRelativeAge", () => {
	const now = Date.now();
	const minutesAgo = (mins: number) => now - mins * 60_000;

	it("produces compact relative labels", () => {
		expect(formatRelativeAge(now)).toBe("just now");
		expect(formatRelativeAge(minutesAgo(1))).toBe("just now");
		expect(formatRelativeAge(minutesAgo(5))).toBe("5m ago");
		expect(formatRelativeAge(minutesAgo(59))).toBe("59m ago");
		expect(formatRelativeAge(minutesAgo(60))).toBe("1h ago");
		expect(formatRelativeAge(minutesAgo(60 * 23))).toBe("23h ago");
		expect(formatRelativeAge(minutesAgo(60 * 24))).toBe("1d ago");
		expect(formatRelativeAge(minutesAgo(60 * 24 * 29))).toBe("29d ago");
	});

	it("falls back to an absolute date beyond 30 days", () => {
		const ts = minutesAgo(60 * 24 * 31);
		expect(formatRelativeAge(ts)).toBe(formatShortDate(new Date(ts)));
		expect(formatRelativeAge(ts)).toMatch(/^\d{1,2} [A-Za-z]{3} \d{4}$/);
	});

	it("handles invalid timestamps defensively", () => {
		expect(formatRelativeAge(NaN)).toBe("Date unknown");
	});
});
