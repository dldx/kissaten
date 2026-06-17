import { render } from 'svelte/server';
import ImageResponse from 'takumi-js/response';
import OgImage from '$lib/components/OgImage.svelte';
import { api } from '$lib/api';
import type { CoffeeBean } from '$lib/api';
import type { RequestEvent } from './$types';
import { readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import style from '../../../../app.css?inline';

function getMimeType(path: string): string {
	const ext = path.split('.').pop()?.toLowerCase();
	switch (ext) {
		case 'png': return 'image/png';
		case 'jpg':
		case 'jpeg': return 'image/jpeg';
		case 'webp': return 'image/webp';
		case 'gif': return 'image/gif';
		case 'svg': return 'image/svg+xml';
		default: return 'image/png';
	}
}

function tryReadFile(paths: string[]): { data: Buffer; mime: string } | null {
	for (const p of paths) {
		try {
			if (existsSync(p)) {
				return { data: readFileSync(p), mime: getMimeType(p) };
			}
		} catch {}
	}
	return null;
}

function toDataUrl(file: { data: Buffer; mime: string }): string {
	return `data:${file.mime};base64,${file.data.toString('base64')}`;
}

async function resolveBeanImage(
	bean: CoffeeBean,
	fetchFn: typeof fetch
): Promise<string | null> {
	const raw = (bean as any).image_data || bean.image_url || null;
	if (raw) {
		if (raw.startsWith('data:')) return raw;
		if (raw.startsWith('/')) {
			// Local path — read from filesystem
			const paths = [
				join(process.cwd(), 'static', raw),
				join(process.cwd(), '..', raw),
				join(process.cwd(), raw),
			];
			const file = tryReadFile(paths);
			if (file) return toDataUrl(file);
		}
		// External URL — fetch it
		try {
			const response = await fetchFn(raw);
			if (response.ok) {
				const buffer = Buffer.from(await response.arrayBuffer());
				const contentType = response.headers.get('content-type') || 'image/png';
				return `data:${contentType};base64,${buffer.toString('base64')}`;
			}
		} catch (e) {
			console.error('Failed to fetch external bean image:', e);
		}
	}
	// Fallback to roaster logo sticker
	const roasterSlug =
		bean.bean_url_path?.split('/')[1] ||
		bean.roaster?.toLowerCase().replace(/\s+/g, '_');
	if (!roasterSlug) return null;
	const logoPaths = [
		join(process.cwd(), '..', 'data', 'roasters', roasterSlug, 'logo_sticker.png'),
		join(process.cwd(), 'static', 'data', 'roasters', roasterSlug, 'logo_sticker.png'),
	];
	const logoFile = tryReadFile(logoPaths);
	if (logoFile) return toDataUrl(logoFile);
	return null;
}

const LOGO_SVG = readFileSync(
	join(process.cwd(), 'static', 'logo_dark_full.svg'),
	'utf-8'
)
	.replace(/ width="[\d.]+"/, '')
	.replace(/ height="[\d.]+"/, '')
	.replace('<svg', '<svg style="width:100%;height:100%;display:block"');

const QUICKSAND_FONT = readFileSync(
	join(
		process.cwd(),
		'node_modules',
		'@fontsource-variable',
		'quicksand',
		'files',
		'quicksand-latin-wght-normal.woff2'
	)
);

async function loadFonts() {
	return [
		{
			name: 'Quicksand',
			data: QUICKSAND_FONT,
			weight: 400 as const,
			style: 'normal' as const
		}
	];
}

export const GET = async ({ params, fetch: f, setHeaders }: RequestEvent) => {
	const { type, slug: slugParam } = params;
	const parts = (slugParam ?? '').split('/').filter(Boolean);
	const roaster = parts[0];
	const bean = parts[1];

	const fonts = await loadFonts();

	let variant: 'default' | 'bean' | 'origin' | 'farm' | 'process' | 'varietal' | 'roaster' | 'flavour' = 'default';
	let title = 'Kissaten';
	let subtitle = '';
	let price = '';
	let tagline = 'Discover extraordinary coffee';
	let beanData: CoffeeBean | null = null;
	let beanImageData: string | null = null;

	try {
		if (type === 'bean' && roaster && bean) {
			variant = 'bean';
			const res = await api.getBeanBySlug(roaster, bean, f);
			if (res.success && res.data) {
				beanData = res.data;
				beanImageData = await resolveBeanImage(res.data, f);
				title = res.data.name;
				subtitle = `by ${res.data.roaster}`;
				if (res.data.price && res.data.currency)
					price = `${res.data.currency} ${res.data.price.toFixed(2)}`;
				const origin =
					(res.data.origins?.[0]?.country_full_name as string | undefined) || '';
				tagline = origin ? `${origin} · Specialty Coffee` : 'Specialty Coffee';
			} else {
				title = 'Coffee Bean';
				subtitle = roaster.replace(/_/g, ' ');
			}
		} else if (type === 'origin') {
			variant = 'origin';
			const cc = (roaster || '').toUpperCase();
			const region = parts[1];
			const regionSlug = region ? api.normalizeRegionName(region) : null;
			if (regionSlug) {
				const res = await api.getRegionDetail(cc, regionSlug, f);
				if (res.success && res.data) {
					title = `${res.data.region_name}, ${res.data.country_name}`;
					const beans = res.data.statistics?.total_beans ?? 0;
					subtitle = `Explore ${beans}+ coffee beans from ${res.data.region_name}, ${res.data.country_name}`;
					tagline = ``;
				} else {
					title = region.replace(/-/g, ' ');
					subtitle = cc;
				}
			} else if (cc) {
				const res = await api.getCountryDetail(cc, f);
				if (res.success && res.data) {
					title = res.data.country_name;
					const beans = res.data.statistics?.total_beans ?? 0;
					subtitle = `Explore ${beans}+ coffee beans from ${res.data.country_name}`;
					tagline = '';
				} else {
					title = cc;
				}
			}
		} else if (type === 'farm') {
			variant = 'farm';
			const cc = (parts[0] || '').toUpperCase();
			const regionSlug = parts[1] ? api.normalizeRegionName(parts[1]) : null;
			const farmSlug = parts[2] ? api.normalizeFarmName(parts[2]) : null;
			if (cc && regionSlug && farmSlug) {
				const res = await api.getFarmDetail(cc, regionSlug, farmSlug, undefined, f);
				if (res.success && res.data) {
					title = `${res.data.farm_name}, ${res.data.country_name}`;
					const beans = res.data.beans?.length ?? 0;
					const producer = res.data.producer_name;
					subtitle = producer
						? `by ${producer} · Explore ${beans}+ coffee beans from ${res.data.farm_name}`
						: `Explore ${beans}+ coffee beans from ${res.data.farm_name}, ${res.data.region_name}, ${res.data.country_name}`;
					tagline = '';
				} else {
					title = (parts[2] || '').replace(/-/g, ' ');
					subtitle = `${(parts[1] || '').replace(/-/g, ' ')}, ${cc}`;
				}
			}
		} else if (type === 'process') {
			variant = 'process';
			const slug = (slugParam || '').split('/')[0];
			const res = await api.getProcessDetails(slug, undefined, f);
			if (res.success && res.data) {
				title = res.data.name;
				subtitle = `Explore beans using ${res.data.name.toLocaleLowerCase()} process`;
				tagline = '';
			} else {
				title = slug.replace(/-/g, ' ');
			}
		} else if (type === 'varietal') {
			variant = 'varietal';
			const slug = (slugParam || '').split('/')[0];
			const res = await api.getVarietalDetails(slug, undefined, f);
			if (res.success && res.data) {
				title = res.data.name;
				const beans = res.data.statistics?.total_beans ?? 0;
				subtitle = `Explore ${beans}+ beans of this varietal`;
				tagline = '';
			} else {
				title = slug.replace(/-/g, ' ');
			}
		} else if (type === 'roaster') {
			variant = 'roaster';
			const r = (slugParam || '').split('/')[0];
			title = r.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
			if(title === 'Custom') {
				title = 'Speciality Coffee Roaster';
			}
			tagline = '';
		} else if (type === 'flavour') {
			variant = 'flavour';
			const slug = (slugParam || '').split('/')[0];
			title = slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
			subtitle = `Explore coffee beans with ${title.toLowerCase()} tasting notes`;
			tagline = '';
		}
	} catch (e) {
		console.error('OG image render error:', e);
	}

	const { body, head } = await render(OgImage, {
		props: { variant, title, subtitle, price, tagline, bean: beanData, logoSvg: LOGO_SVG, beanImageData }
	});

	const responseOptions: any = {
		width: 1200,
		height: 630,
		stylesheets: [style]
	};
	if (fonts.length > 0) {
		responseOptions.fonts = fonts;
	}

	setHeaders({
		'Cache-Control': 'public, max-age=86400, s-maxage=604800, stale-while-revalidate=2592000'
	});

	return new ImageResponse(`${head}${body}`, responseOptions);
};
