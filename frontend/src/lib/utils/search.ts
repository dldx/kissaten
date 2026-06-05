	import type { TastingSession } from "../db/localdb";
import { getCountryDisplayName } from "../utils";

/**
 * Weighted search for tasting sessions.
 * Matches keywords across session name, bean details, and user notes.
 * Returns sessions sorted by relevance score.
 */
export function searchTastingHistory(
	history: TastingSession[],
	query: string
): TastingSession[] {
	if (!query.trim()) return history;

	const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
	if (terms.length === 0) return history;

	const scored = history.map((session) => {
		const score = calculateRelevance(session, terms);
		return { session, score };
	});

	// Filter out zero-score items and sort by score descending
	return scored
		.filter((item) => item.score > 0)
		.sort((a, b) => b.score - a.score)
		.map((item) => item.session);
}

/**
 * Field weights for search relevance.
 */
const WEIGHTS = {
	sessionName: 10,
	beanName: 8,
	roasterName: 6,
	brewingNotes: 5,
	selectedNotes: 4,
	process: 4,
	origin: 3,
	variety: 3,
	roast: 2,
	description: 1
};

function calculateRelevance(session: TastingSession, terms: string[]): number {
	let totalScore = 0;
	const matchedFields: string[] = [];

	// Helper to score a field
	const scoreField = (fieldName: string, text: string | undefined | null, weight: number) => {
		if (!text) return 0;
		// Normalize text: replace symbols common in roast/origin names with spaces for better matching
		const normalizedText = text.toLowerCase().replace(/[&+/]/g, ' ');
		let fieldScore = 0;

		for (const term of terms) {
			const cleanTerm = term.replace(/[&+/]/g, '').toLowerCase();
			if (!cleanTerm) continue;

			// Exact match for term
			if (normalizedText.includes(cleanTerm)) {
				fieldScore += weight;
				// Bonus for word boundaries/exact start
				if (normalizedText.startsWith(cleanTerm)) fieldScore += weight * 0.5;
				matchedFields.push(`${fieldName}: "${text}"`);
			}
		}
		return fieldScore;
	};

	// 1. Session Basics
	totalScore += scoreField('sessionName', session.name, WEIGHTS.sessionName);
	totalScore += scoreField('brewingNotes', session.brewingNotes, WEIGHTS.brewingNotes);
	totalScore += scoreField('beanName', session.beanName, WEIGHTS.beanName);
	totalScore += scoreField('roasterName', session.roasterName, WEIGHTS.roasterName);

	// 2. Selected Flavour Notes
	if (session.selectedNotes) {
		for (const note of session.selectedNotes) {
			totalScore += scoreField('selectedNote', note, WEIGHTS.selectedNotes);
		}
	}

	// 3. Detailed Bean Data
	if (session.beanData) {
		const bean = session.beanData;
		totalScore += scoreField('beanDataName', bean.name, WEIGHTS.beanName);
		totalScore += scoreField('beanDataRoaster', bean.roaster, WEIGHTS.roasterName);
		totalScore += scoreField('beanDescription', bean.description, WEIGHTS.description);

		// Check for top-level process/variety if they exist
		totalScore += scoreField('beanProcess', (bean as any).process, WEIGHTS.process);
		totalScore += scoreField('beanVariety', (bean as any).variety, WEIGHTS.variety);

		// Map 'Both' to 'Filter & Espresso' for better search discoverability
		let displayProfile = bean.roast_profile;
		if (displayProfile?.toLowerCase() === 'both') {
			displayProfile = 'Filter & Espresso';
		}

		totalScore += scoreField('roastProfile', displayProfile, WEIGHTS.roast);
		totalScore += scoreField('roastLevel', bean.roast_level, WEIGHTS.roast);

		// Special Coffee Logic: Omni/Filter/Espresso cross-matching
		const profile = (displayProfile || '').toLowerCase();
		const hasOmni = profile.includes('omni');
		const hasBoth = profile.includes('filter') && profile.includes('espresso');

		const isFilterSearch = terms.some(t => t.includes('filter'));
		const isEspressoSearch = terms.some(t => t.includes('espresso'));
		const isOmniSearch = terms.some(t => t.includes('omni'));

		if ((isFilterSearch || isEspressoSearch) && (hasOmni || hasBoth)) {
			totalScore += (WEIGHTS.roast * 0.8); // High bonus: searching for a method matches Omni/Both
			matchedFields.push(`roastSpecial: "${hasOmni ? 'Omni' : 'Both'} matched ${isFilterSearch ? 'filter' : 'espresso'} search"`);
		} else if (isOmniSearch && hasBoth) {
			totalScore += (WEIGHTS.roast * 0.8); // High bonus: searching for Omni matches multi-use roasts
			matchedFields.push(`roastSpecial: "Both-use matched omni search"`);
		}

		if (bean.origins) {
			for (const origin of bean.origins) {
				totalScore += scoreField('originCountry', origin.country, WEIGHTS.origin);

				// Priority 1: Use origin.country_full_name if it exists in the schema
				// Priority 2: Fall back to getCountryDisplayName()
				const fullName = (origin as any).country_full_name || getCountryDisplayName(origin.country);

				if (fullName && fullName !== origin.country) {
					totalScore += scoreField('originCountryFull', fullName, WEIGHTS.origin);
				}
				totalScore += scoreField('originRegion', origin.region, WEIGHTS.origin);
				totalScore += scoreField('originFarm', origin.farm, WEIGHTS.origin);

				// Added process and variety fields from origin data
				totalScore += scoreField('process', origin.process, WEIGHTS.process);
				totalScore += scoreField('variety', origin.variety, WEIGHTS.variety);
				if (origin.variety_canonical && Array.isArray(origin.variety_canonical)) {
					for (const v of origin.variety_canonical) {
						totalScore += scoreField('varietyCanonical', v, WEIGHTS.variety);
					}
				}
			}
		}

		if (bean.tasting_notes) {
			for (const note of bean.tasting_notes) {
				// Use .note from TastingNote interface, fallback to .name or the string itself
				const noteText = typeof note === 'string' ? note : (note as any).note || (note as any).name;
				totalScore += scoreField('officialNote', noteText, WEIGHTS.description);
			}
		}
	}

	return totalScore;
}
