export type AdminNotificationKind =
  | "new-signup"
  | "beta-request"
  | "roaster-suggestion"
  | "page-feedback"
  | "newsletter-subscribed"
  | "newsletter-unsubscribed";

type AdminNotificationKindMeta = {
  subject: string;
  title: string;
  accent: string;
  emoji: string;
  summary: (input: AdminNotificationInput) => string;
  details: (input: AdminNotificationInput) => string;
  cta: string;
};

const meta: Record<AdminNotificationKind, AdminNotificationKindMeta> = {
  "new-signup": {
    subject: "New Kissaten user signed up",
    title: "New user signed up",
    accent: "#4caf50",
    emoji: "✨",
    summary: (i) => `${i.name ?? "A new user"} (${i.email}) just created an account.`,
    details: (i) => `Email: ${i.email}`,
    cta: "View in admin",
  },
  "beta-request": {
    subject: "Beta program request",
    title: "Beta program request",
    accent: "#8b5cf6",
    emoji: "🧪",
    summary: (i) => `${i.name ?? "A user"} (${i.email}) wants to join the beta program.`,
    details: (i) => `Email: ${i.email}`,
    cta: "Review beta queue",
  },
  "roaster-suggestion": {
    subject: "New roaster suggested",
    title: "New roaster suggested",
    accent: "#f2a03d",
    emoji: "☕",
    summary: (i) => `${i.name ?? "A user"} (${i.email}) suggested a new roaster: ${i.roasterName ?? "(unnamed)"}.`,
    details: (i) =>
      [
        i.roasterName ? `Roaster: ${i.roasterName}` : null,
        i.country ? `Country: ${i.country}` : null,
        i.website ? `Website: ${i.website}` : null,
        `Submitted by: ${i.email}`,
      ]
        .filter(Boolean)
        .join("\n"),
    cta: "Review suggestions",
  },
  "page-feedback": {
    subject: "Page feedback reported",
    title: "Page feedback reported",
    accent: "#ef4444",
    emoji: "🐛",
    summary: (i) =>
      `${i.name ?? "A user"} (${i.email}) reported a problem on ${i.entityName ?? i.roasterName ?? "a page"}.`,
    details: (i) =>
      [
        i.entityName ? `Page: ${i.entityName}` : null,
        i.kind ? `Kind: ${i.kind}` : null,
        i.entityUrlPath ? `URL: ${i.entityUrlPath}` : null,
        i.fields ? `Fields: ${i.fields}` : null,
        i.message ? `\nMessage:\n${i.message}` : null,
        `Submitted by: ${i.email}`,
      ]
        .filter(Boolean)
        .join("\n"),
    cta: "Review feedback",
  },
  "newsletter-subscribed": {
    subject: "Newsletter subscription",
    title: "Newsletter subscription",
    accent: "#f2a03d",
    emoji: "📬",
    summary: (i) => `${i.name ?? "A user"} (${i.email}) subscribed to the newsletter.`,
    details: (i) => `Email: ${i.email}`,
    cta: "View subscribers",
  },
  "newsletter-unsubscribed": {
    subject: "Newsletter unsubscription",
    title: "Newsletter unsubscription",
    accent: "#b5a89a",
    emoji: "📭",
    summary: (i) => `${i.name ?? "A user"} (${i.email}) unsubscribed from the newsletter.`,
    details: (i) => `Email: ${i.email}`,
    cta: "View subscribers",
  },
};

export type AdminNotificationInput = {
  email: string;
  name?: string | null;
  roasterName?: string | null;
  country?: string | null;
  website?: string | null;
  entityName?: string | null;
  entityUrlPath?: string | null;
  kind?: string | null;
  fields?: string | null;
  message?: string | null;
  at?: Date;
};

export type AdminNotificationRendered = {
  subject: string;
  text: string;
  html: string;
};

