import { generateTastingImage, type TastingImageOptions, generateTastingText } from './imageGenerator';
import { toast } from 'svelte-sonner';
import type { TastingSession } from '$lib/db/localdb';
import { deleteTasting as dbDeleteTasting } from '$lib/db/localdb';
import { runGlobalSync } from '$lib/sync/syncManager.svelte';

/**
 * Shared logic for exporting a tasting session as an image (native share, clipboard, or download)
 */
export async function copyTastingAsImage(options: TastingImageOptions, sessionName: string) {
	try {
		const imageKey = JSON.stringify(options);
		// Native share (navigator.share with files) requires an active user gesture:
		// awaiting image generation before share() consumes the gesture, so mobile
		// browsers throw NotAllowedError. Only when the blob is already cached can we
		// call share() synchronously within the tap.
		const wasCached = cachedImageBlob !== null && cachedImageKey === imageKey;

		const blob = wasCached ? cachedImageBlob! : await getTastingImageBlob(options);
		const fileName = `${sessionName.trim() || 'coffee-tasting'}.png`;
		const canNativeShare =
			!!navigator.share &&
			!!navigator.canShare &&
			navigator.canShare({
				files: [new File([blob], fileName, { type: blob.type })],
			});
		// Native share needs the blob cached (no await before share()); otherwise we
		// fall back to clipboard/download and ask for one more tap.
		const sharedOnFirstTap = wasCached && canNativeShare;

		// 1. Native share — only possible on a cached blob (no await before share())
		if (sharedOnFirstTap) {
			try {
				await navigator.share({
					files: [new File([blob], fileName, { type: blob.type })],
					title: 'Coffee Tasting Session',
					text: 'My coffee tasting highlights',
				});
				return;
			} catch (e) {
				// User dismissed the share sheet — treat as handled
				if ((e as Error)?.name === 'AbortError') return;
				console.warn('Native share failed, falling back to clipboard', e);
			}
		}

		// 2. Try Clipboard API with feature detection for ClipboardItem
		if (
			typeof ClipboardItem !== 'undefined' &&
			navigator.clipboard &&
			navigator.clipboard.write
		) {
			const item = new ClipboardItem({ [blob.type]: blob });
			await navigator.clipboard.write([item]);
			toast.success(
				canNativeShare
					? 'Image ready! Tap Share again to open the share sheet.'
					: 'Tasting summary copied as image!',
			);
			return;
		}

		// 3. Fallback to download if clipboard/share not available
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = fileName;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
		toast.success(
			canNativeShare
				? 'Image ready! Tap Share again to open the share sheet.'
				: 'Tasting summary downloaded as image!',
		);
	} catch (e) {
		console.error('Failed to copy or share as image', e);
		toast.error('Failed to export image');
	}
}

// --- Image generation cache ---
// Generating the canvas image is async; caching the latest blob lets a tap call
// navigator.share() synchronously (within the user gesture) so it doesn't throw
// NotAllowedError on mobile. prewarmTastingImage() fills the cache ahead of time.
let cachedImageKey = '';
let cachedImageBlob: Blob | null = null;
let inflightImageKey = '';
let inflightImage: Promise<Blob> | null = null;

async function getTastingImageBlob(options: TastingImageOptions): Promise<Blob> {
	const key = JSON.stringify(options);
	if (cachedImageKey === key && cachedImageBlob) return cachedImageBlob;
	if (inflightImageKey === key && inflightImage) return inflightImage;

	inflightImageKey = key;
	const promise = generateTastingImage(options);
	inflightImage = promise;
	promise.then((blob) => {
		cachedImageBlob = blob;
		cachedImageKey = key;
		if (inflightImage === promise) {
			inflightImage = null;
			inflightImageKey = '';
		}
	});
	return promise;
}

/**
 * Warm the image cache ahead of a user tap so the native share sheet opens on
 * the first tap. Fire-and-forget; failures just fall back to a fresh generate.
 */
export function prewarmTastingImage(options: TastingImageOptions): void {
	void getTastingImageBlob(options).catch((e) => {
		console.warn('Prewarm tasting image failed', e);
	});
}

