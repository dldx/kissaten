import { api } from '$lib/api.js';

export interface CarouselItem {
	type: 'bean' | 'roaster' | 'process' | 'varietal';
	data: any;
	key: string;
}

export interface HomePageData {
	carouselItems: CarouselItem[];
	coffeeBeans: any[];
	roasters: any[];
	processes: any[];
	varietals: any[];
}

export async function load({ fetch, parent }) {
    const data = await parent();
	// Return a promise that fetches all data in parallel
    const dataPromise = fetchHomePageData(fetch, data);

	return {
		dataPromise
	};
}

async function fetchHomePageData(fetch: typeof globalThis.fetch, parentData: any): Promise<HomePageData> {
	const data: HomePageData = {
		carouselItems: [],
		coffeeBeans: [],
		roasters: [],
		processes: [],
		varietals: []
	};

	try {
		// Fetch all data in parallel
		const [beansResponse, roastersResponse, processesResponse, varietalsResponse] = await Promise.all([
            api.search({ per_page: 12, sort_by: 'scraped_at', sort_order: 'desc', convert_to_currency: parentData?.currencyState?.selectedCurrency }, fetch),
			api.getRoasters(fetch),
			api.getProcesses(fetch),
			api.getVarietals(fetch)
		]);

		// Process coffee beans
		if (beansResponse.success && beansResponse.data) {
			data.coffeeBeans = beansResponse.data
				.sort(() => Math.random() - 0.5)
				.slice(0, 4);
		}

		// Process roasters
		if (roastersResponse.success && roastersResponse.data) {
			data.roasters = roastersResponse.data
				.filter(r => r.current_beans_count > 0)
				.sort(() => Math.random() - 0.5)
				.slice(0, 4);
		}

		// Process processes
		if (processesResponse.success && processesResponse.data) {
			const allProcesses = Object.values(processesResponse.data).flatMap(category => category.processes);
			data.processes = allProcesses.sort(() => Math.random() - 0.5).slice(0, 4);
		}

		// Process varietals
		if (varietalsResponse.success && varietalsResponse.data) {
			const allVarietals = Object.values(varietalsResponse.data).flatMap(category => category.varietals);
			data.varietals = allVarietals.sort(() => Math.random() - 0.5).slice(0, 4);
		}

		// Combine all items and shuffle the overall order
		const combinedItems: CarouselItem[] = [
			...data.coffeeBeans.map(bean => ({ type: 'bean' as const, data: bean, key: `bean-${bean.id}` })),
			...data.roasters.map(roaster => ({ type: 'roaster' as const, data: roaster, key: `roaster-${roaster.id}` })),
			...data.processes.map(process => ({ type: 'process' as const, data: process, key: `process-${process.slug}` })),
			...data.varietals.map(varietal => ({ type: 'varietal' as const, data: varietal, key: `varietal-${varietal.slug}` }))
		];

		data.carouselItems = combinedItems.sort(() => Math.random() - 0.5);

	} catch (error) {
		console.error('Failed to fetch carousel data:', error);
	}

	return data;
}
