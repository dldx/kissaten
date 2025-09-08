const API_BASE_URL = '';

export interface Bean {
	country?: string | null;
	country_full_name?: string | null;
	region?: string | null;
	producer?: string | null;
	farm?: string | null;
	elevation: number;
	latitude?: number | null;
	longitude?: number | null;
	process?: string | null;
	variety?: string | null;
	harvest_date?: string | null;
}

export interface CoffeeBean {
	id: number;
	name: string;
	roaster: string;
	url: string;
	image_url?: string | null;
	origins: Bean[];
	country: string;
	country_full_name?: string | null;
	region: string;
	producer: string;
	farm: string;
	elevation: number;
	is_single_origin: boolean;
	is_decaf: boolean;
	price_paid_for_green_coffee: number | null;
	currency_of_price_paid_for_green_coffee: string | null;
	roast_level: string | null;
	roast_profile: string | null;
	weight: number | null;
	price: number | null;
	currency: string;
	cupping_score: number | null;
	tasting_notes: string[];
	description: string;
	in_stock: boolean | null;
	scraped_at: string;
	scraper_version: string;
	filename: string;
	clean_url_slug?: string;
	bean_url_path?: string;
	// Currency conversion fields
	original_price?: number;
	original_currency?: string;
	price_converted?: boolean;
}

export interface Roaster {
	id: number;
	name: string;
	slug: string;
	website: string;
	location: string;
	email: string;
	active: boolean;
	last_scraped: string | null;
	total_beans_scraped: number;
	current_beans_count: number;
	location_codes: string[];  // Array of hierarchical location codes (e.g., ["FR", "XE", "EU"])
}

export interface Country {
	country_code: string;
	country_name: string;
	bean_count?: number;
	roaster_count?: number;
}

export interface RoasterLocation {
	code: string;
	location: string;
	region: string;
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

export interface Process {
	name: string;
	slug: string;
	bean_count: number;
	roaster_count: number;
	country_count: number;
	category: string;
}

export interface ProcessCategory {
	name: string;
	processes: Process[];
	total_beans: number;
}

export interface ProcessDetails {
	name: string;
	slug: string;
	category: string;
	statistics: {
		total_beans: number;
		total_roasters: number;
		total_countries: number;
		avg_price: number;
		min_price: number;
		max_price: number;
	};
	top_countries: Array<{
		country_code: string;
		country_name: string;
		bean_count: number;
	}>;
	top_roasters: Array<{
		name: string;
		bean_count: number;
	}>;
	common_tasting_notes: Array<{
		note: string;
		frequency: number;
	}>;
}

export interface Varietal {
	name: string;
	slug: string;
	bean_count: number;
	roaster_count: number;
	country_count: number;
	countries: Country[];
	category: string;
}

export interface VarietalCategory {
	name: string;
	varietals: Varietal[];
	total_beans: number;
}

export interface VarietalDetails {
	name: string;
	slug: string;
	category: string;
	statistics: {
		total_beans: number;
		total_roasters: number;
		total_countries: number;
		avg_price: number;
		min_price: number;
		max_price: number;
	};
	top_countries: Array<{
		country_code: string;
		country_name: string;
		bean_count: number;
	}>;
	top_roasters: Array<{
		name: string;
		bean_count: number;
	}>;
	common_tasting_notes: Array<{
		note: string;
		frequency: number;
	}>;
	common_processing_methods?: Array<{
		process: string;
		frequency: number;
	}>;
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
	tasting_notes_query?: string;
	roaster?: string | string[];
	roaster_location?: string | string[];
	origin?: string | string[];
	region?: string; // Now supports wildcards and boolean operators
	producer?: string; // Now supports wildcards and boolean operators
	farm?: string; // Now supports wildcards and boolean operators
	roast_level?: string; // Now supports wildcards and boolean operators
	roast_profile?: string; // Now supports wildcards and boolean operators
	process?: string; // Now supports wildcards and boolean operators
	variety?: string; // Now supports wildcards and boolean operators
	min_price?: number;
	max_price?: number;
	min_weight?: number;
	max_weight?: number;
	min_elevation?: number;
	max_elevation?: number;
	in_stock_only?: boolean;
	is_decaf?: boolean;
	is_single_origin?: boolean;
	min_cupping_score?: number;
	max_cupping_score?: number;
	tasting_notes_only?: boolean;
	page?: number;
	per_page?: number;
	sort_by?: string;
	sort_order?: string;
	convert_to_currency?: string; // New currency conversion parameter
}

export interface AISearchQuery {
	query: string;
}

export interface AISearchParameters {
	search_text?: string | null;
	tasting_notes_search?: string | null;
	use_tasting_notes_only: boolean;
	roaster?: string[] | null;
	roaster_location?: string[] | null;
	variety?: string | null; // Now supports wildcards and boolean operators
	process?: string | null; // Now supports wildcards and boolean operators
	roast_level?: string | null;
	roast_profile?: string | null;
	origin?: string[] | null;
	region?: string | null; // Now supports wildcards and boolean operators
	producer?: string | null; // New field with wildcard support
	farm?: string | null; // New field with wildcard support
	min_price?: number | null;
	max_price?: number | null;
	min_weight?: number | null;
	max_weight?: number | null;
	min_elevation?: number | null;
	max_elevation?: number | null;
	in_stock_only: boolean;
	is_decaf?: boolean | null;
	is_single_origin?: boolean | null;
	sort_by: string;
	sort_order: string;
	confidence: number;
	reasoning?: string | null;
}

export interface AISearchResponse {
	success: boolean;
	search_params?: AISearchParameters | null;
	search_url?: string | null;
	error_message?: string | null;
	processing_time_ms?: number | null;
}

export interface Currency {
	code: string;
	rate_to_usd: number;
	name: string;
}

export interface CurrencyConversion {
	original_amount: number;
	from_currency: string;
	to_currency: string;
	converted_amount: number;
	rate_used: number | null;
}

export class KissatenAPI {
	private baseUrl: string;
	private defaultCurrency?: string;

