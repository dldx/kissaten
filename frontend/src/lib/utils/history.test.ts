import { describe, expect, it } from "vitest";
import type { TastingSession } from "$lib/db/localdb";
import { groupSessionsByMonth, formatShortDate } from "./history";

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
