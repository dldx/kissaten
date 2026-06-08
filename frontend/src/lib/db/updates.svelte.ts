export const dbUpdateTrigger = $state({
    tastingHistory: 0,
    customBeans: 0,
    savedBeans: 0,
    brewRecipes: 0
});

/**
 * Increments the specified trigger to notify subscribers (runes)
 * that the database has changed.
 */
export function notifyUpdate(type: 'tastingHistory' | 'customBeans' | 'savedBeans' | 'brewRecipes') {
    dbUpdateTrigger[type]++;
}
