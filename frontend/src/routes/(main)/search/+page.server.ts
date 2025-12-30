import { fail } from '@sveltejs/kit';
import { Buffer } from 'node:buffer';
import type { Actions } from './$types';

export const actions = {
    default: async ({ request }) => {
        const formData = await request.formData();
        const image = formData.get('image');

        if (image instanceof File && image.size > 0 && image.name) {
            // Convert to base64 to pass to client
            const buffer = await image.arrayBuffer();
            const base64 = Buffer.from(buffer).toString('base64');
            const dataUrl = `data:${image.type};base64,${base64}`;

            return {
                sharedImage: dataUrl,
                sharedImageName: image.name,
                sharedImageType: image.type
            };
        }

        return fail(400, { success: false, error: 'No valid image provided' });
    }
} satisfies Actions;
