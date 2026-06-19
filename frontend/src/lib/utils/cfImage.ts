/**
 * Helpers for building Cloudflare Image Resizing URLs.
 *
 * Cloudflare intercepts requests to `/cdn-cgi/image/<params>/<path>` on the
 * kissaten.app zone, fetches the original from the origin (nginx), and
 * returns a transformed image. The result is cached on Cloudflare's edge.
 *
 * Reference: https://developers.cloudflare.com/images/transform-images/with-url-parameters/
 *
 * Example:
 *   /cdn-cgi/image/fit=cover,width=512,quality=85/static/data/roasters/foo/123.png
 */

import { dev } from '$app/environment';

export type FitMode = 'cover' | 'contain' | 'scale-down';

export const defaultWidths = {
	bean: [400, 800, 1200, 1600, 2000],
	logo: [128, 256, 512],
	painting: [640, 1280, 1920, 2560, 3840],
} as const;

export interface CfImageOptions {
	width: number;
	dpr?: number;
	fit?: FitMode;
	quality?: number;
}

export interface SrcsetOptions {
	widths?: readonly number[];
	dprs?: readonly number[];
	fit?: FitMode;
	quality?: number;
}

const ZONE_ORIGIN = 'https://kissaten.app';

/**
 * Returns true for URLs that should be rewritten through Cloudflare's
 * /cdn-cgi/image/ endpoint:
 *  - relative paths (`/static/data/...`) — yes
 *  - same-origin absolute URLs — yes
 *  - data: / blob: URLs — no (can't be fetched by Cloudflare)
 *  - external URLs (Cloudinary, Shopify CDN, ...) — no (already optimized)
 *  - in dev mode — no (the dev server doesn't run through Cloudflare, so the
 *    /cdn-cgi/image/ path would 404)
 */
export function isTransformable(src: string): boolean {
	if (dev) return false;
	if (!src) return false;
	if (src.startsWith('data:') || src.startsWith('blob:')) return false;
	if (src.startsWith('/')) return true;
	try {
		const url = new URL(src);
		if (typeof window !== 'undefined') {
			return url.origin === window.location.origin;
		}
		return `${url.protocol}//${url.host}` === ZONE_ORIGIN;
	} catch {
		return false;
	}
}

/** Strip the origin from an absolute URL, leaving just the path + query. */
function stripOrigin(src: string): string {
	if (src.startsWith('/')) return src;
	try {
		const url = new URL(src);
		return `${url.pathname}${url.search}`;
	} catch {
		return src;
	}
}

/** Build a single Cloudflare Image Resizing URL for the given width. */
export function buildCfImage(src: string, opts: CfImageOptions): string {
	if (!isTransformable(src)) return src;
	const params: string[] = [`width=${opts.width}`];
	if (opts.dpr && opts.dpr !== 1) params.push(`dpr=${opts.dpr}`);
	if (opts.fit) params.push(`fit=${opts.fit}`);
	if (opts.quality) params.push(`quality=${opts.quality}`);
	// Add redirect on error
	params.push("onerror=redirect");
	return `/cdn-cgi/image/${params.join(",")}${stripOrigin(src)}`;
}

/**
 * Build the default `src` and a full `srcset` string.
 *
 * Supports two modes:
 * 1. Responsive (widths provided): uses `w` descriptors.
 * 2. Fixed-size (dprs and width provided): uses `x` descriptors and `dpr` param.
 *
 * Returns an empty `srcset` for non-transformable URLs.
 */
export function buildCfSrcset(
	src: string,
	opts: SrcsetOptions & { width?: number },
): { primarySrc: string; srcset: string } {
	if (!isTransformable(src)) {
		return { primarySrc: src, srcset: "" };
	}
	const fit = opts.fit ?? "cover";
	const quality = opts.quality ?? 90;

	// Mode 2: Fixed-size with DPRs (x descriptors)
	if (opts.width && opts.dprs && opts.dprs.length > 0) {
		const primarySrc = buildCfImage(src, { width: opts.width, fit, quality });
		const srcset = opts.dprs
			.map(
				(d) =>
					`${buildCfImage(src, { width: Math.round(opts.width! * d), fit, quality })} ${d}x`,
			)
			.join(", ");
		return { primarySrc, srcset };
	}

	// Mode 1: Responsive (w descriptors)
	if (opts.widths && opts.widths.length > 0) {
		const primaryWidth = opts.widths[Math.floor(opts.widths.length / 2)];
		const primarySrc = buildCfImage(src, { width: primaryWidth, fit, quality });
		const srcset = opts.widths
			.map((w) => `${buildCfImage(src, { width: w, fit, quality })} ${w}w`)
			.join(", ");
		return { primarySrc, srcset };
	}

	return { primarySrc: src, srcset: "" };
}
