import { getFlavourImageFromAvailable, getAvailableFlavourImages } from '$lib/utils';
import { flavourImageUrl, availableImages } from '$lib/stores/flavourImageStore';
import { get } from 'svelte/store';

let lastRequestId = 0;
let clearTimeout: number | null = null;


export async function fetchAndSetFlavourImage(notes: string[]) {
	const requestId = ++lastRequestId;

	// Cancel any pending clear operation
	if (clearTimeout) {
		window.clearTimeout(clearTimeout);
		clearTimeout = null;
	}

	// Get current value from the store
	const availableImagesValue = get(availableImages);

	// If the store is empty, we might need to fetch the images first
	if (availableImagesValue.length === 0) {
		console.warn('Available images not yet loaded in store');
		return;
	}

	const imageUrl = await getFlavourImageFromAvailable(notes, availableImagesValue);
	if (requestId === lastRequestId) {
		// If we have a new image URL, set it immediately
		if (imageUrl) {
			flavourImageUrl.set(imageUrl);
		} else {
			// If clearing the image, wait a bit first
			clearTimeout = setTimeout(() => {
				if (requestId === lastRequestId) {
					flavourImageUrl.set(null);
				}
			}, 500);
		}
	}
}

export function clearFlavourImage() {
	lastRequestId++; // Invalidate any pending requests

	// Cancel any pending clear operation
	if (clearTimeout) {
		window.clearTimeout(clearTimeout);
		clearTimeout = null;
	}

	// Wait a bit before clearing
	clearTimeout = setTimeout(() => {
		flavourImageUrl.set(null);
	}, 500);
}

