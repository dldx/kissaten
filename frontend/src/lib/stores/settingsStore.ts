import { writable } from 'svelte/store';

// Experiments settings
export const flavourImagesEnabled = writable(true);

// Load settings from localStorage on initialization
if (typeof window !== 'undefined') {
	const stored = localStorage.getItem('kissaten-flavour-images');
	if (stored) {
		try {
			flavourImagesEnabled.set(JSON.parse(stored));
		} catch (e) {
			console.warn('Failed to parse experiments setting from localStorage');
		}
	}
}

// Save to localStorage when changed
flavourImagesEnabled.subscribe((value) => {
	if (typeof window !== 'undefined') {
		localStorage.setItem('kissaten-flavour-images', JSON.stringify(value));
	}
});
