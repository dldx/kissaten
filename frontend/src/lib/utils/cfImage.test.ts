import { describe, expect, it, vi } from 'vitest';

// Simulate production environment: Cloudflare transforms are enabled.
vi.mock('$app/environment', () => ({ dev: false }));

import { buildCfImage, buildCfSrcset, defaultWidths, isTransformable } from './cfImage';

describe('isTransformable', () => {
	it('returns true for relative /static/data/ paths', () => {
		expect(isTransformable('/static/data/roasters/foo/bar.png')).toBe(true);
		expect(isTransformable('/static/data/flavours/paintings/Acacia.png')).toBe(true);
	});

	it('returns false for data: URLs', () => {
		expect(isTransformable('data:image/png;base64,iVBORw0KGgo=')).toBe(false);
	});

	it('returns false for blob: URLs', () => {
		expect(isTransformable('blob:https://kissaten.app/abc-123')).toBe(false);
	});

	it('returns false for empty or invalid input', () => {
		expect(isTransformable('')).toBe(false);
	});

	it('returns false for external CDN URLs (Cloudinary, Shopify)', () => {
		expect(
			isTransformable('https://res.cloudinary.com/dak-coffee-roasters/image/upload/foo.png'),
		).toBe(false);
		expect(isTransformable('https://cdn.shopify.com/s/files/1/0065/6182/products/retailbag.jpg')).toBe(
			false,
		);
	});

	it('returns true for same-origin absolute URLs (kissaten.app)', () => {
		expect(isTransformable('https://kissaten.app/static/data/roasters/foo/bar.png')).toBe(true);
	});
});

describe('buildCfImage', () => {
	it('builds a comma-separated URL with width, fit, and quality, plus onerror=redirect', () => {
		const result = buildCfImage('/static/data/roasters/foo/bar.png', {
			width: 512,
			fit: 'cover',
			quality: 85,
		});
		expect(result).toBe(
			'/cdn-cgi/image/width=512,fit=cover,quality=85,onerror=redirect/static/data/roasters/foo/bar.png',
		);
	});

	it('includes dpr when provided', () => {
		const result = buildCfImage('/static/data/roasters/foo/bar.png', {
			width: 300,
			dpr: 2,
		});
		expect(result).toBe(
			'/cdn-cgi/image/width=300,dpr=2,onerror=redirect/static/data/roasters/foo/bar.png',
		);
	});

	it('omits fit when not provided', () => {
		const result = buildCfImage('/static/data/roasters/foo/bar.png', { width: 256 });
		expect(result).toBe(
			'/cdn-cgi/image/width=256,onerror=redirect/static/data/roasters/foo/bar.png',
		);
	});

	it('returns the original URL unchanged for non-transformable sources', () => {
		const external = 'https://cdn.shopify.com/foo.png';
		expect(buildCfImage(external, { width: 512 })).toBe(external);
		expect(buildCfImage('data:image/png;base64,abc', { width: 512 })).toBe(
			'data:image/png;base64,abc',
		);
	});

	it('strips the origin from same-origin absolute URLs', () => {
		const result = buildCfImage('https://kissaten.app/static/data/roasters/foo/bar.png', {
			width: 512,
			fit: 'cover',
			quality: 85,
		});
		expect(result).toBe(
			'/cdn-cgi/image/width=512,fit=cover,quality=85,onerror=redirect/static/data/roasters/foo/bar.png',
		);
	});
});

describe('buildCfSrcset', () => {
	it('returns empty srcset and original src for non-transformable URLs', () => {
		const external = 'https://cdn.shopify.com/foo.png';
		const result = buildCfSrcset(external, { widths: defaultWidths.bean });
		expect(result.primarySrc).toBe(external);
		expect(result.srcset).toBe('');
	});

	it('produces a srcset with one entry per width and `w` descriptors (Responsive mode)', () => {
		const result = buildCfSrcset('/static/data/roasters/foo/bar.png', {
			widths: [256, 512, 1024],
			fit: 'cover',
			quality: 85,
		});
		expect(result.srcset).toBe(
			'/cdn-cgi/image/width=256,fit=cover,quality=85,onerror=redirect/static/data/roasters/foo/bar.png 256w, ' +
				'/cdn-cgi/image/width=512,fit=cover,quality=85,onerror=redirect/static/data/roasters/foo/bar.png 512w, ' +
				'/cdn-cgi/image/width=1024,fit=cover,quality=85,onerror=redirect/static/data/roasters/foo/bar.png 1024w',
		);
	});

	it('produces a srcset with `x` descriptors and scaling physical widths (Fixed mode)', () => {
		const result = buildCfSrcset('/static/data/roasters/foo/bar.png', {
			width: 300,
			dprs: [1, 2, 3],
			fit: 'contain',
		});
		expect(result.srcset).toBe(
			'/cdn-cgi/image/width=300,fit=contain,quality=90,onerror=redirect/static/data/roasters/foo/bar.png 1x, ' +
				'/cdn-cgi/image/width=600,fit=contain,quality=90,onerror=redirect/static/data/roasters/foo/bar.png 2x, ' +
				'/cdn-cgi/image/width=900,fit=contain,quality=90,onerror=redirect/static/data/roasters/foo/bar.png 3x',
		);
	});

	it('uses the middle width as the default src in responsive mode', () => {
		const result = buildCfSrcset('/static/data/roasters/foo/bar.png', {
			widths: [256, 512, 1024],
			fit: 'cover',
			quality: 85,
		});
		expect(result.primarySrc).toBe(
			'/cdn-cgi/image/width=512,fit=cover,quality=85,onerror=redirect/static/data/roasters/foo/bar.png',
		);
	});

	it('handles the logo preset with contain fit', () => {
		const result = buildCfSrcset('/static/data/roasters/foo/logo_sticker.png', {
			widths: defaultWidths.logo,
			fit: 'contain',
			quality: 85,
		});
		expect(result.srcset).toContain('fit=contain');
		expect(result.srcset).toContain(' 128w');
		expect(result.srcset).toContain(' 256w');
		expect(result.srcset).toContain(' 512w');
	});

	it('returns empty srcset when widths array is empty', () => {
		const result = buildCfSrcset('/static/data/roasters/foo/bar.png', { widths: [] });
		expect(result.srcset).toBe('');
		expect(result.primarySrc).toBe('/static/data/roasters/foo/bar.png');
	});
});

describe('defaultWidths', () => {
	it('exposes the documented presets', () => {
		expect(defaultWidths.bean).toEqual([400, 800, 1200, 1600, 2000]);
		expect(defaultWidths.logo).toEqual([128, 256, 512]);
		expect(defaultWidths.painting).toEqual([640, 1280, 1920, 2560, 3840]);
	});
});

describe('dev mode behaviour', () => {
	it('returns the original URL unchanged when dev mode is enabled', async () => {
		vi.resetModules();
		vi.doMock('$app/environment', () => ({ dev: true }));
		const { isTransformable, buildCfImage, buildCfSrcset } = await import('./cfImage');

		expect(isTransformable('/static/data/roasters/foo/bar.png')).toBe(false);
		expect(
			buildCfImage('/static/data/roasters/foo/bar.png', { width: 512, fit: 'cover' }),
		).toBe('/static/data/roasters/foo/bar.png');
		const result = buildCfSrcset('/static/data/roasters/foo/bar.png', {
			widths: [256, 512, 1024],
		});
		expect(result.primarySrc).toBe('/static/data/roasters/foo/bar.png');
		expect(result.srcset).toBe('');

		// Restore production mode for any subsequent tests
		vi.doMock('$app/environment', () => ({ dev: false }));
		vi.resetModules();
	});
});