	constructor(baseUrl: string = API_BASE_URL, defaultCurrency?: string) {
		this.baseUrl = baseUrl;
		this.defaultCurrency = defaultCurrency;
	}

	/**
	 * Helper method to add currency conversion parameter to search params if needed
	 */
	private addCurrencyParam(searchParams: URLSearchParams, convertToCurrency?: string): void {
		const currency = convertToCurrency || this.defaultCurrency;
		if (currency && !searchParams.has('convert_to_currency')) {
			searchParams.set('convert_to_currency', currency);
		}
	}

	/**
	 * Helper method to get the primary origin from a coffee bean
	 */
	getPrimaryOrigin(bean: CoffeeBean): Bean | null {
		return bean.origins && bean.origins.length > 0 ? bean.origins[0] : null;
	}

	/**
	 * Helper method to get formatted origin string for display
	 */
	getOriginDisplayString(bean: CoffeeBean): string {
		if (!bean.origins || bean.origins.length === 0) {
			return 'Unknown Origin';
		}

		if (bean.is_single_origin) {
			const origin = bean.origins[0];
			const parts = [];
			if (origin.country_full_name) parts.push(origin.country_full_name);
			if (origin.region) parts.push(origin.region);
			if (origin.farm) parts.push(origin.farm);
			return parts.join(', ') || 'Unknown Origin';
		} else {
			// For blends, show all countries
			const countries = bean.origins
				.map(origin => origin.country_full_name)
				.filter(country => country)
				.join(', ');
			return countries || 'Blend';
		}
	}

	/**
	 * Helper method to get all processes from a coffee bean's origins
	 */
	getBeanProcesses(bean: CoffeeBean): string[] {
		return bean.origins
			.map(origin => origin.process)
			.filter(process => process) as string[];
	}

	/**
	 * Helper method to get all varieties from origins
	 */
	getVarieties(bean: CoffeeBean): string[] {
		return bean.origins
			.map(origin => origin.variety)
			.filter(variety => variety) as string[];
	}

