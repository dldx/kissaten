import { getFlavourImage } from '$lib/remote/flavour.remote';
import { flavourImageUrl } from '$lib/stores/flavourImageStore';

let lastRequestId = 0;

export async function fetchAndSetFlavourImage(notes: string[]) {
	const requestId = ++lastRequestId;
	const imageUrl = await getFlavourImage(notes);
	if (requestId === lastRequestId) {
		flavourImageUrl.set(imageUrl);
	}
}

export function clearFlavourImage() {
	lastRequestId++; // Invalidate any pending requests
	flavourImageUrl.set(null);
}

