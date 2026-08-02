export type FeedbackFieldInput =
  | { type: "text" }
  | { type: "number"; min?: number; max?: number; step?: number }
  | { type: "textarea"; rows?: number }
  | { type: "month" }
  | { type: "select"; options: string[] }
  | { type: "tags" };

export type FeedbackFieldOption = {
  key: string;
  label: string;
  /** Current value as the user sees it on the page. Used purely for
   *  display in the dialog and to enrich the admin email. Truncated
   *  to ~40 chars by the page's builder. */
  value?: string;
  hint?: string;
  group?: string;
  originIndex?: number;
  /** What kind of input to render for the "suggested value" box.
   *  Defaults to `text` when omitted. */
  input?: FeedbackFieldInput;
};

export type FeedbackContext = {
  kind: string;
  entityName?: string;
  entityUrlPath?: string;
  entitySlug?: string;
  fields?: FeedbackFieldOption[];
  intro?: string;
  metadata?: Record<string, unknown>;
};