/**
 * Shared logic for generating a search URL based on tasting notes
 */
export function getTastingSearchUrl(notes: string[]) {
	const params = new URLSearchParams();
	if (notes && notes.length > 0) {
		// Join with '&' to create a boolean 'AND' search in the backend
		params.set('tasting_notes_query', notes.join('&'));
		params.set('sort_by', 'relevance');
		params.set('order', 'desc');
	}
	return `/search?${params.toString()}`;
}

/**
 * Common logic to copy tasting summary as text
 */
export async function copyTastingToClipboard(session: TastingSession) {
	try {
		const options: TastingImageOptions = {
			sessionName: session.name || "Coffee Tasting",
			dateOrNotes:
				session.brewingNotes ||
				new Intl.DateTimeFormat("en-GB", {
					dateStyle: "full",
				}).format(session.date),
			basics: session.basics || {},
			mouthfeel: session.mouthfeel || {},
			allSelectedNotesList: session.selectedNotes || [],
			beanData: session.beanData,
		};
		const text = generateTastingText(options);
		if (navigator.clipboard?.writeText) {
			await navigator.clipboard.writeText(text);
			toast.success("Summary copied to clipboard!");
		} else {
			// Fallback for browsers without clipboard support
			const textArea = document.createElement("textarea");
			textArea.value = text;
			document.body.appendChild(textArea);
			textArea.select();
			document.execCommand("copy");
			document.body.removeChild(textArea);
			toast.success("Summary copied to clipboard!");
		}
	} catch (e) {
		console.error("Failed to copy to clipboard", e);
		toast.error("Failed to copy to clipboard");
	}
}

/**
 * Common logic to delete a tasting session with confirmation
 */
export async function deleteTasting(id: number | undefined, options?: { onSuccess?: () => void, goBack?: boolean }) {
	if (id === undefined) return;
	if (confirm("Are you sure you want to delete this session?")) {
		await dbDeleteTasting(id);
		toast.success("Session deleted");
		if (options?.onSuccess) options.onSuccess();
		if (options?.goBack) window.history.back();

		// Background sync to propagate deletion
		void runGlobalSync({ silent: true });
	}
}

/**
 * Common logic to perform export as image with dark mode awareness
 */
export async function exportTastingAsImage(session: TastingSession, isDarkMode: boolean = false) {
	const options: TastingImageOptions = {
		sessionName: session.name || "Coffee Tasting",
		dateOrNotes:
			session.brewingNotes ||
			new Intl.DateTimeFormat("en-GB", {
				dateStyle: "full",
			}).format(session.date),
		basics: session.basics || {},
		mouthfeel: session.mouthfeel || {},
		allSelectedNotesList: session.selectedNotes || [],
		beanData: session.beanData,
		isDarkMode,
	};
	await copyTastingAsImage(options, session.name || "");
}

/**
 * Slugify a custom bean's free-text roaster name for use under the `/custom/`
 * history namespace (e.g. `/tasting/history/custom/manhattan_coffee_roasters`).
 * Mirrors `KissatenAPI.slugifyRoaster` so custom-roaster slugs look consistent
 * with real roaster slugs.
 */
export function slugifyCustomRoaster(roasterName: string | undefined | null): string {
	return (roasterName || "")
		.toLowerCase()
		.replace(/ /g, "_")
		.replace(/[^a-z0-9&_\-éūëöáíúñûē']/g, "_");
}

/**
 * Resolve the display name for a custom bean session's roaster, falling back to
 * the bean's stored roaster if the session-level name is missing.
 */
export function getCustomRoasterName(session: TastingSession): string {
	return session.roasterName || session.beanData?.roaster || "";
}

/**
 * Shared logic to build history URL for a tasting session
 */
export function getHistoryUrl(session: TastingSession) {
	if (session.beanUrlPath) {
		return `/tasting/history${session.beanUrlPath}/${session.id}`;
	}
	return `/tasting/history/unknown/unknown/${session.id}`;
}
