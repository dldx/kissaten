export type SeoProps = {
	title?: string;
	description?: string;
	image?: string;
	url?: string;
	type?: 'website' | 'article' | 'product';
	noindex?: boolean;
	product?: {
		name: string;
		brand?: string;
		description?: string;
		image?: string;
		price?: number | null;
		currency?: string | null;
		sku?: string | null;
		inStock?: boolean | null;
	};
};

export const defaultSeo = {
	siteName: 'Kissaten',
	siteUrl: 'https://kissaten.app',
	defaultImage: '/og/default',
	twitterCard: 'summary_large_image',
	locale: 'en_US',
} as const;

export function toAbsoluteUrl(pathOrUrl: string): string {
	if (!pathOrUrl) return `${defaultSeo.siteUrl}${defaultSeo.defaultImage}`;
	if (/^https?:\/\//.test(pathOrUrl)) return pathOrUrl;
	return `${defaultSeo.siteUrl}${pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`}`;
}

export function buildTitle(pageTitle: string | undefined): string {
	if (!pageTitle) return defaultSeo.siteName;
	const trimmed = pageTitle.trim();
	if (trimmed.length === 0) return defaultSeo.siteName;
	if (trimmed.includes('|') || trimmed.toLowerCase().endsWith(defaultSeo.siteName.toLowerCase())) {
		return trimmed;
	}
	return `${trimmed} | ${defaultSeo.siteName}`;
}

export function safeJsonLdStringify(payload: unknown): string {
	return JSON.stringify(payload)
		.replace(/</g, '\\u003c')
		.replace(/>/g, '\\u003e')
		.replace(/&/g, '\\u0026');
}
