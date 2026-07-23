import { command, form, getRequestEvent, query } from "$app/server";
import { z } from "zod";
import { desc, eq, and, sql } from "drizzle-orm";
import { nanoid } from "nanoid";
import { db } from "$lib/server/database";
import {
  roasterSuggestions,
  roasterSuggestionVotes,
} from "$lib/server/database/schema";
import { roasterSuggestionSchema } from "$lib/schema/roasterSuggestion";

function requireAuth() {
  const { locals } = getRequestEvent();
  if (!locals.user) {
    throw new Error("Authentication required. Please sign in to continue.");
  }
  return locals.user;
}

export type RoasterSuggestionStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "implemented";

export interface RoasterSuggestion {
  id: string;
  name: string;
  nameNormalized: string;
  country: string | null;
  website: string | null;
  userId: string;
  status: RoasterSuggestionStatus;
  upvoteCount: number;
  implementedRoasterSlug: string | null;
  createdAt: Date;
  updatedAt: Date;
  hasUpvoted: boolean;
  // The voter's notification consent for this suggestion. Only set when
  // `hasUpvoted` is true; null otherwise. Lets the client render a
  // post-vote "Notify me" toggle without an extra round-trip.
  notifyOnImplementation: boolean | null;
}

export type SubmitRoasterSuggestionResult =
  | { status: "created"; suggestion: RoasterSuggestion }
  | { status: "exists"; suggestion: RoasterSuggestion };

export type UpvoteRoasterSuggestionResult =
  | {
      status: "ok";
      suggestionId: string;
      upvoteCount: number;
      notifyOnImplementation: boolean;
    }
  | {
      status: "already_voted";
      suggestionId: string;
      upvoteCount: number;
      notifyOnImplementation: boolean;
    };

function normalizeName(name: string): string {
  return name.trim().toLowerCase();
}

/**
 * Returns pending suggestions, ordered by upvote count (desc) then recency
 * (desc). `hasUpvoted` is filled for the current user; for logged-out
 * visitors it's always false.
 *
 * Implemented roasters are NOT returned here — those live in the DuckDB
 * backend, surfaced to the page via `data.roasters`. When an admin later
 * marks a suggestion as `implemented`, it disappears from this list (the
 * real roaster card in the grid replaces it).
 */
export const getRoasterSuggestions = query(async () => {
  const { locals } = getRequestEvent();
  const currentUserId = locals.user?.id ?? null;

  const rows = await db
    .select({
      id: roasterSuggestions.id,
      name: roasterSuggestions.name,
      nameNormalized: roasterSuggestions.nameNormalized,
      country: roasterSuggestions.country,
      website: roasterSuggestions.website,
      userId: roasterSuggestions.userId,
      status: roasterSuggestions.status,
      upvoteCount: roasterSuggestions.upvoteCount,
      implementedRoasterSlug: roasterSuggestions.implementedRoasterSlug,
      createdAt: roasterSuggestions.createdAt,
      updatedAt: roasterSuggestions.updatedAt,
    })
    .from(roasterSuggestions)
    .where(eq(roasterSuggestions.status, "pending"))
    .orderBy(
      desc(roasterSuggestions.upvoteCount),
      desc(roasterSuggestions.createdAt),
    );

  if (rows.length === 0) return [];

  const voteRows = currentUserId
    ? await db
        .select({
          suggestionId: roasterSuggestionVotes.suggestionId,
          notifyOnImplementation: roasterSuggestionVotes.notifyOnImplementation,
        })
        .from(roasterSuggestionVotes)
        .where(eq(roasterSuggestionVotes.userId, currentUserId))
    : [];
  const voteMap = new Map(
    voteRows.map((r) => [r.suggestionId, r.notifyOnImplementation]),
  );

  return rows.map(
    (row): RoasterSuggestion => ({
      ...row,
      status: row.status as RoasterSuggestionStatus,
      hasUpvoted: voteMap.has(row.id),
      notifyOnImplementation: voteMap.get(row.id) ?? null,
    }),
  );
});

/**
 * Submit a roaster suggestion. Deduplicates against existing suggestions by
 * normalized name. If a duplicate is found, returns `{ status: 'exists' }`
 * so the client can prompt the user to upvote instead.
 *
 * NOTE: dedup against *implemented* roasters is performed client-side using
 * `data.roasters` (those live in the DuckDB backend, not libsql). The server
 * cannot authoritatively dedup against them.
 */
