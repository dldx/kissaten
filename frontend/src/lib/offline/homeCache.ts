import type { CarouselItem, HomePageData } from "../../routes/(main)/+page.ts";
import {
  getCached,
  listCachedBeanSnapshots,
  isBrowserDbAvailable,
} from "./apiCache";

/**
 * Reconstruct a `HomePageData`-shaped payload purely from the Dexie cache
 * (Phase 0 / Phase 2). Used client-side when the streamed `dataPromise` on the
 * home page cannot resolve offline (or within a short race timeout).
 *
 * Returns `null` when nothing usable is cached (callers keep their current
 * default behavior in that case). Never throws.
 */
export async function getCachedHomeData(): Promise<HomePageData | null> {
  if (import.meta.env.SSR || !isBrowserDbAvailable()) return null;

  try {
    const [statsEntry, roastersEntry, processesEntry, varietalsEntry] =
      await Promise.all([
        getCached("/api/v1/stats"),
        getCached("/api/v1/roasters"),
        getCached("/api/v1/processes"),
        getCached("/api/v1/varietals"),
      ]);
    const beanSnapshots = await listCachedBeanSnapshots(4);

    // Same defaults as fetchHomePageData in (main)/+page.ts.
    const data: HomePageData = {
      carouselItems: [],
      coffeeBeans: [],
      roasters: [],
      processes: [],
      varietals: [],
      stats: {
        totalBeans: 5000,
        totalRoasters: 150,
        totalFarms: 1000,
        totalFlavours: 200,
        totalRoasterCountries: 20,
        totalOriginCountries: 45,
      },
    };

    // Stats — parsed identically to fetchHomePageData.
    if (statsEntry?.json?.success && statsEntry.json.data) {
      const s = statsEntry.json.data;
      data.stats = {
        totalBeans: s.total_beans,
        totalRoasters: s.total_roasters,
        totalFarms: s.total_farms,
        totalFlavours: s.total_flavours,
        totalRoasterCountries: s.total_roaster_countries,
        totalOriginCountries: s.total_origin_countries,
      };
    }

    // Carousel beans ← catalogue bean snapshots.
    data.coffeeBeans = beanSnapshots.map((b) => b.beanData);

    // Roasters ← cached /api/v1/roasters (same filter/shuffle logic).
    if (
      roastersEntry?.json?.success &&
      Array.isArray(roastersEntry.json.data)
    ) {
      data.roasters = roastersEntry.json.data
        .filter((r: any) => (r?.current_beans_count ?? 0) > 0)
        .sort(() => Math.random() - 0.5)
        .slice(0, 4);
    }

    // Processes ← cached /api/v1/processes (flatten categories, slice 4).
    if (processesEntry?.json?.success && processesEntry.json.data) {
      const all = Object.values(processesEntry.json.data).flatMap(
        (category: any) => category?.processes ?? [],
      );
      data.processes = all.sort(() => Math.random() - 0.5).slice(0, 4);
    }

    // Varietals ← cached /api/v1/varietals (flatten categories, slice 4).
    if (varietalsEntry?.json?.success && varietalsEntry.json.data) {
      const all = Object.values(varietalsEntry.json.data).flatMap(
        (category: any) => category?.varietals ?? [],
      );
      data.varietals = all.sort(() => Math.random() - 0.5).slice(0, 4);
    }

    // Combined + shuffled carousel items, mirroring fetchHomePageData.
    const combinedItems: CarouselItem[] = [
      ...data.coffeeBeans.map((bean) => ({
        type: "bean" as const,
        data: bean,
        key: `bean-${bean.id}`,
      })),
      ...data.roasters.map((roaster) => ({
        type: "roaster" as const,
        data: roaster,
        key: `roaster-${roaster.id}`,
      })),
      ...data.processes.map((process) => ({
        type: "process" as const,
        data: process,
        key: `process-${process.slug}`,
      })),
      ...data.varietals.map((varietal) => ({
        type: "varietal" as const,
        data: varietal,
        key: `varietal-${varietal.slug}`,
      })),
    ];
    data.carouselItems = combinedItems.sort(() => Math.random() - 0.5);

    // "Usable" = at least some stats OR some carousel items.
    if (!statsEntry && combinedItems.length === 0) return null;
    return data;
  } catch (error) {
    console.warn("Error building cached home data:", error);
    return null;
  }
}
