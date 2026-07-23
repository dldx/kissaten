import { getRoasterSuggestions } from "$lib/api/roaster_suggestions.remote";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async () => {
	const suggestions = await getRoasterSuggestions();
	return { suggestions };
};
