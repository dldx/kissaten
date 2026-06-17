import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';


const SITE_URL = 'https://kissaten.app';

function escapeXml(value: string): string {
	return value
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}

export const GET: RequestHandler = async ({ setHeaders }) => {
	const now = new Date().toISOString().slice(0, 10);
	const origin = env.ORIGIN || SITE_URL;

	const subSitemaps = [
		{ loc: `${origin}/sitemap-static.xml`, lastmod: now },
		{ loc: `${origin}/sitemap-processes.xml`, lastmod: now },
		{ loc: `${origin}/sitemap-varietals.xml`, lastmod: now },
		{ loc: `${origin}/sitemap-origins.xml`, lastmod: now }
	];

	const body = `<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${subSitemaps
	.map(
		(s) => `	<sitemap>
		<loc>${escapeXml(s.loc)}</loc>
		<lastmod>${s.lastmod}</lastmod>
	</sitemap>`
	)
	.join('\n')}
</sitemapindex>`;

	setHeaders({
		'Content-Type': 'application/xml; charset=utf-8',
		'Cache-Control': 'public, max-age=3600, s-maxage=86400'
	});

	return new Response(body);
};
