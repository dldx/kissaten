
import { query } from '$app/server';
import { searchItemsWithImages } from '$lib/utils';
import * as v from 'valibot';

export const getFlavourImage = query(
    v.array(v.string()),
    async (flavours: string[]) => {
        try {
            const results = await searchItemsWithImages(flavours);
            if (results.length > 0 && results[0].images.length > 0) {
                return results[0].images[0];
            }
        } catch (error) {
            console.error('Error fetching flavour image:', error);
        }
        return null;
    }
);
