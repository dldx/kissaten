import type { PageLoad } from './$types';
import type { VarietalCategory } from '$lib/api';
import { api } from '$lib/api';

export const load: PageLoad = async ({ fetch }) => {
	try {
		const varietalsResponse = await api.getVarietals(fetch);

		if (!varietalsResponse.success || !varietalsResponse.data) {
			throw new Error('Failed to load varietals');
		}

		return {
			varietals: varietalsResponse.data as Record<string, VarietalCategory>,
			metadata: varietalsResponse.metadata || {}
		};
	} catch (error) {
		console.error('Error loading varietals:', error);
		return {
			varietals: {} as Record<string, VarietalCategory>,
			metadata: { error: 'Failed to load varietals' }
		};
	}
};
