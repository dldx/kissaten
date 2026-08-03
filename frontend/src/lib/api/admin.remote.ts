import { form, getRequestEvent, query } from "$app/server";
import { z } from "zod";
import { and, asc, count, desc, eq } from "drizzle-orm";
import { error } from "@sveltejs/kit";
import { db } from "$lib/server/database";
import {
  roasterSuggestions,
  roasterSuggestionVotes,
  user,
} from "$lib/server/database/schema";
import {
  notifyUserBetaApproved,
  notifyAdminSuggestionImplemented,
  notifyVotersSuggestionImplemented,
} from "$lib/server/admin-notifications";

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

export interface AdminStats {
  totalUsers: number;
  pendingBetaInterest: number;
  newsletterSubscribers: number;
  pendingRoasterSuggestions: number;
  activeBetaTesters: number;
}

export const getAdminStats = query(async (): Promise<AdminStats> => {
  requireAdmin();

  const [totals, pendingBeta, newsletters, pendingRoster, activeBeta] =
    await Promise.all([
      db.select({ n: count() }).from(user),
      db
        .select({ n: count() })
        .from(user)
        .where(and(eq(user.betaInterest, true), eq(user.isBetaAllowed, false))),
      db
        .select({ n: count() })
        .from(user)
        .where(eq(user.newsletterSubscribed, true)),
      db
        .select({ n: count() })
        .from(roasterSuggestions)
        .where(eq(roasterSuggestions.status, "pending")),
      db
        .select({ n: count() })
        .from(user)
        .where(and(eq(user.isBetaAllowed, true), eq(user.betaEnabled, true))),
    ]);

  return {
    totalUsers: totals[0]?.n ?? 0,
    pendingBetaInterest: pendingBeta[0]?.n ?? 0,
    newsletterSubscribers: newsletters[0]?.n ?? 0,
    pendingRoasterSuggestions: pendingRoster[0]?.n ?? 0,
    activeBetaTesters: activeBeta[0]?.n ?? 0,
  };
});

export interface BetaInterestRow {
  id: string;
  name: string;
  email: string;
  updatedAt: Date;
  createdAt: Date;
}

export const listBetaInterest = query(async (): Promise<BetaInterestRow[]> => {
  requireAdmin();
  return db
    .select({
      id: user.id,
      name: user.name,
      email: user.email,
      updatedAt: user.updatedAt,
      createdAt: user.createdAt,
    })
    .from(user)
    .where(and(eq(user.betaInterest, true), eq(user.isBetaAllowed, false)))
    .orderBy(desc(user.updatedAt));
});

