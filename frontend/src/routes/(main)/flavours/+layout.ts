import { availableImages } from '$lib/stores/flavourImageStore';
import { getAvailableFlavourImages } from '$lib/utils';

export const load = async ({ fetch }: { fetch: typeof globalThis.fetch }) => {
    // Fetch available flavour images from the API
    const images = await getAvailableFlavourImages(fetch);

    // Update the store with the fetched images
    availableImages.set(images);

    return {
        availableImages: images
    };
};