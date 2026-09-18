import { describe, expect, it } from "vitest";
import type { CoffeeBean } from "$lib/api";
import { getBeanFeedbackFields } from "./beanFeedback";

function makeBean(overrides: Partial<CoffeeBean> = {}): CoffeeBean {
	return {
		description: "Test bean",
		price: 12.5,
		currency: "GBP",
		weight: 250,
		in_stock: true,
		cupping_score: 85,
		roast_level: "Light",
		roast_profile: "Filter",
		tasting_notes: [],
		origins: [],
		...overrides,
	} as CoffeeBean;
}

describe("getBeanFeedbackFields", () => {
	it("renders in_stock display exactly as the select options", () => {
		const chips = (value: boolean | null) => {
			const fields = getBeanFeedbackFields(makeBean({ in_stock: value }));
			return fields.find((f) => f.key === "in_stock");
		};

		expect(chips(true)?.value).toBe("In stock");
		expect(chips(false)?.value).toBe("Out of stock");
		expect(chips(null)?.value).toBe("—");
	});

	it("configures number fields to the CoffeeBean schema constraints", () => {
		const fields = getBeanFeedbackFields(makeBean());
		const byKey = new Map(fields.map((f) => [f.key, f.input]));

		expect(byKey.get("price")).toEqual({ type: "number", min: 0.01, step: 0.01 });
		expect(byKey.get("weight")).toEqual({ type: "number", min: 1, step: 1 });
		expect(byKey.get("cupping_score")).toEqual({
			type: "number",
			min: 70,
			max: 100,
			step: 0.5,
		});
	});

	it("routes exactly price, weight and cupping_score to the numeric input", () => {
		const fields = getBeanFeedbackFields(makeBean());
		const numberKeys = fields
			.filter((f) => f.input?.type === "number")
			.map((f) => f.key)
			.sort();

		expect(numberKeys).toEqual(["cupping_score", "price", "weight"]);
	});

	it("displays every select field as either the placeholder or one of its options", () => {
		for (const value of [true, false, null] as const) {
			const fields = getBeanFeedbackFields(makeBean({ in_stock: value }));
			for (const field of fields) {
				if (field.input?.type !== "select") continue;
				expect(
					field.value === "—" || (field.input.options as string[]).includes(field.value ?? ""),
				).toBe(true);
			}
		}
	});
});