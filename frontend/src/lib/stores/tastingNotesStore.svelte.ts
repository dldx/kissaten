import type { TastingNoteCategoriesResponse } from "$lib/api";
import { CATEGORY_MAPPINGS } from "$lib/tasting/conversation";

/**
 * Reverse of CATEGORY_MAPPINGS: apiKey → conversationName
 * e.g. "Spices" → "Spicy"
 */
const API_KEY_TO_CONVERSATION_NAME: Record<string, string> = Object.fromEntries(
	Object.entries(CATEGORY_MAPPINGS).map(([convName, apiKey]) => [apiKey, convName])
);

/**
 * A flat map from note name (lowercase) → conversation category name (e.g. "Spicy", "Fruity").
 * Populated by the /tasting layout on mount and used by TastingSummaryCard for display.
 */
export const noteToCategoryMap = $state<Record<string, string>>({});

/**
 * Populate the store from an API response.
 * Inverts the categories structure into a flat note → conversationCategoryName lookup,
 * normalizing API keys (e.g. "Spices") back to conversation names (e.g. "Spicy").
 */
export function populateNoteCategoryMap(data: TastingNoteCategoriesResponse) {
	for (const [apiKey, entries] of Object.entries(data.categories)) {
		// Normalize to the conversation name (e.g. "Spices" → "Spicy"), or use the API key as-is
		const conversationName = API_KEY_TO_CONVERSATION_NAME[apiKey] ?? apiKey;

		for (const entry of entries) {
			for (const note of entry.tasting_notes) {
				noteToCategoryMap[note.toLowerCase()] = conversationName;
			}
		}
	}
}
