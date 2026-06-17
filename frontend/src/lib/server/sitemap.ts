import { env } from '$env/dynamic/private';
import { api } from '$lib/api';
import type { CoffeeBean, Process, Varietal } from '$lib/api';

export const API_BASE = env.PUBLIC_API_BASE || env.API_BASE_URL || 'https://kissaten.app';
export const SITE_URL = env.ORIGIN || 'https://kissaten.app';

export function escapeXml(value: string | number | null | undefined): string {
	if (value === null || value === undefined) return '';
	return String(value)
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&apos;');
}

export function urlNode(
	loc: string,
	options: { lastmod?: string | null; changefreq?: string; priority?: string } = {}
): string {
	const parts = [`\t<url>`, `\t\t<loc>${escapeXml(loc)}</loc>`];
	if (options.lastmod) parts.push(`\t\t<lastmod>${options.lastmod}</lastmod>`);
	if (options.changefreq) parts.push(`\t\t<changefreq>${options.changefreq}</changefreq>`);
	if (options.priority) parts.push(`\t\t<priority>${options.priority}</priority>`);
	parts.push('\t</url>');
	return parts.join('\n');
}

export function wrapUrlset(nodes: string[]): string {
	return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${nodes.join('\n')}
</urlset>`;
}

export function beanUrl(bean: { bean_url_path?: string | null; clean_url_slug?: string; roaster?: string }): string | null {
	if (bean.bean_url_path) {
		const path = bean.bean_url_path.startsWith('/') ? bean.bean_url_path : `/${bean.bean_url_path}`;
		return `${SITE_URL}/roasters${path}`;
	}
	if (bean.clean_url_slug && bean.roaster) {
		const roasterSlug = bean.roaster.toLowerCase().replace(/\s+/g, '_');
		return `${SITE_URL}/roasters/${roasterSlug}/${bean.clean_url_slug}`;
	}
	return null;
}

export function isoDate(value: string | null | undefined): string | null {
	if (!value) return null;
	const d = new Date(value);
	if (isNaN(d.getTime())) return null;
	return d.toISOString().slice(0, 10);
}

type ProbeCache = Map<string, 'ok' | 'fail'>;
const probeCache: ProbeCache = (globalThis as any).__sitemapProbeCache ?? new Map();
(globalThis as any).__sitemapProbeCache = probeCache;
let lastProbeReset = 0;
const PROBE_TTL_MS = 24 * 60 * 60 * 1000;

function resetCacheIfStale() {
	const now = Date.now();
	if (now - lastProbeReset > PROBE_TTL_MS) {
		probeCache.clear();
		lastProbeReset = now;
	}
}

export async function headOk(url: string, timeoutMs = 5000): Promise<boolean> {
	resetCacheIfStale();
	const cached = probeCache.get(url);
	if (cached === 'ok') return true;
	if (cached === 'fail') return false;

	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeoutMs);
	try {
		const res = await fetch(url, { method: 'HEAD', signal: controller.signal });
		if (res.status === 200) {
			probeCache.set(url, 'ok');
			return true;
		}
		probeCache.set(url, 'fail');
		return false;
	} catch (e) {
		probeCache.set(url, 'fail');
		return false;
	} finally {
		clearTimeout(timer);
	}
}

export async function fetchAllBeans(fetchFn: typeof fetch = fetch): Promise<CoffeeBean[]> {
	const pageSize = 100;
	const first = await api.search({ page: 1, per_page: pageSize, sort_by: 'date_added', sort_order: 'desc' }, fetchFn);
	if (!first.success || !first.data) return [];
	const totalPages = first.pagination?.total_pages ?? 1;
	if (totalPages <= 1) return first.data;

	const remaining = await Promise.all(
		Array.from({ length: totalPages - 1 }, (_, i) =>
			api.search({ page: i + 2, per_page: pageSize, sort_by: 'date_added', sort_order: 'desc' }, fetchFn)
		)
	);
	const beans: CoffeeBean[] = [...first.data];
	for (const r of remaining) {
		if (r.success && r.data) beans.push(...r.data);
	}
	return beans;
}

export async function fetchAllProcesses(fetchFn: typeof fetch = fetch): Promise<Process[]> {
	const res = await api.getProcesses(fetchFn);
	if (!res.success || !res.data) return [];
	const all: Process[] = [];
	for (const cat of Object.values(res.data)) {
		all.push(...cat.processes);
	}
	return all;
}

export async function fetchAllVarietals(fetchFn: typeof fetch = fetch): Promise<Varietal[]> {
	const res = await api.getVarietals(fetchFn);
	if (!res.success || !res.data) return [];
	const all: Varietal[] = [];
	for (const cat of Object.values(res.data)) {
		all.push(...cat.varietals);
	}
	return all;
}
