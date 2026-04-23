import { generateTastingImage, type TastingImageOptions } from './imageGenerator';
import { toast } from 'svelte-sonner';

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