export const submitRoasterSuggestion = form(
  roasterSuggestionSchema,
  async (data): Promise<SubmitRoasterSuggestionResult> => {
    const currentUser = requireAuth();
    const nameNormalized = normalizeName(data.name);

    // Check for an existing suggestion with the same normalized name.
    const [existing] = await db
      .select()
      .from(roasterSuggestions)
      .where(eq(roasterSuggestions.nameNormalized, nameNormalized))
      .limit(1);

    if (existing) {
      const voteRow = await db
        .select({
          id: roasterSuggestionVotes.id,
          notifyOnImplementation: roasterSuggestionVotes.notifyOnImplementation,
        })
        .from(roasterSuggestionVotes)
        .where(
          and(
            eq(roasterSuggestionVotes.suggestionId, existing.id),
            eq(roasterSuggestionVotes.userId, currentUser.id),
          ),
        )
        .get();
      return {
        status: "exists",
        suggestion: {
          ...existing,
          status: existing.status as RoasterSuggestionStatus,
          hasUpvoted: Boolean(voteRow),
          notifyOnImplementation: voteRow?.notifyOnImplementation ?? null,
        },
      };
    }

    const id = `sug_${nanoid()}`;
    const voteId = `vote_${nanoid()}`;
    const now = new Date();
    // The submitter automatically upvotes their own suggestion (counts as 1).
    // Their per-vote notification consent is persisted from the form field.
    await db.insert(roasterSuggestions).values({
      id,
      name: data.name,
      nameNormalized,
      country: data.country ?? null,
      website: data.website ?? null,
      userId: currentUser.id,
      status: "pending",
      upvoteCount: 1,
      implementedRoasterSlug: null,
      createdAt: now,
      updatedAt: now,
    });
    await db.insert(roasterSuggestionVotes).values({
      id: voteId,
      suggestionId: id,
      userId: currentUser.id,
      notifyOnImplementation: data.notifyOnImplementation,
      createdAt: now,
    });

    return {
      status: "created",
      suggestion: {
        id,
        name: data.name,
        nameNormalized,
        country: data.country ?? null,
        website: data.website ?? null,
        userId: currentUser.id,
        status: "pending",
        upvoteCount: 1,
        implementedRoasterSlug: null,
        createdAt: now,
        updatedAt: now,
        hasUpvoted: true,
        notifyOnImplementation: data.notifyOnImplementation,
      },
    };
  },
);

export const upvoteRoasterSuggestion = command(
  z.object({
    suggestionId: z.string().min(1),
    // GDPR Art. 7: consent must not be pre-ticked (Planet49, C-673/17).
    // Default to false; the voter must actively opt in.
    notifyOnImplementation: z.boolean().default(false),
  }),
  async ({ suggestionId, notifyOnImplementation }): Promise<UpvoteRoasterSuggestionResult> => {
    const currentUser = requireAuth();

    // Idempotent insert: if the (suggestionId, userId) pair already exists,
    // the unique constraint fires and we treat it as already_voted (one
    // permanent upvote per user — no toggle).
    try {
      await db.insert(roasterSuggestionVotes).values({
        id: `vote_${nanoid()}`,
        suggestionId,
        userId: currentUser.id,
        notifyOnImplementation,
        createdAt: new Date(),
      });
    } catch (err) {
      // SQLite unique-constraint violation. Drizzle surfaces it as a
      // generic Error — match on the constraint name in the message.
      const msg = err instanceof Error ? err.message : String(err);
      if (
        msg.includes("roaster_suggestion_votes_uniq") ||
        msg.toLowerCase().includes("unique")
      ) {
        const [row] = await db
          .select({
            upvoteCount: roasterSuggestions.upvoteCount,
            notifyOnImplementation: roasterSuggestionVotes.notifyOnImplementation,
          })
          .from(roasterSuggestions)
          .innerJoin(
            roasterSuggestionVotes,
            and(
              eq(roasterSuggestionVotes.suggestionId, roasterSuggestions.id),
              eq(roasterSuggestionVotes.userId, currentUser.id),
            ),
          )
          .where(eq(roasterSuggestions.id, suggestionId))
          .limit(1);
        return {
          status: "already_voted",
          suggestionId,
          upvoteCount: row?.upvoteCount ?? 0,
          notifyOnImplementation: row?.notifyOnImplementation ?? false,
        };
      }
      throw err;
    }

    await db
      .update(roasterSuggestions)
      .set({
        upvoteCount: sql`${roasterSuggestions.upvoteCount} + 1`,
        updatedAt: new Date(),
      })
      .where(eq(roasterSuggestions.id, suggestionId));

    const [row] = await db
      .select({ upvoteCount: roasterSuggestions.upvoteCount })
      .from(roasterSuggestions)
      .where(eq(roasterSuggestions.id, suggestionId))
      .limit(1);

    return {
      status: "ok",
      suggestionId,
      upvoteCount: row?.upvoteCount ?? 0,
      notifyOnImplementation,
    };
  },
);

/**
 * Update the notification consent flag on the current user's vote for a
 * given suggestion. Lets the voter toggle "Notify me when added" after
 * voting. GDPR Art. 7: consent must be as easy to withdraw as to give.
 */
export const updateVoteNotify = command(
  z.object({
    suggestionId: z.string().min(1),
    notifyOnImplementation: z.boolean(),
  }),
  async ({ suggestionId, notifyOnImplementation }) => {
    const currentUser = requireAuth();
    await db
      .update(roasterSuggestionVotes)
      .set({ notifyOnImplementation })
      .where(
        and(
          eq(roasterSuggestionVotes.suggestionId, suggestionId),
          eq(roasterSuggestionVotes.userId, currentUser.id),
        ),
      );
    return { suggestionId, notifyOnImplementation };
  },
);
