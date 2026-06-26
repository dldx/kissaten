import { error } from "@sveltejs/kit";
import {
  api,
  type CoffeeBean,
  type Roaster,
  type RoasterDetailResponse,
} from "$lib/api.js";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ params, url, fetch, parent }) => {
  const slug = params.roaster_name;

  const parentData = await parent();
  const convertToCurrency = parentData?.currencyState?.selectedCurrency;

  const page = parseInt(url.searchParams.get("page") || "1");
  const per_page = parseInt(url.searchParams.get("per_page") || "20");
  const sort_by = url.searchParams.get("sort_by") || "date_added";
  const sort_order = url.searchParams.get("sort_order") || "desc";

  try {
    const roasterResponse = await api.getRoasterDetail(
      slug,
      convertToCurrency || undefined,
      fetch,
    );

    if (!roasterResponse.success || !roasterResponse.data) {
      if (
        roasterResponse.message &&
        roasterResponse.message.toLowerCase().includes("not found")
      ) {
        throw error(404, {
          message: `Roaster "${slug}" not found`,
        });
      }
      throw error(500, {
        message: roasterResponse.message || "Failed to load roaster",
      });
    }

    const detail = roasterResponse.data as RoasterDetailResponse;

    const roaster: Roaster = {
      id: detail.id,
      name: detail.name,
      slug: detail.slug,
      website: detail.website || "",
      location: detail.location || "",
      email: "",
      active: true,
      last_scraped: detail.last_scraped ?? null,
      total_beans_scraped: detail.statistics.total_beans,
      current_beans_count: detail.statistics.total_beans,
      location_codes: detail.country_code ? [detail.country_code] : [],
      country_slug: detail.country_slug ?? null,
      region_slug: detail.region_slug ?? null,
      description: detail.description ?? null,
    };

    const beansPromise = api.search(
      {
        roaster: detail.name,
        page,
        per_page,
        sort_by,
        sort_order,
        convert_to_currency: convertToCurrency || undefined,
      },
      fetch,
    );

    return {
      roaster,
      statistics: detail.statistics,
      top_origins: detail.top_origins,
      varietals: detail.varietals,
      processing_methods: detail.processing_methods,
      common_tasting_notes: detail.common_tasting_notes,
      flavour_categories: detail.flavour_categories,
      roast_distribution: detail.roast_distribution,
      uniqueness: detail.uniqueness,
      beans: beansPromise.then((r) => r.data ?? []),
      pagination: beansPromise.then((r) => r.pagination ?? null),
      queryParams: {
        page,
        per_page,
        sort_by,
        sort_order,
      },
    };
  } catch (err) {
    if (err && typeof err === "object" && "status" in err) {
      throw err;
    }
    throw error(500, {
      message:
        err instanceof Error
          ? err.message
          : "An error occurred while loading roaster details",
    });
  }
};
