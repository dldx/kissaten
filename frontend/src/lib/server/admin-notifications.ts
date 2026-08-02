import { eq } from "drizzle-orm";
import { db } from "$lib/server/database";
import { user } from "$lib/server/database/schema";
import { sendEmail } from "$lib/server/email";
import {
  adminNotificationTemplate,
  ADMIN_NOTIFICATION_LOGO_ATTACHMENT,
  betaApprovedUserTemplate,
  USER_EMAIL_LOGO_ATTACHMENT,
  type AdminNotificationKind,
} from "$lib/server/email-templates";

function isEnabled(): boolean {
  const raw = process.env.ADMIN_NOTIFICATIONS_ENABLED;
  if (raw === undefined) {
    return process.env.NODE_ENV === "production";
  }
  return raw === "true" || raw === "1";
}

async function getAdminEmails(): Promise<string[]> {
  const rows = await db
    .select({ email: user.email })
    .from(user)
    .where(eq(user.role, "admin"));
  return rows.map((r) => r.email).filter((e) => !!e);
}

async function broadcast(
  kind: AdminNotificationKind,
  data: Parameters<typeof adminNotificationTemplate>[0]["data"],
): Promise<void> {
  if (!isEnabled()) return;
  const admins = await getAdminEmails();
  if (admins.length === 0) {
    console.warn(
      `[admin-notifications] No admin users found; skipping ${kind} notification for ${data.email}.`,
    );
    return;
  }
  const rendered = adminNotificationTemplate({ kind, data });
  for (const adminEmail of admins) {
    try {
      await sendEmail({
        to: adminEmail,
        subject: rendered.subject,
        text: rendered.text,
        html: rendered.html,
        attachments: [ADMIN_NOTIFICATION_LOGO_ATTACHMENT],
      });
    } catch (err) {
      console.error(
        `[admin-notifications] Failed to send ${kind} to ${adminEmail}:`,
        err,
      );
    }
  }
}

export function notifyAdminNewSignUp(input: {
  email: string;
  name?: string | null;
  at?: Date;
}): void {
  void broadcast("new-signup", {
    email: input.email,
    name: input.name,
    at: input.at ?? new Date(),
  });
}

export function notifyAdminBetaRequest(input: {
  email: string;
  name?: string | null;
  at?: Date;
}): void {
  void broadcast("beta-request", {
    email: input.email,
    name: input.name,
    at: input.at ?? new Date(),
  });
}

export function notifyAdminRoasterSuggestion(input: {
  email: string;
  name?: string | null;
  roasterName: string;
  country?: string | null;
  website?: string | null;
  at?: Date;
}): void {
  void broadcast("roaster-suggestion", {
    email: input.email,
    name: input.name,
    roasterName: input.roasterName,
    country: input.country,
    website: input.website,
    at: input.at ?? new Date(),
  });
}

export function notifyAdminPageFeedback(input: {
  email: string;
  name?: string | null;
  kind: string;
  entityName?: string | null;
  entityUrlPath?: string | null;
  fields?: string | null;
  message?: string | null;
  at?: Date;
}): void {
  void broadcast("page-feedback", {
    email: input.email,
    name: input.name,
    kind: input.kind,
    entityName: input.entityName,
    entityUrlPath: input.entityUrlPath,
    fields: input.fields,
    message: input.message,
    at: input.at ?? new Date(),
  });
}

export function notifyAdminNewsletterChange(input: {
  email: string;
  name?: string | null;
  action: "subscribed" | "unsubscribed";
  at?: Date;
}): void {
  void broadcast(
    input.action === "subscribed" ? "newsletter-subscribed" : "newsletter-unsubscribed",
    {
      email: input.email,
      name: input.name,
      at: input.at ?? new Date(),
    },
  );
}

export function notifyUserBetaApproved(input: {
  email: string;
  name?: string | null;
}): void {
  if (!isEnabled()) return;
  const rendered = betaApprovedUserTemplate({ name: input.name });
  void sendEmail({
    to: input.email,
    subject: rendered.subject,
    text: rendered.text,
    html: rendered.html,
    attachments: [USER_EMAIL_LOGO_ATTACHMENT],
  }).catch((err) => {
    console.error(
      `[admin-notifications] Failed to send beta-approved email to ${input.email}:`,
      err,
    );
  });
}
