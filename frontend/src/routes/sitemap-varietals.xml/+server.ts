import type { RequestHandler } from './$types';
import { fetchAllVarietals, urlNode, wrapUrlset, SITE_URL } from '$lib/server/sitemap';


export const GET: RequestHandler = async ({ fetch, setHeaders }) => {
	let body: string;
	try {
		const varietals = await fetchAllVarietals(fetch);
		const seen = new Set<string>();
		const nodes: string[] = [];
		for (const v of varietals) {
			if (!v.slug) continue;
			const url = `${SITE_URL}/varietals/${v.slug}`;
			if (seen.has(url)) continue;
			seen.add(url);
			nodes.push(urlNode(url, { changefreq: 'weekly', priority: '0.7' }));
		}
		body = wrapUrlset(nodes);
	} catch (e) {
		console.error('sitemap-varietals fetch error:', e);
		body = wrapUrlset([]);
	}

	setHeaders({
		'Content-Type': 'application/xml; charset=utf-8',
		'Cache-Control': 'public, max-age=3600, s-maxage=86400'
	});

	return new Response(body);
};
