import { getFlavourImageFromAvailable, getAvailableFlavourImages } from '$lib/utils';
import { flavourImageUrl, availableImages } from '$lib/stores/flavourImageStore';
import { get } from 'svelte/store';

let lastRequestId = 0;


export async function fetchAndSetFlavourImage(notes: string[]) {
	const requestId = ++lastRequestId;

	// Get current value from the store
	const availableImagesValue = get(availableImages);

	// If the store is empty, we might need to fetch the images first
	if (availableImagesValue.length === 0) {
		console.warn('Available images not yet loaded in store');
		return;
	}

	const imageUrl = await getFlavourImageFromAvailable(notes, availableImagesValue);
	if (requestId === lastRequestId) {
		flavourImageUrl.set(imageUrl);
	}
}

export function clearFlavourImage() {
	lastRequestId++; // Invalidate any pending requests
	flavourImageUrl.set(null);
}

