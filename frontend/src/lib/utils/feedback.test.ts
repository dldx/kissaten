import { describe, expect, it } from "vitest";
import { toSuggestedValue } from "./feedback";

describe("toSuggestedValue", () => {
	it("trims and stringifies numbers", () => {
		expect(toSuggestedValue("  250  ")).toBe("250");
		expect(toSuggestedValue(250)).toBe("250");
		expect(toSuggestedValue(12.5)).toBe("12.5");
		expect(toSuggestedValue(0)).toBe("0");
	});

	it("returns undefined for absent, empty, or whitespace-only values", () => {
		expect(toSuggestedValue(null)).toBeUndefined();
		expect(toSuggestedValue(undefined)).toBeUndefined();
		expect(toSuggestedValue("")).toBeUndefined();
		expect(toSuggestedValue("   ")).toBeUndefined();
	});

	it("returns undefined for non-finite numbers", () => {
		expect(toSuggestedValue(NaN)).toBeUndefined();
		expect(toSuggestedValue(Infinity)).toBeUndefined();
		expect(toSuggestedValue(-Infinity)).toBeUndefined();
	});
});
