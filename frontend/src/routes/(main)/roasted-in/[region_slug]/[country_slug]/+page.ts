import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { Roaster } from '$lib/api';
import { api } from '$lib/api';

export const load: PageLoad = async ({ params, fetch }) => {
	const { region_slug, country_slug } = params;

	// Normalize slugs
	const normalizedRegionSlug = region_slug.toLowerCase().replace(/_/g, '-');
	const normalizedCountrySlug = country_slug.toLowerCase().replace(/_/g, '-');

	// Fetch country data
	const countryResponse = await api.getLocationDetail(normalizedCountrySlug, fetch);

	if (!countryResponse.success || !countryResponse.data) {
		throw error(404, 'Country not found');
	}

	// Verify this is a country, not a region
	if (countryResponse.data.location_type !== 'country') {
		throw error(400, 'Invalid location hierarchy');
	}

	// Fetch region data to verify the hierarchy
	const regionResponse = await api.getLocationDetail(normalizedRegionSlug, fetch);

	if (!regionResponse.success || !regionResponse.data) {
		throw error(404, 'Region not found');
	}

	// Verify this is a region
	if (regionResponse.data.location_type !== 'region') {
		throw error(400, 'Invalid region');
	}

	const country = countryResponse.data;
	const region = regionResponse.data;

	// Convert location roasters to full Roaster type for components
	const roasters: Roaster[] = country.top_roasters?.map(r => ({
		id: r.id,
		name: r.name,
		slug: r.slug,
		website: r.website,
		location: r.city || r.country_name || '',
		email: '',
		active: true,
		last_scraped: null,
		total_beans_scraped: r.total_beans,
		current_beans_count: r.available_beans,
		location_codes: [],
		country_slug: normalizedCountrySlug,
		region_slug: normalizedRegionSlug,
	})) || [];

	// Prepare items for InsightCard
	const originItems = country.top_origins?.slice(0, 5).map((o) => ({
		label: o.name,
		count: o.count,
		href: `/search?roaster_location=${country.country_code}&origin=${o.code}`,
	})) || [];

	const varietalItems = country.varietals?.slice(0, 5).map((v) => ({
		label: v.variety,
		count: v.count,
		href: `/search?roaster_location=${country.country_code}&variety="${encodeURIComponent(v.variety)}"`,
	})) || [];

	// Build page context for layout
	const pageContext = {
		breadcrumbs: [
			{ label: 'Roasters', href: '/roasters' },
			{ label: region.location_name, href: `/roasted-in/${normalizedRegionSlug}` },
			{ label: country.location_name }
		],
		title: country.location_name,
		countryCode: country.country_code,
		locationCode: country.country_code,
		statistics: {
			available_beans: country.statistics.available_beans,
			total_beans: country.statistics.total_beans,
			roaster_count: country.statistics.roaster_count,
			city_or_country_count: country.statistics.city_count || 0,
			city_or_country_label: 'Cities'
		},
		insights: {
			originItems,
			varietalItems
		},
		roasters
	};

	return {
		country,
		region,
		countrySlug: normalizedCountrySlug,
		regionSlug: normalizedRegionSlug,
		roasters,
		originItems,
		varietalItems,
		pageContext
	};
};
