import { error } from "@sveltejs/kit";
import {
  api,
  type CoffeeBean,
  type Roaster,
  type RoasterDetailResponse,
} from "$lib/api.js";
import { findLatestSearchForRoaster } from "$lib/offline/apiCache";
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

    let beans: Promise<CoffeeBean[]> = beansPromise.then((r) => r.data ?? []);
    let pagination: Promise<any> = beansPromise.then(
      (r) => r.pagination ?? null,
    );

    // Client-side only: if the network search takes >3s (offline / very slow),
    // fall back to the latest cached `/api/v1/search` response for this
    // roaster instead of leaving the `{#await}` blocks hanging. The shapes stay
    // identical (`data` array / `pagination` object).
    if (!import.meta.env.SSR) {
      const TIMED_OUT = Symbol("timed-out");
      const timer = new Promise<symbol>((resolve) =>
        setTimeout(() => resolve(TIMED_OUT), 3000),
      );

      const cachedSearch = (async () => {
        try {
          return (await findLatestSearchForRoaster(detail.name)) ?? undefined;
        } catch {
          return undefined;
        }
      })();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const withCacheFallback = async (
        network: Promise<any>,
        fromCache: (hit: any) => any,
        noHit: any,
      ): Promise<any> => {
        try {
          const result = await Promise.race([network, timer]);
          if (result === TIMED_OUT) {
            const hit = await cachedSearch;
            return hit ? fromCache(hit.json) : noHit;
          }
          return result;
        } catch {
          // Network rejected → try the cache before giving up.
          const hit = await cachedSearch.catch(() => undefined);
          return hit ? fromCache(hit.json) : noHit;
        }
      };

      beans = withCacheFallback(beans, (json: any) => json.data ?? [], []);
      pagination = withCacheFallback(
        pagination,
        (json: any) => json?.pagination ?? null,
        null,
      );
    }

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
      beans,
      pagination,
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
