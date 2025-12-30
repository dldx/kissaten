import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ fetch }) => {
	try {
		const processesResponse = await api.getProcesses(fetch);

		if (!processesResponse.success || !processesResponse.data) {
			throw error(500, 'Failed to load processing methods');
		}

		return {
			processes: processesResponse.data,
			metadata: processesResponse.metadata
		};
	} catch (err) {
		console.error('Error loading processes:', err);
		throw error(500, 'Failed to load processing methods');
	}
};
