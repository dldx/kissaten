import type { RequestHandler } from './$types';
import { buildOriginsSitemap } from '$lib/server/sitemap-origins';


export const GET: RequestHandler = async ({ fetch, setHeaders }) => {
	let body: string;
	try {
		body = await buildOriginsSitemap(fetch);
	} catch (e) {
		console.error('sitemap-origins fetch error:', e);
		body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>`;
	}

	setHeaders({
		'Content-Type': 'application/xml; charset=utf-8',
		'Cache-Control': 'public, max-age=3600, s-maxage=86400'
	});

	return new Response(body);
};
