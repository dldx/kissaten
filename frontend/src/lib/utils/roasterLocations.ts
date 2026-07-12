/**
 * Shared helpers for roaster location option display.
 *
 * Roaster location options produced by `+layout.ts` take the shape
 * `{ value: code, text: "Location Name (count)" }` (e.g.
 * `{ value: "XE", text: "Europe (33)" }`). These helpers resolve a
 * location code to its human-readable name for inline UI copy such as
 * placeholders and filter tags.
 */

export interface RoasterLocationOption {
	value: string;
	text: string;
}

/**
 * Strip the trailing roaster-count suffix (e.g. " (33)") and any
 * legacy "CODE - " prefix from a roaster location option's `text`
 * field, returning just the location name.
 *
 * @example
 *   locationDisplayName("Europe (33)")        // "Europe"
 *   locationDisplayName("GB - United Kingdom (12)") // "United Kingdom"
 *   locationDisplayName("Europe")             // "Europe"
 */
export function locationDisplayName(text: string): string {
	return text
		.replace(/^[A-Z]{2}\s*-\s*/, "")
		.replace(/\s*\(\d+\)$/, "")
		.trim();
}

/**
 * Resolve a single roaster location code to its display name, falling
 * back to the raw code when the option cannot be found.
 */
export function roasterLocationDisplayName(
	code: string,
	options: RoasterLocationOption[] | undefined | null,
): string {
	const option = options?.find((o) => o.value === code);
	if (!option) return code;
	return locationDisplayName(option.text);
}

/**
 * Resolve a list of roaster location codes to their display names,
 * preserving order. Unknown codes fall back to themselves.
 */
export function roasterLocationDisplayNames(
	codes: string[],
	options: RoasterLocationOption[] | undefined | null,
): string[] {
	return codes.map((code) => roasterLocationDisplayName(code, options));
}
