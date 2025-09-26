import { searchItemsWithImages } from '$lib/utils';


export const load = async ({ params, fetch }) => {
    const imageUrl = await searchItemsWithImages(params.flavour, 1, fetch).then(results => results[0]?.images[0]);
    return {
        flavour: params.flavour,
        imageUrl: imageUrl
    };
};