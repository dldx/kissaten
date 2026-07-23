import { z } from "zod";

export const roasterSuggestionSchema = z.object({
  name: z
    .string()
    .min(1, "Roaster name is required")
    .max(120, "Roaster name is too long (max 120 characters)")
    .transform((val) => val.trim()),
  country: z
    .string()
    .max(100, "Country name is too long (max 100 characters)")
    .optional()
    .transform((val) => (val ? val.trim() : undefined)),
  website: z
    .string()
    .url("Please enter a valid URL, e.g. https://example.com")
    .max(500, "Website URL is too long (max 500 characters)")
    .optional()
    .or(z.literal(""))
    .transform((val) => (val ? val.trim() : undefined)),
  // GDPR Art. 7 granular consent: per-submission opt-in to be notified
  // when this roaster is implemented. Defaults to true (opt-out by
  // unchecking), but is explicit and reversible per suggestion.
  // The form sends 'true'/'false' strings via a hidden input (see profile
  // form pattern); transform back to boolean on the server.
  notifyOnImplementation: z
    .enum(['true', 'false'])
    .transform((val) => val === 'true'),
});

export type RoasterSuggestionInput = z.infer<typeof roasterSuggestionSchema>;
