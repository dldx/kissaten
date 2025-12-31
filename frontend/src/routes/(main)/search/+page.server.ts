import { fail } from '@sveltejs/kit';
import { Buffer } from 'node:buffer';
import sharp from 'sharp';
import type { Actions } from './$types';

export const actions = {
    default: async ({ request }) => {
        const formData = await request.formData();
        const image = formData.get('image');

        if (image instanceof File && image.size > 0 && image.name) {
            try {
                // Resize image before converting to base64 to prevent 413 errors
                const buffer = await image.arrayBuffer();
                const resizedBuffer = await sharp(Buffer.from(buffer))
                    .resize(1500, 1500, { 
                        fit: 'inside',
                        withoutEnlargement: true
                    })
                    .jpeg({ quality: 90 })
                    .toBuffer();

                const base64 = resizedBuffer.toString('base64');
                const dataUrl = `data:image/jpeg;base64,${base64}`;

                return {
                    sharedImage: dataUrl,
                    sharedImageName: image.name,
                    sharedImageType: 'image/jpeg'
                };
            } catch (error) {
                console.error('Image processing failed:', error);
                return fail(500, { success: false, error: 'Image processing failed' });
            }
        }

        return fail(400, { success: false, error: 'No valid image provided' });
    }
} satisfies Actions;
