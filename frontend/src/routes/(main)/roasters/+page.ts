import { api, type Roaster } from "$lib/api.js";
import { getRoasterSuggestions } from "$lib/api/roaster_suggestions.remote";
import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch }) => {
  try {
    const response = await api.getRoasters(fetch);

    if (!response.success || !response.data) {
      throw error(500, {
        message: response.message || "Failed to load roasters",
      });
    }

    // `getRoasterSuggestions` is a remote `query` — safe to call for
    // logged-out visitors (returns an empty array). SvelteKit remote
    // functions are awaited on the server during load.
    const suggestions = await getRoasterSuggestions();

    return {
      roasters: response.data,
      suggestions,
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
