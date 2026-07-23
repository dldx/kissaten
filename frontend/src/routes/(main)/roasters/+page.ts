import { api, type Roaster } from "$lib/api.js";
import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch, data }) => {
  try {
    const response = await api.getRoasters(fetch);

    if (!response.success || !response.data) {
      throw error(500, {
        message: response.message || "Failed to load roasters",
      });
    }

    // `suggestions` are loaded by the sibling `+page.server.ts` (which calls
    // the `getRoasterSuggestions` remote query on the server) and surfaced to
    // us via the `data` arg. We pass them through so the component's
    // `data.suggestions` is populated without a client-side /_app/remote fetch.
    return {
      roasters: response.data,
      suggestions: data.suggestions,
    };
  } catch (err) {
    console.error("Error loading roasters data:", err);
    throw error(500, {
      message:
        err instanceof Error
          ? err.message
          : "An error occurred while loading roasters data",
    });
  }
};
