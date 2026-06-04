export const dbUpdateTrigger = $state({
    tastingHistory: 0,
    customBeans: 0
});

/**
 * Increments the specified trigger to notify subscribers (runes)
 * that the database has changed.
 */
export function notifyUpdate(type: 'tastingHistory' | 'customBeans') {
    dbUpdateTrigger[type]++;
}