function formatAt(d?: Date): string {
  const date = d ?? new Date();
  return date.toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderText(input: {
  kind: AdminNotificationKind;
  data: AdminNotificationInput;
  dashboardUrl: string;
}): string {
  const m = meta[input.kind];
  const summary = m.summary(input.data);
  const details = m.details(input.data);
  const at = formatAt(input.data.at);
  return [
    `[Kissaten admin] ${m.title}`,
    "",
    summary,
    "",
    details,
    "",
    `When: ${at}`,
    `Open admin: ${input.dashboardUrl}`,
  ].join("\n");
}

function renderHtml(input: {
  kind: AdminNotificationKind;
  data: AdminNotificationInput;
  dashboardUrl: string;
}): string {
  const m = meta[input.kind];
  const data = input.data;
  const summary = m.summary(data);
  const details = m.details(data);
  const at = formatAt(data.at);

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #fdf8f3;">
  <table role="presentation" style="width: 100%; border-collapse: collapse;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);">
          <tr>
            <td style="padding: 40px 40px 30px; text-align: center; background: #def1e1; border-radius: 9.4px 9.4px 0 0;">
              <a href="https://kissaten.app">
                <img src="cid:logo@kissaten.app" alt="Kissaten logo" style="width: 100%; max-width: 300px; margin-bottom: 20px;">
              </a>
              <h1 style="margin: 0; color: #1a1410; font-size: 28px; font-weight: 700; letter-spacing: -0.5px; font-family: 'Knewave', sans-serif;">${m.emoji} ${escapeHtml(m.title)}</h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px; background-color: #ffffff;">
              <p style="margin: 0 0 16px; color: #3d3730; font-size: 16px; line-height: 1.6;">
                ${escapeHtml(summary)}
              </p>
              <div style="margin: 24px 0; padding: 16px; background-color: #f8f6f3; border-radius: 10.4px; border: 1px solid #e5e0d8;">
                <pre style="margin: 0; font-family: 'Courier New', monospace; font-size: 13px; color: #3d3730; line-height: 1.6; white-space: pre-wrap;">${escapeHtml(details)}</pre>
              </div>
              <p style="margin: 0 0 8px; color: #736b5e; font-size: 13px; line-height: 1.6;">
                <strong>When:</strong> ${escapeHtml(at)}
              </p>
              <table role="presentation" style="width: 100%; border-collapse: collapse; margin-top: 28px;">
                <tr>
                  <td align="center" style="padding: 10px 0;">
                    <a href="${escapeHtml(input.dashboardUrl)}" style="display: inline-block; padding: 14px 36px; background: #def1e1; color: #1a1410; text-decoration: none; border-radius: 10.4px; font-weight: 600; font-size: 16px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);">
                      ${escapeHtml(m.cta)} 🛠️
                    </a>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding: 28px 40px; background-color: #faf8f5; border-radius: 0 0 9.4px 9.4px; text-align: center; border-top: 1px solid #e5e0d8;">
              <p style="margin: 0 0 12px; color: #8c8376; font-size: 13px; line-height: 1.5;">
                You're receiving this because you're a Kissaten admin.
              </p>
              <p style="margin: 0; font-size: 13px;">
                <a href="https://kissaten.app" style="color: ${m.accent}; text-decoration: none; font-weight: 600;">kissaten.app</a>
                <span style="color: #b5a89a; margin: 0 8px;">•</span>
                <span style="color: #8c8376;">Internal admin notification</span>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
`;
}

export function adminNotificationTemplate(input: {
  kind: AdminNotificationKind;
  data: AdminNotificationInput;
  dashboardUrl?: string;
}): AdminNotificationRendered {
  const m = meta[input.kind];
  const dashboardUrl = input.dashboardUrl ?? "https://kissaten.app/admin";
  const at = formatAt(input.data.at);
  const subject = `${m.subject} — ${input.data.email} (${at})`;
  const text = renderText({ kind: input.kind, data: input.data, dashboardUrl });
  const html = renderHtml({ kind: input.kind, data: input.data, dashboardUrl });
  return { subject, text, html };
}

export const ADMIN_NOTIFICATION_LOGO_ATTACHMENT = {
  filename: "logo_full.png",
  path: "static/logo_full.png",
  cid: "logo@kissaten.app",
};

export type UserEmailRendered = {
  subject: string;
  text: string;
  html: string;
};

export function betaApprovedUserTemplate(input: {
  name?: string | null;
  profileUrl?: string;
}): UserEmailRendered {
  const profileUrl = input.profileUrl ?? "https://kissaten.app/profile";
  const greetingName = input.name?.trim() || "there";
  const subject = "You're in! Beta access approved for Kissaten";
  const text = [
    `Hi ${greetingName},`,
    "",
    "Great news — you've been approved for the Kissaten beta program! 🎉",
    "",
    "You can now opt in to beta features like private tasting notes and early access",
    "to new functionality. To turn them on, head to your profile and flip the beta",
    "switch.",
    "",
    `Enable beta features: ${profileUrl}`,
    "",
    "Thanks for being an early supporter — enjoy!",
    "",
    "— The Kissaten team",
  ].join("\n");

  const html = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #fdf8f3;">
  <table role="presentation" style="width: 100%; border-collapse: collapse;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);">
          <tr>
            <td style="padding: 40px 40px 30px; text-align: center; background: #def1e1; border-radius: 9.4px 9.4px 0 0;">
              <a href="https://kissaten.app">
                <img src="cid:logo@kissaten.app" alt="Kissaten logo" style="width: 100%; max-width: 300px; margin-bottom: 20px;">
              </a>
              <h1 style="margin: 0; color: #1a1410; font-size: 32px; font-weight: 700; letter-spacing: -0.5px; font-family: 'Knewave', sans-serif;">You're in! 🎉</h1>
            </td>
          </tr>
          <tr>
            <td style="padding: 40px; background-color: #ffffff;">
              <p style="margin: 0 0 16px; color: #3d3730; font-size: 16px; line-height: 1.6;">
                Hi ${escapeHtml(greetingName)},
              </p>
              <p style="margin: 0 0 16px; color: #3d3730; font-size: 16px; line-height: 1.6;">
                Great news &mdash; you've been <strong>approved for the Kissaten beta program</strong>.
              </p>
              <p style="margin: 0 0 16px; color: #3d3730; font-size: 16px; line-height: 1.6;">
                You can now opt in to beta features like private tasting notes and early
                access to new functionality. To turn them on, head to your profile and
                flip the beta switch.
              </p>
              <table role="presentation" style="width: 100%; border-collapse: collapse; margin-top: 28px;">
                <tr>
                  <td align="center" style="padding: 10px 0;">
                    <a href="${escapeHtml(profileUrl)}" style="display: inline-block; padding: 14px 36px; background: #def1e1; color: #1a1410; text-decoration: none; border-radius: 10.4px; font-weight: 600; font-size: 16px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);">
                      Enable Beta Features ☕
                    </a>
                  </td>
                </tr>
              </table>
              <div style="margin: 32px 0 0; padding: 16px; background-color: #f0f9f4; border-radius: 10.4px; border: 1px solid #4caf50;">
                <p style="margin: 0; color: #2d5a3d; font-size: 13px; line-height: 1.6;">
                  <strong>💡 Heads up:</strong> Beta features are still in active development,
                  so you might see rough edges. Your feedback helps us shape them.
                </p>
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding: 28px 40px; background-color: #faf8f5; border-radius: 0 0 9.4px 9.4px; text-align: center; border-top: 1px solid #e5e0d8;">
              <p style="margin: 0 0 12px; color: #8c8376; font-size: 13px; line-height: 1.5;">
                Thanks for being an early supporter!
              </p>
              <p style="margin: 0; font-size: 13px;">
                <a href="https://kissaten.app" style="color: #f2a03d; text-decoration: none; font-weight: 600;">kissaten.app</a>
                <span style="color: #b5a89a; margin: 0 8px;">•</span>
                <span style="color: #8c8376;">Your coffee bean discovery platform</span>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
`;

  return { subject, text, html };
}

export const USER_EMAIL_LOGO_ATTACHMENT = {
  filename: "logo_full.png",
  path: "static/logo_full.png",
  cid: "logo@kissaten.app",
};