	/**
	 * Helper method to build a clean bean URL path from bean data
	 */
	getBeanUrlPath(bean: CoffeeBean): string {
		if (bean.bean_url_path) {
			return bean.bean_url_path;
		}
		if (bean.clean_url_slug && bean.roaster) {
			const roasterSlug = bean.roaster.toLowerCase().replace(/\s+/g, '_');
			return `/${roasterSlug}/${bean.clean_url_slug}`;
		}
		return '';
	}

	/**
	 * Helper method to extract roaster slug from roaster name
	 */
	getRoasterSlug(roasterName: string): string {
		return roasterName.toLowerCase().replace(/\s+/g, '_');
	}

	/**
	 * Parse a clean bean URL path into roaster slug and bean slug
	 * @param urlPath - Path like "/roaster_name/bean_slug"
	 * @returns Object with roasterSlug and beanSlug
	 */
	parseBeanUrl(urlPath: string): { roasterSlug: string; beanSlug: string } | null {
		const match = urlPath.match(/^\/([^/]+)\/(.+)$/);
		if (!match) {
			return null;
		}
		return {
			roasterSlug: match[1],
			beanSlug: match[2]
		};
	}

	async search(params: SearchParams = {}, fetchFn: typeof fetch = fetch): Promise<APIResponse<CoffeeBean[]>> {
		const searchParams = new URLSearchParams();

		Object.entries(params).forEach(([key, value]) => {
			if (value !== undefined && value !== null && value !== '') {
				if (Array.isArray(value)) {
					// For arrays, append each value separately
					value.forEach(v => {
						if (v !== undefined && v !== null && v !== '') {
							searchParams.append(key, v.toString());
						}
					});
				} else {
					searchParams.append(key, value.toString());
				}
			}
		});

		// Add currency conversion if not already specified
		this.addCurrencyParam(searchParams, params.convert_to_currency);

		const response = await fetchFn(`${this.baseUrl}/api/v1/search?${searchParams}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getRoasters(fetchFn: typeof fetch = fetch): Promise<APIResponse<Roaster[]>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/roasters`);
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

	async getCountries(fetchFn: typeof fetch = fetch): Promise<APIResponse<Country[]>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/countries`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getRoasterLocations(fetchFn: typeof fetch = fetch): Promise<APIResponse<RoasterLocation[]>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/roaster-locations`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getCountryCodes(fetchFn: typeof fetch = fetch): Promise<APIResponse<CountryCode[]>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/country-codes`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async searchBeanByRoasterAndName(roaster: string, name: string, fetchFn: typeof fetch = fetch): Promise<APIResponse<CoffeeBean>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/search/bean?roaster=${encodeURIComponent(roaster)}&name=${encodeURIComponent(name)}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getBeanBySlug(roasterSlug: string, beanSlug: string, fetchFn: typeof fetch = fetch, convertToCurrency?: string): Promise<APIResponse<CoffeeBean>> {
		const params = new URLSearchParams();
		const currency = convertToCurrency || this.defaultCurrency;
		if (currency) {
			params.append('convert_to_currency', currency);
		}

		const url = `${this.baseUrl}/api/v1/beans/${encodeURIComponent(roasterSlug)}/${encodeURIComponent(beanSlug)}${params.toString() ? '?' + params.toString() : ''}`;
		const response = await fetchFn(url);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getBeanRecommendationsBySlug(roasterSlug: string, beanSlug: string, limit: number = 6, fetchFn: typeof fetch = fetch, convertToCurrency?: string): Promise<APIResponse<CoffeeBean[]>> {
		const params = new URLSearchParams();
		params.append('limit', limit.toString());
		const currency = convertToCurrency || this.defaultCurrency;
		if (currency) {
			params.append('convert_to_currency', currency);
		}

		const response = await fetchFn(`${this.baseUrl}/api/v1/beans/${encodeURIComponent(roasterSlug)}/${encodeURIComponent(beanSlug)}/recommendations?${params.toString()}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getProcesses(fetchFn: typeof fetch = fetch): Promise<APIResponse<Record<string, ProcessCategory>>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/processes`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getProcessDetails(processSlug: string, convert_to_currency?: string, fetchFn: typeof fetch = fetch): Promise<APIResponse<ProcessDetails>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/processes/${encodeURIComponent(processSlug)}?convert_to_currency=${convert_to_currency}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getProcessBeans(
		processSlug: string,
		params: { page?: number; per_page?: number; sort_by?: string; sort_order?: string; convert_to_currency?: string } = {},
		fetchFn: typeof fetch = fetch
	): Promise<APIResponse<CoffeeBean[]>> {
		const searchParams = new URLSearchParams();
		Object.entries(params).forEach(([key, value]) => {
			if (value !== undefined && value !== null && value !== '') {
				searchParams.append(key, value.toString());
			}
		});

		// Add currency conversion if not already specified
		this.addCurrencyParam(searchParams, params.convert_to_currency);

		const url = `${this.baseUrl}/api/v1/processes/${encodeURIComponent(processSlug)}/beans${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
		const response = await fetchFn(url);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	/**
	 * Helper method to normalize process names for URL slugs
	 */
	normalizeProcessName(processName: string): string {
		return processName
			.toLowerCase()
			.replace(/[^a-zA-Z0-9\s]/g, '')
			.replace(/\s+/g, '-')
			.trim();
	}

	async getVarietals(fetchFn: typeof fetch = fetch): Promise<APIResponse<Record<string, VarietalCategory>>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/varietals`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getVarietalDetails(varietalSlug: string, convert_to_currency?: string, fetchFn: typeof fetch = fetch): Promise<APIResponse<VarietalDetails>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/varietals/${encodeURIComponent(varietalSlug)}?convert_to_currency=${convert_to_currency}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	async getVarietalBeans(
		varietalSlug: string,
		params: { page?: number; per_page?: number; sort_by?: string; sort_order?: string; convert_to_currency?: string } = {},
		fetchFn: typeof fetch = fetch
	): Promise<APIResponse<CoffeeBean[]>> {
		const searchParams = new URLSearchParams();
		Object.entries(params).forEach(([key, value]) => {
			if (value !== undefined && value !== null && value !== '') {
				searchParams.append(key, value.toString());
			}
		});

		// Add currency conversion if not already specified
		this.addCurrencyParam(searchParams, params.convert_to_currency);

		const url = `${this.baseUrl}/api/v1/varietals/${encodeURIComponent(varietalSlug)}/beans${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
		const response = await fetchFn(url);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	/**
	 * Helper method to normalize varietal names for URL slugs
	 */
	normalizeVarietalName(varietalName: string): string {
		return varietalName
			.toLowerCase()
			.replace(/[^a-zA-Z0-9\s]/g, '')
			.replace(/\s+/g, '-')
			.trim();
	}

	/**
	 * Perform AI-powered search query translation
	 */
	async aiSearch(query: string, fetchFn: typeof fetch = fetch): Promise<APIResponse<AISearchResponse>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/ai/search`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ query })
		});

		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	/**
	 * Perform AI search and get redirect URL for frontend navigation
	 * This returns the redirect URL that should be navigated to
	 */
	async aiSearchRedirect(query: string, fetchFn: typeof fetch = fetch): Promise<string> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/ai/search/redirect`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({ query })
		});

		if (!response.ok) {
			// Fallback to regular search if request fails
			return `/search?q=${encodeURIComponent(query)}`;
		}

		const result: APIResponse<{ redirect_url: string; ai_success: boolean }> = await response.json();

		if (result.success && result.data?.redirect_url) {
			return result.data.redirect_url;
		}

		// Fallback to regular search if AI search fails
		return `/search?q=${encodeURIComponent(query)}`;
	}

