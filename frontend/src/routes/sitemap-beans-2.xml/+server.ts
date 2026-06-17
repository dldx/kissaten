import type { RequestHandler } from './$types';
import { buildBeansSitemapPart } from '$lib/server/sitemap-beans';


export const GET: RequestHandler = async ({ fetch, setHeaders }) => {
	let body: string;
	try {
		body = await buildBeansSitemapPart(1, fetch);
	} catch (e) {
		console.error('sitemap-beans-2 fetch error:', e);
		body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>`;
	}

	setHeaders({
		'Content-Type': 'application/xml; charset=utf-8',
		'Cache-Control': 'public, max-age=3600, s-maxage=86400'
	});

	return new Response(body);
};
