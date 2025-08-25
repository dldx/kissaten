const API_BASE_URL = 'http://localhost:8000';

export interface CoffeeBean {
	id: number;
	name: string;
	roaster: string;
	url: string;
	image_url?: string | null;
	country: string;
	country_full_name?: string | null;
	region: string;
	producer: string;
	farm: string;
	elevation: number;
	is_single_origin: boolean;
	process: string;
	variety: string;
	harvest_date: string | null;
	price_paid_for_green_coffee: number | null;
	currency_of_price_paid_for_green_coffee: string | null;
	roast_level: string | null;
	weight: number | null;
	price: number | null;
	currency: string;
	tasting_notes: string[];
	description: string;
	in_stock: boolean | null;
	scraped_at: string;
	scraper_version: string;
	filename: string;
}

export interface Roaster {
	id: number;
	name: string;
	website: string;
	location: string;
	email: string;
	active: boolean;
	last_scraped: string | null;
	total_beans_scraped: number;
	current_beans_count: number;
}

export interface Country {
	country_code: string;
	country_name: string;
	bean_count: number;
	roaster_count: number;
}

export interface CountryCode {
	name: string;
	alpha_2: string;
	alpha_3: string;
	country_code: string;
	region: string;
	sub_region: string;
}

export interface PaginationInfo {
	page: number;
	per_page: number;
	total_items: number;
	total_pages: number;
	has_next: boolean;
	has_previous: boolean;
}

export interface APIResponse<T> {
	success: boolean;
	data: T | null;
	message?: string;
	pagination?: PaginationInfo;
	metadata?: Record<string, any>;
}

export interface SearchParams {
	query?: string;
	roaster?: string;
	country?: string;
	roast_level?: string;
	process?: string;
	variety?: string;
	min_price?: number;
	max_price?: number;
	min_weight?: number;
	max_weight?: number;
	in_stock_only?: boolean;
	page?: number;
	per_page?: number;
	sort_by?: string;
	sort_order?: string;
}

export class KissatenAPI {
	private baseUrl: string;

	constructor(baseUrl: string = API_BASE_URL) {
		this.baseUrl = baseUrl;
	}

	async search(params: SearchParams = {}): Promise<APIResponse<CoffeeBean[]>> {
		const searchParams = new URLSearchParams();

		Object.entries(params).forEach(([key, value]) => {
			if (value !== undefined && value !== null && value !== '') {
				searchParams.append(key, value.toString());
			}
		});

		const response = await fetch(`${this.baseUrl}/api/v1/search?${searchParams}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getRoasters(): Promise<APIResponse<Roaster[]>> {
		const response = await fetch(`${this.baseUrl}/api/v1/roasters`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getRoasterBeans(roasterName: string): Promise<APIResponse<CoffeeBean[]>> {
		const response = await fetch(`${this.baseUrl}/api/v1/roasters/${encodeURIComponent(roasterName)}/beans`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getCountries(): Promise<APIResponse<Country[]>> {
		const response = await fetch(`${this.baseUrl}/api/v1/countries`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getCountryCodes(): Promise<APIResponse<CountryCode[]>> {
		const response = await fetch(`${this.baseUrl}/api/v1/country-codes`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getStats(): Promise<APIResponse<any>> {
		const response = await fetch(`${this.baseUrl}/api/v1/stats`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getCoffeeBean(id: number): Promise<APIResponse<CoffeeBean>> {
		const response = await fetch(`${this.baseUrl}/api/v1/beans/${id}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getBeanRecommendations(id: number, limit: number = 6): Promise<APIResponse<CoffeeBean[]>> {
		const response = await fetch(`${this.baseUrl}/api/v1/beans/${id}/recommendations?limit=${limit}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getBeanByFilename(roasterName: string, beanFilename: string): Promise<APIResponse<CoffeeBean>> {
		const response = await fetch(`${this.baseUrl}/api/v1/roasters/${encodeURIComponent(roasterName)}/beans/${encodeURIComponent(beanFilename)}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getBeanRecommendationsByFilename(roasterName: string, beanFilename: string, limit: number = 6): Promise<APIResponse<CoffeeBean[]>> {
		const response = await fetch(`${this.baseUrl}/api/v1/roasters/${encodeURIComponent(roasterName)}/beans/${encodeURIComponent(beanFilename)}/recommendations?limit=${limit}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

}

// Export a default instance
export const api = new KissatenAPI();
