/**
 * Shared open/closed state for the feedback dialog so the floating button
 * (mounted in the root layout) and inline triggers (mounted on specific
 * pages) can open the same dialog instance.
 */
export const feedbackDialog = $state({ open: false });

export function openFeedbackDialog() {
  feedbackDialog.open = true;
}

export function closeFeedbackDialog() {
  feedbackDialog.open = false;
}
