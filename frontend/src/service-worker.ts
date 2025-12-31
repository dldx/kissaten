/// <reference types="@sveltejs/kit" />
import { build, files, version } from '$service-worker';

// Create a unique cache name for this deployment
const CACHE = `cache-${version}`;

const ASSETS = [
	...build, // the app itself
	...files  // everything in `static`
];

self.addEventListener('install', (event) => {
	// Create a new cache and add all files to it
	async function addFilesToCache() {
		const cache = await caches.open(CACHE);
		await cache.addAll(ASSETS);
	}

	event.waitUntil(addFilesToCache());
});

self.addEventListener('activate', (event) => {
	// Remove previous cached data from disk
	async function deleteOldCaches() {
		for (const key of await caches.keys()) {
			if (key !== CACHE) await caches.delete(key);
		}
	}

	event.waitUntil(deleteOldCaches());
});

// Helper function to resize image using OffscreenCanvas
async function resizeImage(blob: Blob, maxWidth: number, maxHeight: number): Promise<Blob> {
	const bitmap = await createImageBitmap(blob);

	let { width, height } = bitmap;
	const ratio = Math.min(maxWidth / width, maxHeight / height);

	if (ratio < 1) {
		width *= ratio;
		height *= ratio;
	}

	const canvas = new OffscreenCanvas(width, height);
	const ctx = canvas.getContext('2d');
	if (!ctx) throw new Error('Could not get canvas context');

	ctx.drawImage(bitmap, 0, 0, width, height);

	return await canvas.convertToBlob({
		type: 'image/jpeg',
		quality: 0.9
	});
}

self.addEventListener('fetch', (event) => {
	const url = new URL(event.request.url);

	// Handle PWA share target POST requests
	if (event.request.method === 'POST' && url.pathname === '/search') {
		event.respondWith((async () => {
			try {
				const formData = await event.request.formData();
				const imageFile = formData.get('image');

				if (imageFile instanceof File && imageFile.size > 0) {
					// Resize image client-side
					const resizedBlob = await resizeImage(imageFile, 1500, 1500);
					const resizedFile = new File([resizedBlob], imageFile.name, {
						type: 'image/jpeg',
						lastModified: Date.now()
					});

					// Store resized image in cache for client to retrieve
					const cache = await caches.open('shared-images');
					const imageUrl = `/shared-image-${Date.now()}`;
					await cache.put(imageUrl, new Response(resizedBlob, {
						headers: { 'Content-Type': 'image/jpeg' }
					}));

					// Redirect to search page with reference to cached image
					return Response.redirect(`/search?shared-image=${encodeURIComponent(imageUrl)}`, 303);
				}
			} catch (error) {
				console.error('[SW] Error processing shared image:', error);
			}

			// Fallback: let the request through to the server
			return fetch(event.request);
		})());
		return;
	}

	// ignore other POST requests
	if (event.request.method !== 'GET') return;

	// Ignore chrome-extension and other non-http(s) schemes
	if (!url.protocol.startsWith('http')) {
		return;
	}

	async function respond() {
		const cache = await caches.open(CACHE);

		// `build`/`files` can always be served from the cache
		if (ASSETS.includes(url.pathname)) {
			const response = await cache.match(url.pathname);
			if (response) {
				return response;
			}
		}

		// for everything else, try the network first, but fall back to the cache if we're offline
		try {
			const response = await fetch(event.request);

			// if we're online, stash a copy of the page in the cache
			// Only cache http(s) requests with successful responses
			if (response.status === 200 && url.protocol.startsWith('http')) {
				try {
					await cache.put(event.request, response.clone());
				} catch (error) {
					// Silently fail cache.put errors (e.g., for chrome-extension URLs)
					console.warn('[SW] Failed to cache:', url.href, error);
				}
			}

			return response;
		} catch (error) {
			const response = await cache.match(event.request);
			if (response) {
				return response;
			}
			// Don't throw for non-critical resources
			console.warn('[SW] Fetch failed and no cache:', url.href, error);
			return new Response('Network error', {
				status: 408,
				headers: { 'Content-Type': 'text/plain' }
			});
		}
	}

	event.respondWith(respond());
});
