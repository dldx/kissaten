import { browser } from "$app/environment";

const DEBUG_FLAG = "kissaten:debug";
const SCROLL_TAG = "scroll";

/**
 * Runtime-gated debug logging for the infinite-scroll pipeline.
 *
 * Disabled by default. To toggle on (in development or production):
 *   localStorage.setItem("kissaten:debug", "scroll")
 *
 * To toggle off:
 *   localStorage.removeItem("kissaten:debug")
 */
function isScrollDebugEnabled(): boolean {
	if (!browser) return false;
	try {
		const raw = localStorage.getItem(DEBUG_FLAG);
		return raw?.split(",").map((s) => s.trim()).includes(SCROLL_TAG) ?? false;
	} catch {
		return false;
	}
}

export function debugLog(tag: string, ...args: unknown[]): void {
	if (!isScrollDebugEnabled()) return;
	console.debug(`[${tag}]`, ...args);
}

export function debugWarn(tag: string, ...args: unknown[]): void {
	if (!isScrollDebugEnabled()) return;
	console.warn(`[${tag}]`, ...args);
}
