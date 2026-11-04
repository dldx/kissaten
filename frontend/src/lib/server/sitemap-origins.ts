import { api } from '$lib/api';
import { urlNode, wrapUrlset, SITE_URL } from '$lib/server/sitemap';

/**
 * Origins sitemap builder.
 *
 * A single `/v1/origins/sitemap-entries` call returns every region row
 * (`farm_name` null) and every farm row for all countries. Earlier versions
 * issued one request per country *and* one per region (thousands of serialized
 * requests) and then probed the *public* site with a `HEAD` request for every
 * region/farm to filter dead links — that hairpinned every probe back through
 * Cloudflare and made the route take minutes.
 */
type SitemapEntry = {
	country_code: string;
	region_name: string;
	farm_name: string | null;
};

let cached: { xml: string; at: number } | null = null;
const CACHE_TTL_MS = 60 * 60 * 1000;

export async function buildOriginsSitemap(fetchFn: typeof fetch = fetch): Promise<string> {
	if (cached && Date.now() - cached.at < CACHE_TTL_MS) return cached.xml;

	const res = await api.getOriginsSitemapEntries(fetchFn);
	if (!res.success || !res.data) return wrapUrlset([]);
	const entries: SitemapEntry[] = res.data;

	const seen = new Set<string>();
	const nodes: string[] = [];
	const add = (url: string, opts: Parameters<typeof urlNode>[1]) => {
		if (seen.has(url)) return;
		seen.add(url);
		nodes.push(urlNode(url, opts));
	};

	for (const countryCode of new Set(entries.map((e) => e.country_code))) {
		add(`${SITE_URL}/origins/${countryCode}`, { changefreq: 'weekly', priority: '0.6' });
	}

	const regionSlugFor = new Map<string, string>();
	for (const entry of entries) {
		const key = `${entry.country_code}/${entry.region_name}`;
		let slug = regionSlugFor.get(key);
		if (slug === undefined) {
			slug = api.normalizeRegionName(entry.region_name);
			regionSlugFor.set(key, slug);
		}
		if (!slug) continue;
		add(`${SITE_URL}/origins/${entry.country_code}/${slug}`, {
			changefreq: 'weekly',
			priority: '0.5',
		});
	}

	for (const entry of entries) {
		if (!entry.farm_name) continue;
		const regionSlug = regionSlugFor.get(`${entry.country_code}/${entry.region_name}`);
		const farmSlug = api.normalizeFarmName(entry.farm_name);
		if (!regionSlug || !farmSlug) continue;
		add(`${SITE_URL}/origins/${entry.country_code}/${regionSlug}/${farmSlug}`, {
			changefreq: 'monthly',
			priority: '0.4',
		});
	}

	const xml = wrapUrlset(nodes);
	// Only memoize a real result — never cache an upstream failure.
	if (nodes.length > 0) cached = { xml, at: Date.now() };
	return xml;
}
