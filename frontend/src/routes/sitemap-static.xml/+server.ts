import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
export const prerender = true;

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
	const origin = env.ORIGIN || SITE_URL;
	const staticRoutes = [
		{ path: '', priority: '1.0', changefreq: 'weekly' },
		{ path: 'search', priority: '0.9', changefreq: 'daily' },
		{ path: 'roasters', priority: '0.9', changefreq: 'daily' },
		{ path: 'origins', priority: '0.9', changefreq: 'daily' },
		{ path: 'roasted-in', priority: '0.8', changefreq: 'weekly' },
		{ path: 'varietals', priority: '0.8', changefreq: 'daily' },
		{ path: 'processes', priority: '0.8', changefreq: 'daily' },
		{ path: 'flavours', priority: '0.7', changefreq: 'daily' }
	];

	const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${staticRoutes
	.map(
		(r) => `	<url>
		<loc>${escapeXml(`${origin}/${r.path}`)}</loc>
		<changefreq>${r.changefreq}</changefreq>
		<priority>${r.priority}</priority>
	</url>`
	)
	.join('\n')}
</urlset>`;

	setHeaders({
		'Content-Type': 'application/xml; charset=utf-8',
		'Cache-Control': 'public, max-age=3600, s-maxage=86400'
	});

	return new Response(body);
};
