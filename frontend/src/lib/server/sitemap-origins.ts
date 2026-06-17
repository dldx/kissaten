import { api } from '$lib/api';
import type { Country, RegionSummary, FarmSummary } from '$lib/api';
import { headOk, urlNode, wrapUrlset, SITE_URL } from '$lib/server/sitemap';

const CONCURRENCY = 8;

async function pMap<T, R>(items: T[], mapper: (item: T) => Promise<R>): Promise<R[]> {
	const results: R[] = new Array(items.length);
	let i = 0;
	async function worker() {
		while (i < items.length) {
			const my = i++;
			results[my] = await mapper(items[my]);
		}
	}
	const workers = Array.from({ length: Math.min(CONCURRENCY, items.length) }, () => worker());
	await Promise.all(workers);
	return results;
}

export async function buildOriginsSitemap(fetchFn: typeof fetch = fetch): Promise<string> {
	const countriesRes = await api.getCountries(fetchFn);
	if (!countriesRes.success || !countriesRes.data) return wrapUrlset([]);
	const countries: Country[] = countriesRes.data;

	const seen = new Set<string>();
	const nodes: string[] = [];

	for (const country of countriesRes.data ?? []) {
		const cc = country.country_code;
		if (!cc) continue;
		const countryUrl = `${SITE_URL}/origins/${cc}`;
		if (!seen.has(countryUrl)) {
			seen.add(countryUrl);
			nodes.push(urlNode(countryUrl, { changefreq: 'weekly', priority: '0.6' }));
		}
	}

	const regionLists = await pMap(countries, async (country) => {
		if (!country.country_code) return [] as RegionSummary[];
		try {
			const r = await api.getCountryRegions(country.country_code, fetchFn);
			return r.success && r.data ? r.data : [];
		} catch (e) {
			return [] as RegionSummary[];
		}
	});

	const regionPairs: { cc: string; region: RegionSummary }[] = [];
	for (let i = 0; i < countries.length; i++) {
		for (const region of regionLists[i] ?? []) {
			regionPairs.push({ cc: countries[i].country_code, region });
		}
	}

	const regionOk = await pMap(regionPairs, async ({ cc, region }) => {
		const slug = api.normalizeRegionName(region.region_name);
		if (!slug) return null;
		const url = `${SITE_URL}/origins/${cc}/${slug}`;
		const ok = await headOk(url, 8000);
		return ok ? url : null;
	});

	for (const url of regionOk) {
		if (!url) continue;
		if (seen.has(url)) continue;
		seen.add(url);
		nodes.push(urlNode(url, { changefreq: 'weekly', priority: '0.5' }));
	}

	const uniqueRegions = new Map<string, { cc: string; regionName: string }>();
	for (const { cc, region } of regionPairs) {
		const slug = api.normalizeRegionName(region.region_name);
		if (!slug) continue;
		uniqueRegions.set(`${cc}/${slug}`, { cc, regionName: region.region_name });
	}

	const farmPages = await pMap(Array.from(uniqueRegions.values()), async ({ cc, regionName }) => {
		const slug = api.normalizeRegionName(regionName);
		try {
			const r = await api.getRegionDetail(cc, slug, fetchFn);
			if (!r.success || !r.data) return [] as { cc: string; regionSlug: string; farm: FarmSummary }[];
			const farms: FarmSummary[] = (r.data as any).top_farms || [];
			return farms.map((f) => ({ cc, regionSlug: slug, farm: f }));
		} catch (e) {
			return [] as { cc: string; regionSlug: string; farm: FarmSummary }[];
		}
	});

	const farmPairs = farmPages.flat();
	const farmUrls = await pMap(farmPairs, async ({ cc, regionSlug, farm }) => {
		const farmSlug = api.normalizeFarmName(farm.farm_name);
		if (!farmSlug) return null;
		const url = `${SITE_URL}/origins/${cc}/${regionSlug}/${farmSlug}`;
		const ok = await headOk(url, 8000);
		return ok ? url : null;
	});

	for (const url of farmUrls) {
		if (!url) continue;
		if (seen.has(url)) continue;
		seen.add(url);
		nodes.push(urlNode(url, { changefreq: 'monthly', priority: '0.4' }));
	}

	return wrapUrlset(nodes);
}
