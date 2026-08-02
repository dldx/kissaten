import { command, getRequestEvent } from "$app/server";
import { db } from "$lib/server/database";
import { pageFeedback } from "$lib/server/database/schema";
import { feedbackSchema } from "$lib/schema/feedback";
import { notifyAdminPageFeedback } from "$lib/server/admin-notifications";
import { nanoid } from "nanoid";

function safeClientIp(): string | null {
  try {
    const { getClientAddress } = getRequestEvent();
    const addr = getClientAddress();
    return typeof addr === "string" && addr.length > 0 ? addr : null;
  } catch {
    return null;
  }
}

export type SubmitFeedbackResult = { status: "submitted"; id: string };

/**
 * Submit a page-feedback report. Auth-optional: anonymous submissions are
 * allowed (with optional contact email). The honeypot field (`website`) in
 * the schema rejects any non-empty value with a 400, which catches most
 * naive bots.
 */
export const submitFeedback = command(
  feedbackSchema,
  async (data): Promise<SubmitFeedbackResult> => {
    const { locals, request } = getRequestEvent();
    const reporterUserId = locals.user?.id ?? null;
    const reporterEmail = data.reporterEmail?.trim() || null;
    const reporterUserAgent = request.headers.get("user-agent") ?? null;

    const fields = data.fields.map((f) => ({
      key: f.key,
      label: f.label,
      value: f.value,
      suggestedValue: f.suggestedValue,
      group: f.group,
      originIndex: f.originIndex,
    }));

    const id = `fbk_${nanoid()}`;
    const now = new Date();

    await db.insert(pageFeedback).values({
      id,
      kind: data.kind,
      entitySlug: data.entitySlug?.trim() || null,
      entityUrlPath: data.entityUrlPath?.trim() || null,
      entityName: data.entityName?.trim() || null,
      pageUrl: data.pageUrl,
      pageTitle: data.pageTitle?.trim() || null,
      fields,
      message: data.message,
      reporterUserId,
      reporterEmail,
      reporterUserAgent,
      reporterIp: safeClientIp(),
      status: "new",
      createdAt: now,
      updatedAt: now,
    });

    const fieldsSummary = fields.length
      ? fields
          .map((f) => {
            const tag = f.group ? `[${f.group}] ` : "";
            const current = f.value ? ` (current: ${f.value})` : "";
            const suggested = f.suggestedValue
              ? ` → suggested: ${f.suggestedValue}`
              : "";
            return `${tag}${f.label}${current}${suggested}`;
          })
          .join("\n")
      : "(general feedback — no specific fields)";

    notifyAdminPageFeedback({
      email: reporterEmail ?? locals.user?.email ?? "anonymous",
      name: locals.user?.name ?? null,
      kind: data.kind,
      entityName: data.entityName ?? null,
      entityUrlPath: data.entityUrlPath ?? data.pageUrl,
      fields: fieldsSummary,
      message: data.message,
      at: now,
    });

    return { status: "submitted", id };
  },
);