	/**
	 * Perform AI search and get parsed search parameters for direct form population
	 * This returns search parameters that can be applied directly to the search form
	 */
	async aiSearchParameters(query: string, fetchFn: typeof fetch = fetch): Promise<{ success: boolean; searchParams?: SearchParams; error?: string }> {
		try {
			const response = await fetchFn(`${this.baseUrl}/api/v1/ai/search`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ query })
			});

			if (!response.ok) {
				return {
					success: false,
					error: `HTTP error! status: ${response.status}`,
					searchParams: { query }
				};
			}

			const result: APIResponse<AISearchResponse> = await response.json();

			if (!result.success || !result.data?.search_params) {
				return {
					success: false,
					error: result.data?.error_message || 'AI search failed',
					searchParams: { query }
				};
			}

			const aiParams = result.data.search_params;

			// Convert AI search parameters to SearchParams format
			const searchParams: SearchParams = {
				query: aiParams.search_text || undefined,
				tasting_notes_query: aiParams.tasting_notes_search || undefined,
				roaster: aiParams.roaster || undefined,
				roaster_location: aiParams.roaster_location || undefined,
				origin: aiParams.origin || undefined,
				region: aiParams.region || undefined,
				roast_level: aiParams.roast_level || undefined,
				roast_profile: aiParams.roast_profile || undefined,
				process: aiParams.process || undefined,
				variety: aiParams.variety || undefined,
				min_price: aiParams.min_price || undefined,
				max_price: aiParams.max_price || undefined,
				min_weight: aiParams.min_weight || undefined,
				max_weight: aiParams.max_weight || undefined,
				min_elevation: aiParams.min_elevation || undefined,
				max_elevation: aiParams.max_elevation || undefined,
				in_stock_only: aiParams.in_stock_only || false,
				is_decaf: aiParams.is_decaf ?? undefined,
				is_single_origin: aiParams.is_single_origin ?? undefined,
				sort_by: aiParams.sort_by || 'name',
				sort_order: aiParams.sort_order || 'asc'
			};

