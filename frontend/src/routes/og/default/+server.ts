import { render } from 'svelte/server';
import ImageResponse from 'takumi-js/response';
import OgImage from '$lib/components/OgImage.svelte';
import type { RequestEvent } from './$types';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import style from '../../../app.css?inline';

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

export const GET = async ({ setHeaders }: RequestEvent) => {
	const { body, head } = await render(OgImage, {
		props: {
			variant: 'default',
			title: 'Specialty Coffee Database',
			subtitle: '',
			tagline: 'Discover extraordinary coffee beans from roasters and farms around the world.',
			logoSvg: LOGO_SVG
		}
	});

	const responseOptions: any = {
		width: 1200,
		height: 630,
		stylesheets: [style],
		fonts: [
			{
				name: 'Quicksand',
				data: QUICKSAND_FONT,
				weight: 400 as const,
				style: 'normal' as const
			}
		]
	};

	setHeaders({
		'Cache-Control': 'public, max-age=86400, s-maxage=604800, stale-while-revalidate=2592000'
	});

	return new ImageResponse(`${head}${body}`, responseOptions);
};
