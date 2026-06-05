import type { TastingSession, LocalSavedBean, LocalCustomBean, RecentlyViewedBean } from "../db/localdb";
import { type CoffeeBean } from "../api";
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
 * Weighted search for saved beans.
 */
export function searchSavedBeans(
    beans: LocalSavedBean[],
    query: string
): LocalSavedBean[] {
    return searchGenericBeans(beans, query) as LocalSavedBean[];
}

/**
 * Weighted search for any local bean records containing beanData.
 */
export function searchGenericBeans(
    records: (LocalSavedBean | LocalCustomBean | RecentlyViewedBean)[],
    query: string
): (LocalSavedBean | LocalCustomBean | RecentlyViewedBean)[] {
    if (!query.trim()) return records;

    const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    if (terms.length === 0) return records;

    const scored = records.map((item) => {
        let score = 0;
        if (item.beanData) {
            score += calculateBeanRelevance(item.beanData, terms);
        }

        // Add user notes to the search if available (primarily for saved beans)
        if ('notes' in item && item.notes) {
            const normalizedNotes = item.notes.toLowerCase();
            for (const term of terms) {
                if (normalizedNotes.includes(term)) {
                    score += WEIGHTS.brewingNotes;
                }
            }
        }

        return { item, score };
    });

    return scored
        .filter((item) => item.score > 0)
        .sort((a, b) => b.score - a.score)
        .map((item) => item.item);
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

	// 1. Session Basics
    totalScore += scoreField('sessionName', session.name, WEIGHTS.sessionName, terms);
    totalScore += scoreField('brewingNotes', session.brewingNotes, WEIGHTS.brewingNotes, terms);
    totalScore += scoreField('beanName', session.beanName, WEIGHTS.beanName, terms);
    totalScore += scoreField('roasterName', session.roasterName, WEIGHTS.roasterName, terms);

	// 2. Selected Flavour Notes
	if (session.selectedNotes) {
		for (const note of session.selectedNotes) {
            totalScore += scoreField('selectedNote', note, WEIGHTS.selectedNotes, terms);
		}
	}

	// 3. Detailed Bean Data
	if (session.beanData) {
        totalScore += calculateBeanRelevance(session.beanData, terms);
    }

    return totalScore;
}

/**
 * Shared bean relevance calculation.
 */
export function calculateBeanRelevance(bean: CoffeeBean, terms: string[]): number {
    let totalScore = 0;

    totalScore += scoreField('beanDataName', bean.name, WEIGHTS.beanName, terms);
    totalScore += scoreField('beanDataRoaster', bean.roaster, WEIGHTS.roasterName, terms);
    totalScore += scoreField('beanDescription', bean.description, WEIGHTS.description, terms);

    // Check for top-level process/variety if they exist
    totalScore += scoreField('beanProcess', (bean as any).process, WEIGHTS.process, terms);
    totalScore += scoreField('beanVariety', (bean as any).variety, WEIGHTS.variety, terms);

    // Map 'Both' to 'Filter & Espresso' for better search discoverability
    let displayProfile = bean.roast_profile;
    if (displayProfile?.toLowerCase() === 'both') {
        displayProfile = 'Filter & Espresso';
    }

    totalScore += scoreField('roastProfile', displayProfile, WEIGHTS.roast, terms);
    totalScore += scoreField('roastLevel', bean.roast_level, WEIGHTS.roast, terms);

    // Special Coffee Logic: Omni/Filter/Espresso cross-matching
    const profile = (displayProfile || '').toLowerCase();
    const hasOmni = profile.includes('omni');
    const hasBoth = profile.includes('filter') && profile.includes('espresso');

    const isFilterSearch = terms.some(t => t.includes('filter'));
    const isEspressoSearch = terms.some(t => t.includes('espresso'));
    const isOmniSearch = terms.some(t => t.includes('omni'));

    if ((isFilterSearch || isEspressoSearch) && (hasOmni || hasBoth)) {
        totalScore += (WEIGHTS.roast * 0.8); // High bonus: searching for a method matches Omni/Both
    } else if (isOmniSearch && hasBoth) {
        totalScore += (WEIGHTS.roast * 0.8); // High bonus: searching for Omni matches multi-use roasts
    }

    if (bean.origins) {
        for (const origin of bean.origins) {
            totalScore += scoreField('originCountry', origin.country, WEIGHTS.origin, terms);

            // Priority 1: Use origin.country_full_name if it exists in the schema
            // Priority 2: Fall back to getCountryDisplayName()
            const fullName = (origin as any).country_full_name || getCountryDisplayName(origin.country);

            if (fullName && fullName !== origin.country) {
                totalScore += scoreField('originCountryFull', fullName, WEIGHTS.origin, terms);
            }
            totalScore += scoreField('originRegion', origin.region, WEIGHTS.origin, terms);
            totalScore += scoreField('originFarm', origin.farm, WEIGHTS.origin, terms);

            // Added process and variety fields from origin data
            totalScore += scoreField('process', origin.process, WEIGHTS.process, terms);
            totalScore += scoreField('variety', origin.variety, WEIGHTS.variety, terms);
            if (origin.variety_canonical && Array.isArray(origin.variety_canonical)) {
                for (const v of origin.variety_canonical) {
                    totalScore += scoreField('varietyCanonical', v, WEIGHTS.variety, terms);
                }
            }
        }
    }

    if (bean.tasting_notes) {
        for (const note of bean.tasting_notes) {
            // Use .note from TastingNote interface, fallback to .name or the string itself
            const noteText = typeof note === 'string' ? note : (note as any).note || (note as any).name;
            totalScore += scoreField('officialNote', noteText, WEIGHTS.description, terms);
		}
	}

	return totalScore;
}

// Helper to score a field
function scoreField(fieldName: string, text: string | undefined | null, weight: number, terms: string[]) {
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
        }
    }
    return fieldScore;
}

