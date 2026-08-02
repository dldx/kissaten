import { z } from "zod";

export const feedbackSchema = z.object({
  kind: z.string().min(1).max(40),
  entitySlug: z.string().max(200).optional().or(z.literal("")),
  entityUrlPath: z.string().max(500).optional().or(z.literal("")),
  entityName: z.string().max(200).optional().or(z.literal("")),
  pageUrl: z.string().min(1).max(1000),
  pageTitle: z.string().max(200).optional().or(z.literal("")),
  fields: z
    .array(
      z.object({
        key: z.string().min(1).max(80),
        label: z.string().min(1).max(200),
        value: z.string().max(8000).optional(),
        suggestedValue: z.string().max(8000).optional(),
        group: z.string().max(80).optional(),
        originIndex: z.number().int().nonnegative().optional(),
      }),
    )
    .max(50)
    .default([]),
  message: z
    .string()
    .max(2000, "Please keep your message under 2000 characters"),
  reporterEmail: z
    .string()
    .email("Please enter a valid email address")
    .max(200)
    .optional()
    .or(z.literal("")),
  // Honeypot. Bots auto-fill anything that looks "required"; the empty
  // refinement means only an empty string passes. A non-empty value fails
  // validation with 400.
  website: z
    .string()
    .max(0)
    .optional(),
}).superRefine((data, ctx) => {
  // A free-text message is only required when no specific fields were
  // selected. If the user already ticked a field (and optionally suggested
  // a value), the message is optional.
  if (data.fields.length === 0 && data.message.trim().length < 20) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["message"],
      message: "Please describe the issue (at least 20 characters)",
    });
  }
});

export type FeedbackInput = z.infer<typeof feedbackSchema>;