			return {
				success: true,
				searchParams
			};

		} catch (error) {
			console.error('AI search parameters error:', error);
			return {
				success: false,
				error: error instanceof Error ? error.message : 'AI search failed',
				searchParams: { query }
			};
		}
	}

	/**
	 * Check AI search service health
	 */
	async aiSearchHealth(fetchFn: typeof fetch = fetch): Promise<APIResponse<{ status: string }>> {
		try {
			const response = await fetchFn(`${this.baseUrl}/api/v1/ai/health`);
			if (!response.ok) {
				return { success: false, data: null, message: `HTTP error! status: ${response.status}` };
			}
			return response.json();
		} catch (error) {
			return { success: false, data: null, message: 'AI service unavailable' };
		}
	}

	/**
	 * Get all available currencies with their exchange rates
	 */
	async getCurrencies(fetchFn: typeof fetch = fetch): Promise<APIResponse<Currency[]>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/currencies`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	/**
	 * Convert an amount from one currency to another
	 */
	async convertCurrency(
		amount: number,
		fromCurrency: string,
		toCurrency: string,
		fetchFn: typeof fetch = fetch
	): Promise<APIResponse<CurrencyConversion>> {
		const params = new URLSearchParams({
			amount: amount.toString(),
			from_currency: fromCurrency,
			to_currency: toCurrency
		});

		const response = await fetchFn(`${this.baseUrl}/api/v1/convert?${params}`);
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	/**
	 * Force update currency exchange rates (admin function)
	 */
	async updateCurrencies(fetchFn: typeof fetch = fetch): Promise<APIResponse<any>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/currencies/update`, {
			method: 'POST'
		});
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

	/**
	 * Refresh currency rates if they're older than 23 hours
	 */
	async refreshCurrencies(fetchFn: typeof fetch = fetch): Promise<APIResponse<any>> {
		const response = await fetchFn(`${this.baseUrl}/api/v1/currencies/refresh`, {
			method: 'POST'
		});
		if (!response.ok) {
			throw new Error(`HTTP error! status: ${response.status}`);
		}
		return response.json();
	}

}

// Export a default instance
export const api = new KissatenAPI();

// Export a factory function for creating API instances with default currency
export function createAPIWithCurrency(currency?: string): KissatenAPI {
	return new KissatenAPI(API_BASE_URL, currency);
}
