import { writable } from 'svelte/store';

export const flavourImageDimensions = writable({ width: 0, height: 0 });
export const flavourImageUrl = writable<string | null>(null);
export const flavourImageAttribution = writable<{ image_author?: string; image_license?: string; image_license_url?: string } | null>(null);
export const availableImages = writable<Array<{ note: string; filename: string; url: string; image_author?: string; image_license?: string; image_license_url?: string }>>([]);
