import { command, getRequestEvent, query } from "$app/server";
import { z } from "zod";
import { and, desc, eq } from "drizzle-orm";
import { error } from "@sveltejs/kit";
import { db } from "$lib/server/database";
import { pageFeedback } from "$lib/server/database/schema";
import { feedbackSchema } from "$lib/schema/feedback";
import { notifyAdminPageFeedback } from "$lib/server/admin-notifications";
import { nanoid } from "nanoid";

function requireAdmin() {
  const { locals } = getRequestEvent();
  if (!locals.user) {
    throw error(401, "Authentication required.");
  }
  if (locals.user.role !== "admin") {
    throw error(403, "Admin access required.");
  }
  return locals.user;
}

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

export type ProductReviewDecision = "approved" | "rejected";

export interface ProductReviewDecisionRow {
  entityUrlPath: string;
  decision: ProductReviewDecision;
  decidedAt: number; // created_at ms
}

/**
 * List the LATEST admin review decision per entity_url_path from page_feedback
 * (kind='product-review'). Admin-only. Used by the review queue to distinguish
 * pending items from already-decided ones.
 */
export const listProductReviewDecisions = query(
  async (): Promise<ProductReviewDecisionRow[]> => {
    requireAdmin();
    const rows = await db
      .select({
        entityUrlPath: pageFeedback.entityUrlPath,
        fields: pageFeedback.fields,
        createdAt: pageFeedback.createdAt,
      })
      .from(pageFeedback)
      .where(eq(pageFeedback.kind, "product-review"));

    // Dedupe: latest row per entityUrlPath wins (max createdAt).
    const latest = new Map<string, ProductReviewDecisionRow>();
    for (const row of rows) {
      const decision = row.fields?.find((f) => f.key === "decision")?.value;
      if (!row.entityUrlPath || !decision) continue;
      if (decision !== "approved" && decision !== "rejected") continue;
      const entry: ProductReviewDecisionRow = {
        entityUrlPath: row.entityUrlPath,
        decision,
        decidedAt: row.createdAt.getTime(),
      };
      const existing = latest.get(row.entityUrlPath);
      if (!existing || entry.decidedAt > existing.decidedAt) {
        latest.set(row.entityUrlPath, entry);
      }
    }
    return [...latest.values()];
  },
);
export type SubmitProductReviewResult = { status: "submitted"; id: string };

/**
 * Record an admin product-review decision (tasting kits, etc.) into the
 * page_feedback table. The decision lives in fields[0] as {key:"decision"}.
 */
export const submitProductReview = command(
  z.object({
    entityUrlPath: z.string().min(1).max(500),
    entitySlug: z.string().max(200).optional().or(z.literal("")),
    entityName: z.string().max(200).optional().or(z.literal("")),
    decision: z.enum(["approved", "rejected"]),
  }),
  async (data): Promise<SubmitProductReviewResult> => {
    const { locals } = getRequestEvent();
    const reporterUserId = locals.user?.id ?? null;
    const entityUrlPath = data.entityUrlPath.trim();
    const id = `fbk_${nanoid()}`;
    const now = new Date();

    // Dedupe guard: if the latest recorded decision for this entity already
    // matches the submitted decision, don't insert a duplicate row — return
    // the existing id. Prevents the queue from accumulating a pile of
    // identical decision rows from repeated clicks.
    const latest = await db
      .select({
        id: pageFeedback.id,
        fields: pageFeedback.fields,
      })
      .from(pageFeedback)
      .where(
        and(
          eq(pageFeedback.kind, "product-review"),
          eq(pageFeedback.entityUrlPath, entityUrlPath),
        ),
      )
      .orderBy(desc(pageFeedback.createdAt))
      .limit(1);
    const latestDecision = latest[0]?.fields?.find(
      (f) => f.key === "decision",
    )?.value;
    if (latestDecision === data.decision && latest[0]) {
      return { status: "submitted", id: latest[0].id };
    }

    await db.insert(pageFeedback).values({
      id,
      kind: "product-review",
      entityUrlPath,
      entitySlug: data.entitySlug?.trim() || null,
      entityName: data.entityName?.trim() || null,
      pageUrl: data.entityUrlPath, // deep link back to the bean
      fields: [{ key: "decision", label: "Decision", value: data.decision }],
      message: `Product review: ${data.decision}`,
      reporterUserId,
      reporterUserAgent: null,
      reporterIp: null,
      status: "new",
      createdAt: now,
      updatedAt: now,
    });
    // notifyAdminPageFeedback so the admin email digest mentions reviews too —
    // keep it optional/silent; wrap in try/catch.
    // Skipped here: decisions are recorded in the page_feedback table, which is
    // enough for the admin review queue. (notifyAdminPageFeedback is available
    // if we later want the email digest to mention review decisions.)
    return { status: "submitted", id };
  },
);
