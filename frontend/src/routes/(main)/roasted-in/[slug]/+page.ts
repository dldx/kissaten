import { api } from '$lib/api';
import type { PageLoad } from './$types';
import type { Roaster } from '$lib/api';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch }) => {
    const slug = params.slug.toLowerCase();

    try {
        const locationResponse = await api.getLocationDetail(slug, fetch);

        if (locationResponse.success && locationResponse.data) {
            const location = locationResponse.data;

            // Transform roasters data
            const roasters: Roaster[] = location.top_roasters?.map((r) => ({
                id: r.id,
                name: r.name,
                slug: r.slug,
                website: r.website,
                location: r.city || r.country_name || "",
                email: "",
                active: true,
                last_scraped: null,
                total_beans_scraped: r.total_beans,
                current_beans_count: r.available_beans,
                location_codes: [],
                country_slug: slug,
                region_slug: location.region_slug,
            })) || [];

            // Prepare items for insights
            const varietalItems = location.varietals?.slice(0, 5).map((v) => ({
                label: v.variety,
                count: v.count,
                href: `/search?roaster_location=${location.region_code}&variety="${encodeURIComponent(v.variety)}"`,
            })) || [];

            const originItems = location.top_origins?.slice(0, 5).map((o) => ({
                label: o.name,
                count: o.count,
                href: `/search?roaster_location=${location.region_code}&origin=${o.code}`,
            })) || [];

            const cityItems = location.top_cities?.slice(0, 5).map((c) => ({
                label: c.note,
                count: c.frequency,
                href: `/roasted-in/${slug}`,
            })) || [];

            // Build breadcrumbs
            const breadcrumbs = [{ label: "Roasters", href: "/roasters" }];

            if (location.region_name && location.region_slug) {
                breadcrumbs.push({
                    label: location.region_name,
                    href: `/roasted-in/${location.region_slug}`,
                });
            }

            breadcrumbs.push({ label: location.location_name });

            // Build page context
            const pageContext = {
                breadcrumbs,
                title: location.location_name,
                countryCode:
                    location.location_type === "country"
                        ? location.country_code
                        : undefined,
                locationCode:
                    location.location_type === "country"
                        ? location.country_code
                        : location.region_code,
                statistics: {
                    available_beans: location.statistics.available_beans,
                    total_beans: location.statistics.total_beans,
                    roaster_count: location.statistics.roaster_count,
                    city_or_country_count:
                        location.statistics.city_count !== null
                            ? location.statistics.city_count
                            : 0,
                    city_or_country_label:
                        location.location_type === "country"
                            ? "Cities"
                            : "Countries",
                },
                insights: {
                    originItems,
                    varietalItems,
                    cityItems:
                        location.location_type === "country"
                            ? cityItems
                            : undefined,
                },
                roasters,
            };

            return {
                location,
                slug,
                roasters,
                varietalItems,
                originItems,
                cityItems,
                pageContext,
            };
        } else {
            throw error(404, `Location '${slug}' not found`);
        }
    } catch (e) {
        console.error('Error loading location detail:', e);
        throw error(404, `Location not found: ${slug}`);
    }
};
