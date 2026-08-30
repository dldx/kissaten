import {
	TASTING_CONVERSATION,
	DEFECT_CONVERSATION,
	type TastingConversationCategory,
} from "./conversation";
import { noteToCategoryMap } from "$lib/stores/tastingNotesStore.svelte";

/**
 * The categorized view of a flat list of tasting notes, derived by looking each
 * note up in the conversation skeleton (via name/flavor/subType match), falling
 * back to the API's note-to-category map, and finally an "other" catch-all
 * bucket. Defect notes are grouped under the "defects" category id.
 */
export interface ReconstructedTasting {
	categoryIds: string[];
	notes: Record<string, string[]>;
	subCategoryIds: Record<string, string[]>;
	orderedNotes: string[];
}

/**
 * Reconstruct the wizard's categorized state from a flat list of tasting notes
 * (as stored on a `TastingSession`). `orderedNotes` is the input list unchanged.
 *
 * Notes that equal a category name only register the category id (no specific
 * note); notes that equal a sub-category name register `subCategoryIds[catId]`
 * but no specific note; specific flavors register `notes[catId]`.
 */
export function reconstructTastingState(
	allSelectedNotesList: string[],
	conversation: TastingConversationCategory[] = TASTING_CONVERSATION,
): ReconstructedTasting {
	const effectiveNotesList =
		allSelectedNotesList.length > 0 ? allSelectedNotesList : [];

	const categories = [...conversation, ...DEFECT_CONVERSATION];
	const categoryIds: string[] = [];
	const notes: Record<string, string[]> = {};
	const subCategoryIds: Record<string, string[]> = {};

	// Respect the order of the flat list while still identifying categories for styling
	for (const noteName of effectiveNotesList) {
		const cat = categories.find(
			(c) =>
				c.name === noteName ||
				c.flavors?.some(
					(f) => (typeof f === "string" ? f : f.name) === noteName,
				) ||
				c.subTypes?.some(
					(s) =>
						s.name === noteName ||
						s.flavors.some(
							(f) =>
								(typeof f === "string" ? f : f.name) ===
								noteName,
						),
				),
		);

		// Found in the conversation skeleton
		if (cat) {
			const targetCatId = cat.isDefect ? "defects" : cat.id;
			if (
				targetCatId !== "defects" &&
				!categoryIds.includes(targetCatId)
			) {
				categoryIds.push(targetCatId);
			}

			const sub = cat.subTypes?.find(
				(s) =>
					s.name === noteName ||
					s.flavors.some(
						(f) =>
							(typeof f === "string" ? f : f.name) === noteName,
					),
			);

			if (sub) {
				if (!subCategoryIds[targetCatId])
					subCategoryIds[targetCatId] = [];
				if (!subCategoryIds[targetCatId].includes(sub.id)) {
					subCategoryIds[targetCatId].push(sub.id);
				}

				const isSpecificFlavor =
					sub.flavors.some(
						(f) =>
							(typeof f === "string" ? f : f.name) === noteName,
					) && noteName !== sub.name;
				if (isSpecificFlavor) {
					if (!notes[targetCatId]) notes[targetCatId] = [];
					if (!notes[targetCatId].includes(noteName))
						notes[targetCatId].push(noteName);
				}
			} else {
				const isSpecificFlavor =
					cat.flavors?.some(
						(f) =>
							(typeof f === "string" ? f : f.name) === noteName,
					) && noteName !== cat.name;
				if (isSpecificFlavor) {
					if (!notes[targetCatId]) notes[targetCatId] = [];
					if (!notes[targetCatId].includes(noteName))
						notes[targetCatId].push(noteName);
				}
			}
		} else {
			// Fallback: try the API's note-to-category map (primaryCategory is the category name e.g. "Fruity")
			const apiCategoryName = noteToCategoryMap[noteName.toLowerCase()];
			const apiCat = apiCategoryName
				? conversation.find(
						(c) =>
							c.name.toLowerCase() ===
							apiCategoryName.toLowerCase(),
					)
				: null;

			if (apiCat) {
				const targetCatId = apiCat.id;
				if (!categoryIds.includes(targetCatId))
					categoryIds.push(targetCatId);
				if (!notes[targetCatId]) notes[targetCatId] = [];
				if (!notes[targetCatId].includes(noteName))
					notes[targetCatId].push(noteName);
			} else {
				// Last resort: unknown note goes into a catch-all bucket
				if (!notes["other"]) notes["other"] = [];
				if (!notes["other"].includes(noteName))
					notes["other"].push(noteName);
				if (!categoryIds.includes("other"))
					categoryIds.push("other");
			}
		}
	}

	return {
		categoryIds,
		notes,
		subCategoryIds,
		orderedNotes: effectiveNotesList,
	};
}