import { error } from "@sveltejs/kit";
import { api, type CoffeeBean } from "$lib/api.js";
import { currencyState } from "$lib/stores/currency.svelte.js";
import { getBeanFeedbackFields } from "$lib/utils/beanFeedback";
import type { FeedbackContext } from "$lib/types/feedback";
import { OfflineError, getBeanSnapshot } from "$lib/offline/apiCache";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ params, fetch }) => {
  const { roaster_name, bean_name } = params;

  // Handle custom beans from Dexie (local-first).
  // We can't access Dexie during SSR, so we always return an empty bean
  // here and let +page.svelte's onMount hydrate it from the local vault.
  // This keeps the load function synchronous on the server and avoids
  // any race between the load and the client-side Dexie lookup.
  if (roaster_name === "custom") {
    return {
      bean: null,
      isCustom: true,
      bean_name,
    };
  }

  try {
    // The URL parameters are already in slug format (roaster_name and bean_name)
    // We can use them directly with the new slug-based endpoint
    let bean: CoffeeBean | null = null;
    let stale = false;

    try {
      // Use the new slug-based endpoint that works directly with URL slugs
      const beanResponse = await api.getBeanBySlug(
        roaster_name,
        bean_name,
        fetch,
        currencyState.selectedCurrency || undefined,
      );

      if (beanResponse.success && beanResponse.data) {
        bean = beanResponse.data;
      }
    } catch (e) {
      // Offline (or a plain network failure while offline): fall back to the
      // locally-cached bean snapshot (`bean_url_path` = /<roaster_slug>/<bean_slug>,
      // which for this route is exactly /roaster_name/bean_name). The route
      // params ARE the slugs, so the key matches what getBeanBySlug's success
      // path and trackBeanView store.
      const isOffline =
        e instanceof OfflineError ||
        (typeof navigator !== "undefined" && !navigator.onLine);

      if (isOffline) {
        const snapshot = await getBeanSnapshot(`/${roaster_name}/${bean_name}`);
        if (snapshot?.beanData) {
          bean = snapshot.beanData;
          stale = true;
        }
      }

      if (!bean) {
        console.warn("Slug-based bean search failed:", e);
      }
    }

    if (!bean && roaster_name !== "custom") {
      throw error(404, {
        message: `Coffee bean "${bean_name}" from "${roaster_name}" not found`,
      });
    }

    const feedbackContext: FeedbackContext | undefined = bean
      ? {
          kind: "bean",
          entityName: `${bean.name} · ${bean.roaster}`,
          entityUrlPath: bean.bean_url_path,
          entitySlug: `${bean.roaster}/${bean.name}`,
          fields: getBeanFeedbackFields(bean),
        }
      : undefined;

    return {
      bean,
      isCustom: false,
      feedbackContext,
      ...(stale ? { stale: true } : {}),
    };
  } catch (err) {
    if (err && typeof err === "object" && "status" in err) {
      throw err;
    }
    throw error(500, {
      message: "Failed to load coffee bean details",
    });
  }
};
