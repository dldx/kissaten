import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	const baseUrl = 'https://kissaten.app';

	// Main index pages only - no dynamic routes
	const staticRoutes = [
		{ path: '', priority: '1.0', changefreq: 'weekly' }, // Homepage
		{ path: 'search', priority: '0.9', changefreq: 'daily' },
		{ path: 'roasters', priority: '0.9', changefreq: 'daily' },
		{ path: 'origins', priority: '0.9', changefreq: 'daily' },
		{ path: 'roasted-in', priority: '0.8', changefreq: 'weekly' },
		{ path: 'varietals', priority: '0.8', changefreq: 'daily' },
		{ path: 'processes', priority: '0.8', changefreq: 'daily' },
		{ path: 'flavours', priority: '0.7', changefreq: 'daily' },
		{ path: 'vault', priority: '0.6', changefreq: 'weekly' },
	];

	const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${staticRoutes
	.map(
		(route) => `	<url>
		<loc>${baseUrl}/${route.path}</loc>
		<changefreq>${route.changefreq}</changefreq>
		<priority>${route.priority}</priority>
	</url>`
	)
	.join('\n')}
</urlset>`;

	return new Response(sitemap, {
		headers: {
			'Content-Type': 'application/xml',
			'Cache-Control': 'public, max-age=3600', // Cache for 1 hour
		},
	});
};
