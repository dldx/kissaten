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
		const blob = await generateTastingImage(options);

		// 1. Try to use Web Share API if supported (excellent for mobile)
		if (
			navigator.share &&
			navigator.canShare &&
			navigator.canShare({
				files: [
					new File([blob], 'tasting.png', { type: blob.type }),
				],
			})
		) {
			const file = new File(
				[blob],
				`${sessionName.trim() || 'coffee-tasting'}.png`,
				{ type: blob.type },
			);
			await navigator.share({
				files: [file],
				title: 'Coffee Tasting Session',
				text: 'My coffee tasting highlights',
			});
			return;
		}

		// 2. Try Clipboard API with feature detection for ClipboardItem
		if (
			typeof ClipboardItem !== 'undefined' &&
			navigator.clipboard &&
			navigator.clipboard.write
		) {
			const item = new ClipboardItem({ [blob.type]: blob });
			await navigator.clipboard.write([item]);
			toast.success('Tasting summary copied as image!');
		} else {
			// 3. Fallback to download if clipboard/share not available
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${sessionName.trim() || 'coffee-tasting'}.png`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
			toast.success('Tasting summary downloaded as image!');
		}
	} catch (e) {
		console.error('Failed to copy or share as image', e);
		toast.error('Failed to export image');
	}
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
			sessionName: session.name || "Coffee Tasting Session",
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
		sessionName: session.name || "Coffee Tasting Session",
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
 * Shared logic to build history URL for a tasting session
 */
export function getHistoryUrl(session: TastingSession) {
	if (session.beanUrlPath) {
		return `/tasting/history${session.beanUrlPath}/${session.id}`;
	}
	return `/tasting/history/unknown/unknown/${session.id}`;
}
