import { api, type CoffeeBean } from '$lib/api';
import { beanUrl, isoDate, urlNode, wrapUrlset, SITE_URL } from '$lib/server/sitemap';

const PAGE_SIZE = 100;
const PART_SIZE = 5000;

type PageRange = { startPage: number; endPage: number };

function planParts(totalPages: number): PageRange[] {
	const pagesPerPart = Math.floor(PART_SIZE / PAGE_SIZE);
	const parts: PageRange[] = [];
	let p = 1;
	while (p <= totalPages) {
		parts.push({ startPage: p, endPage: Math.min(p + pagesPerPart - 1, totalPages) });
		p += pagesPerPart;
	}
	return parts;
}

export async function buildBeansSitemapPart(
	part: number,
	fetchFn: typeof fetch = fetch
): Promise<string> {
	const first = await api.search(
		{ page: 1, per_page: PAGE_SIZE, sort_by: 'date_added', sort_order: 'desc' },
		fetchFn
	);
	if (!first.success || !first.data) {
		return wrapUrlset([]);
	}
	const totalPages = first.pagination?.total_pages ?? 1;
	const plan = planParts(totalPages);
	if (part >= plan.length) return wrapUrlset([]);

	const { startPage, endPage } = plan[part];
	const targetCount = (endPage - startPage + 1) * PAGE_SIZE;

	if (startPage === 1) {
		const beans: CoffeeBean[] = first.data;
		if (endPage > 1) {
			const extras = await Promise.all(
				Array.from({ length: endPage - 1 }, (_, i) =>
					api.search(
						{ page: i + 2, per_page: PAGE_SIZE, sort_by: 'date_added', sort_order: 'desc' },
						fetchFn
					)
				)
			);
			for (const r of extras) if (r.success && r.data) beans.push(...r.data);
		}
		return renderSitemapPart(beans.slice(0, targetCount));
	}

	const pages = await Promise.all(
		Array.from({ length: endPage - startPage + 1 }, (_, i) =>
			api.search(
				{ page: startPage + i, per_page: PAGE_SIZE, sort_by: 'date_added', sort_order: 'desc' },
				fetchFn
			)
		)
	);
	const beans: CoffeeBean[] = [];
	for (const r of pages) if (r.success && r.data) beans.push(...r.data);
	return renderSitemapPart(beans);
}

function renderSitemapPart(beans: CoffeeBean[]): string {
	const seen = new Set<string>();
	const nodes: string[] = [];
	for (const bean of beans) {
		const url = beanUrl(bean);
		if (!url) continue;
		if (seen.has(url)) continue;
		seen.add(url);
		nodes.push(
			urlNode(url, {
				lastmod: isoDate(bean.date_added) || isoDate(bean.scraped_at),
				changefreq: 'weekly',
				priority: '0.8'
			})
		);
	}
	return wrapUrlset(nodes);
}

export { SITE_URL, planParts };
