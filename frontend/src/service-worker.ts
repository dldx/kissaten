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

// Helper to store image in IndexedDB
async function storeImageInDB(blob: Blob, key: string): Promise<void> {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open('SharedImagesDB', 1);

		request.onerror = () => reject(request.error);

		request.onupgradeneeded = (event) => {
			const db = (event.target as IDBOpenDBRequest).result;
			if (!db.objectStoreNames.contains('images')) {
				db.createObjectStore('images');
			}
		};

		request.onsuccess = () => {
			const db = request.result;
			const transaction = db.transaction(['images'], 'readwrite');
			const store = transaction.objectStore('images');
			const putRequest = store.put(blob, key);

			putRequest.onsuccess = () => resolve();
			putRequest.onerror = () => reject(putRequest.error);

			transaction.oncomplete = () => db.close();
		};
	});
}

self.addEventListener('fetch', (event) => {
	const url = new URL(event.request.url);

	// Handle PWA share target POST requests
	if (event.request.method === 'POST' && url.pathname === '/search') {
		console.log('[SW] Intercepted POST to /search');
		event.respondWith((async () => {
			try {
				const formData = await event.request.formData();
				const imageFile = formData.get('image');
				console.log('[SW] Got image file:', imageFile?.name, imageFile?.size);

				if (imageFile instanceof File && imageFile.size > 0) {
					console.log('[SW] Starting image resize...');
					// Resize image client-side
					const resizedBlob = await resizeImage(imageFile, 1500, 1500);
					console.log('[SW] Resized image, new size:', resizedBlob.size);

					// Store resized image in IndexedDB
					const imageKey = `shared-image-${Date.now()}`;
					await storeImageInDB(resizedBlob, imageKey);
					console.log('[SW] Stored image in IndexedDB with key:', imageKey);

					// Redirect to search page with reference to stored image
					const redirectUrl = `${url.origin}/search?shared-image=${encodeURIComponent(imageKey)}`;
					console.log('[SW] Redirecting to:', redirectUrl);
					return Response.redirect(redirectUrl, 303);
				}
			} catch (error) {
				console.error('[SW] Error processing shared image:', error);
			}

			// Fallback: let the request through to the server
			console.log('[SW] Falling back to server handling');
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
