import type { SunburstData } from '$lib/types/sunburst';

interface TastingNoteCategory {
	primary_category: string;
	secondary_category: string;
	tertiary_category: string;
	note_count: number;
	bean_count: number;
	tasting_notes: string[];
	tasting_notes_with_counts: Array<{
		note: string;
		bean_count: number;
	}>;
}

interface CategoriesData {
	[primaryCategory: string]: TastingNoteCategory[];
}

/**
 * Finds or creates a node in the hierarchy.
 * A node is an object with a name and a list of children.
 */
function findOrCreateNode(name: string, parent: SunburstData): SunburstData {
    // Flatten "General" by attaching its would-be children directly to the parent
    if (name === 'General') {
        return parent;
    }
	if (!parent.children) {
		parent.children = [];
	}
	let node = parent.children.find((c) => c.name === name);
	if (!node) {
		node = { name, children: [] };
		parent.children.push(node);
	}
	return node;
}

/**
 * Finds or creates a node in the hierarchy with an optional flag.
 */
function findOrCreateNodeWithFlag(
	name: string,
	parent: SunburstData,
	isOther: boolean
): SunburstData {
	if (!parent.children) {
		parent.children = [];
	}
	let node = parent.children.find((c) => c.name === name);
	if (!node) {
		node = { name, children: [], isOther };
		parent.children.push(node);
	} else if (isOther) {
		node.isOther = true;
	}
	return node;
}

/**
 * Finds or creates a leaf node and adds value to it.
 * A leaf node has a name and a value, but no children.
 */
function findOrCreateLeaf(
	name: string,
	parent: SunburstData,
	value: number
): void {
	if (!parent.children) {
		parent.children = [];
	}
	let leaf = parent.children.find((c) => c.name === name);
	if (leaf) {
		leaf.value = (leaf.value || 0) + value;
	} else {
		leaf = { name, value };
		parent.children.push(leaf);
	}
}

/**
 * Transforms tasting note categories data into hierarchical format for sunburst chart.
 * This function builds a tree and lets D3 calculate the sums of parent nodes.
 */
export function transformToSunburstData(categories: CategoriesData): SunburstData {
	const root: SunburstData = { name: 'Tasting Notes', children: [] };
	const TASTING_NOTE_THRESHOLD = 10;

	// Process all categories and build a tree structure.
	for (const primaryKey in categories) {
		const items = categories[primaryKey];
		for (const item of items) {
			if (!item.primary_category) {
				continue;
			}
			const primaryNode = findOrCreateNode(item.primary_category, root);
			const secondaryNode = findOrCreateNode(item.secondary_category || 'General', primaryNode);
			const tertiaryNode = findOrCreateNode(item.tertiary_category || 'General', secondaryNode);

			// Add individual tasting notes as leaves, bucketing less frequent ones.
			if (item.tasting_notes_with_counts) {
				const notes = [...item.tasting_notes_with_counts].sort(
					(a, b) => b.bean_count - a.bean_count
				);

				if (notes.length > TASTING_NOTE_THRESHOLD) {
					// Add top notes directly to the tertiary node.
					for (let i = 0; i < TASTING_NOTE_THRESHOLD; i++) {
						const note = notes[i];
						if (note.note && note.bean_count > 0) {
							findOrCreateLeaf(note.note, tertiaryNode, note.bean_count);
						}
					}

					// Handle remaining notes
					const remainingNotes = notes.slice(TASTING_NOTE_THRESHOLD);
					if (remainingNotes.length === 1) {
						// If only one note remains, add it directly without creating an "Other" node
						const note = remainingNotes[0];
						if (note.note && note.bean_count > 0) {
							findOrCreateLeaf(note.note, tertiaryNode, note.bean_count);
						}
					} else if (remainingNotes.length > 1) {
						// Group multiple remaining notes under an "Other" node
						const otherNode = findOrCreateNodeWithFlag('Other', tertiaryNode, true);
						for (const note of remainingNotes) {
							if (note.note && note.bean_count > 0) {
								findOrCreateLeaf(note.note, otherNode, note.bean_count);
							}
						}
					}
				} else {
					// If there are fewer notes than the threshold, add them all directly.
					for (const note of notes) {
						if (note.note && note.bean_count > 0) {
							findOrCreateLeaf(note.note, tertiaryNode, note.bean_count);
						}
					}
				}
			}
		}
	}

	// D3's hierarchy().sum() will calculate the parent values automatically.
	// We no longer need to manually sum them up.
	return root;
}