export interface AdminUserRow {
  id: string;
  name: string;
  email: string;
  role: string;
  newsletterSubscribed: boolean;
  isBetaAllowed: boolean;
  betaEnabled: boolean;
  betaInterest: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export const listAllUsers = query(async (): Promise<AdminUserRow[]> => {
  requireAdmin();
  return db
    .select({
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
      newsletterSubscribed: user.newsletterSubscribed,
      isBetaAllowed: user.isBetaAllowed,
      betaEnabled: user.betaEnabled,
      betaInterest: user.betaInterest,
      createdAt: user.createdAt,
      updatedAt: user.updatedAt,
    })
    .from(user)
    .orderBy(asc(user.email));
});

export type RoasterSuggestionStatusFilter =
  | "pending"
  | "approved"
  | "rejected"
  | "implemented";

export interface AdminRoasterSuggestion {
  id: string;
  name: string;
  country: string | null;
  website: string | null;
  status: RoasterSuggestionStatusFilter;
  upvoteCount: number;
  implementedRoasterSlug: string | null;
  suggesterEmail: string | null;
  suggesterName: string | null;
  createdAt: Date;
  updatedAt: Date;
}

export const listAllRoasterSuggestions = query(
  async (): Promise<AdminRoasterSuggestion[]> => {
    requireAdmin();
    const rows = await db
      .select({
        id: roasterSuggestions.id,
        name: roasterSuggestions.name,
        country: roasterSuggestions.country,
        website: roasterSuggestions.website,
        status: roasterSuggestions.status,
        upvoteCount: roasterSuggestions.upvoteCount,
        implementedRoasterSlug: roasterSuggestions.implementedRoasterSlug,
        suggesterEmail: user.email,
        suggesterName: user.name,
        createdAt: roasterSuggestions.createdAt,
        updatedAt: roasterSuggestions.updatedAt,
      })
      .from(roasterSuggestions)
      .leftJoin(user, eq(user.id, roasterSuggestions.userId))
      .orderBy(
        desc(roasterSuggestions.upvoteCount),
        desc(roasterSuggestions.createdAt),
      );

    return rows.map((r) => ({
      ...r,
      status: r.status as RoasterSuggestionStatusFilter,
    }));
  },
);

const userIdSchema = z.object({ userId: z.string().min(1) });

export const approveBetaTester = form(userIdSchema, async ({ userId }) => {
  requireAdmin();

  const [target] = await db
    .select({ email: user.email, name: user.name })
    .from(user)
    .where(eq(user.id, userId))
    .limit(1);

  await db
    .update(user)
    .set({
      isBetaAllowed: true,
      betaInterest: false,
      updatedAt: new Date(),
    })
    .where(eq(user.id, userId));

  if (target?.email) {
    notifyUserBetaApproved({ email: target.email, name: target.name });
  }

  return { success: true, userId } as const;
});

export const declineBetaTester = form(userIdSchema, async ({ userId }) => {
  requireAdmin();

  await db
    .update(user)
    .set({
      betaInterest: false,
      updatedAt: new Date(),
    })
    .where(eq(user.id, userId));

  return { success: true, userId } as const;
});

const suggestionIdSchema = z.object({
  suggestionId: z.string().min(1),
});

export const approveSuggestion = form(
  suggestionIdSchema,
  async ({ suggestionId }) => {
    requireAdmin();

    await db
      .update(roasterSuggestions)
      .set({ status: "approved", updatedAt: new Date() })
      .where(eq(roasterSuggestions.id, suggestionId));

    return { success: true, suggestionId } as const;
  },
);

export const rejectSuggestion = form(
  suggestionIdSchema,
  async ({ suggestionId }) => {
    requireAdmin();

    await db
      .update(roasterSuggestions)
      .set({ status: "rejected", updatedAt: new Date() })
      .where(eq(roasterSuggestions.id, suggestionId));

    return { success: true, suggestionId } as const;
  },
);

const markImplementedSchema = z.object({
  suggestionId: z.string().min(1),
  // Must match the canonical roaster slug charset (see slugifyRoaster in
  // ../api.ts and slugify_roaster in src/kissaten/api/utils.py).
  roasterSlug: z
    .string()
    .min(1)
    .max(100)
    .regex(/^[a-z0-9&_\-éūëöáíóúñûē']+$/, "Invalid roaster slug"),
});

export const markSuggestionImplemented = form(
  markImplementedSchema,
  async ({ suggestionId, roasterSlug }) => {
    requireAdmin();

    const [suggestion] = await db
      .select({
        id: roasterSuggestions.id,
        name: roasterSuggestions.name,
        status: roasterSuggestions.status,
        submittedByEmail: user.email,
      })
      .from(roasterSuggestions)
      .leftJoin(user, eq(user.id, roasterSuggestions.userId))
      .where(eq(roasterSuggestions.id, suggestionId))
      .limit(1);

    if (!suggestion) {
      throw error(404, "Suggestion not found.");
    }

    await db
      .update(roasterSuggestions)
      .set({
        status: "implemented",
        implementedRoasterSlug: roasterSlug,
        updatedAt: new Date(),
      })
      .where(eq(roasterSuggestions.id, suggestionId));

    // Idempotency: if the suggestion was already marked implemented, don't
    // re-notify admins or opted-in voters (otherwise every re-save re-sends).
    if (suggestion.status === "implemented") {
      return { success: true, suggestionId, roasterSlug } as const;
    }

    const votingUsers = await db
      .select({ email: user.email, name: user.name })
      .from(roasterSuggestionVotes)
      .innerJoin(user, eq(user.id, roasterSuggestionVotes.userId))
      .where(
        and(
          eq(roasterSuggestionVotes.suggestionId, suggestionId),
          eq(roasterSuggestionVotes.notifyOnImplementation, true),
        ),
      );

    notifyAdminSuggestionImplemented({
      email: suggestion.submittedByEmail ?? "",
      roasterName: suggestion.name,
      roasterSlug,
    });
    const roasterUrl = `https://kissaten.app/roasters/${roasterSlug}`;
    const recipients = votingUsers
      .filter((r) => !!r.email)
      .map((r) => ({ email: r.email as string, name: r.name }));
    notifyVotersSuggestionImplemented({
      recipients,
      roasterName: suggestion.name,
      roasterUrl,
    });

    return { success: true, suggestionId, roasterSlug } as const;
  },
);
