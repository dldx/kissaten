import type { APIResponse } from "./api";

export interface OriginSearchResult {
    type: "country" | "region" | "farm";
    name: string;
    country_code: string;
    country_name: string;
    region_name?: string | null;
    region_slug?: string | null;
    farm_slug?: string | null;
    producer_name?: string | null;
    bean_count: number;
}

/**
 * Search for countries, regions, and farms matching the query.
 * 
 * @param query - The search query string
 * @param limit - Maximum number of results to return (default: 20)
 * @param fetchFn - Optional fetch function (defaults to window.fetch)
 * @returns A promise that resolves to the API response with search results
 */
export async function searchOrigins(
    query: string,
    limit: number = 20,
    fetchFn: typeof fetch = fetch
): Promise<APIResponse<OriginSearchResult[]>> {
    const params = new URLSearchParams({ q: query, limit: limit.toString() });
    const response = await fetchFn(`/api/v1/search/origins?${params.toString()}`);

    if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
            const errorData = await response.json();
            if (errorData.detail) {
                errorMessage = errorData.detail;
            } else if (errorData.message) {
                errorMessage = errorData.message;
            }
        } catch (e) {
            // Fallback to default message
        }
        throw new Error(errorMessage);
    }

    return response.json();
}
