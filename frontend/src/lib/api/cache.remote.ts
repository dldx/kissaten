import { getRequestEvent, query } from "$app/server";
import { error } from "@sveltejs/kit";
import { z } from "zod";
import { env } from "$env/dynamic/private";
import { resolveInternalApiBase } from "$lib/server/internalApi";

/**
 * Admin-only access to the raw cached pages that scrapers store for each bean.
 *
 * The browser never sees `KISSATEN_ADMIN_API_TOKEN`: this module runs
 * server-side (like every `*.remote.ts`), requireAdmin() gates the call on the
 * signed-in user, and only then does the server talk to the FastAPI admin
 * endpoints with the shared token.
 */

/** The bean summary returned alongside its cached snapshots. */
export interface CachedBeanInfo {
  name: string;
  roaster: string;
  url: string;
  bean_url_path: string;
  scraped_at: string | null;
}

/** One cached scrape session/archive for a bean. */
export interface CachedSnapshot {
  session_date: string;
  filename: string;
  source: "local" | "r2";
  /** Byte size of the archive, or null when the source does not report one. */
  size: number | null;
  last_modified: string | null;
  has_screenshot: boolean | null;
}

/** Payload of GET /v1/admin/cache/beans/{roaster}/{bean}. */
export interface CachedSnapshotsData {
  bean: CachedBeanInfo;
  roaster_dirs: string[];
  snapshots: CachedSnapshot[];
  storage: { local: boolean; r2: boolean };
  warnings: string[];
}

/** Envelope returned by the FastAPI admin cache endpoint. */
export interface CachedSnapshotsResponse {
  success: boolean;
  data?: CachedSnapshotsData;
  message?: string;
  detail?: string;
}

/** Mirror of admin.remote.ts's guard: throws 401/403 for non-admins. */
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

const listCachedSnapshotsSchema = z.object({
  roasterSlug: z.string().min(1),
  beanSlug: z.string().min(1),
});

/**
 * List the cached page snapshots for one bean. Returns the `data` object from
 * the upstream envelope (not the `{ success, data }` wrapper).
 */
export const listCachedSnapshots = query(
  listCachedSnapshotsSchema,
  async ({ roasterSlug, beanSlug }): Promise<CachedSnapshotsData> => {
    requireAdmin();

    const token = env.KISSATEN_ADMIN_API_TOKEN;
    if (!token) {
      throw error(
        503,
        "Cache viewer is not configured: KISSATEN_ADMIN_API_TOKEN is missing on the frontend server.",
      );
    }

    const base = resolveInternalApiBase(env);
    const upstreamUrl = `${base}/v1/admin/cache/beans/${encodeURIComponent(
      roasterSlug,
    )}/${encodeURIComponent(beanSlug)}`;

    let res: Response;
    try {
      res = await getRequestEvent().fetch(upstreamUrl, {
        headers: {
          accept: "application/json",
          "X-Kissaten-Admin-Token": token,
        },
      });
    } catch {
      throw error(502, "Could not reach the backend cache service.");
    }

    if (!res.ok) {
      let detail = "";
      try {
        const body = (await res.json()) as {
          detail?: unknown;
          message?: unknown;
        };
        if (typeof body?.detail === "string") detail = body.detail;
        else if (typeof body?.message === "string") detail = body.message;
      } catch {
        // Upstream didn't return JSON; fall back to the status text.
      }
      throw error(
        res.status,
        detail || `Cache lookup failed (HTTP ${res.status}).`,
      );
    }

    const payload = (await res.json()) as CachedSnapshotsResponse;
    if (!payload?.success || !payload.data) {
      throw error(
        502,
        payload?.message || "Cache lookup returned an invalid response.",
      );
    }

    return payload.data;
  },
);
