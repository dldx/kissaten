import { writable } from 'svelte/store';

export const flavourImageDimensions = writable({ width: 0, height: 0 });
export const flavourImageUrl = writable<string | null>(null);
