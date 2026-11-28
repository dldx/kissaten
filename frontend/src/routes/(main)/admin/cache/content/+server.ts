import type { RequestHandler } from "./$types";
import { env } from "$env/dynamic/private";
import { resolveInternalApiBase } from "$lib/server/internalApi";

/**
 * Admin-only proxy for cached raw pages.
 *
 * The FastAPI cache endpoints require the server-side
 * `X-Kissaten-Admin-Token` header. That token must never reach the browser, so
 * this same-origin endpoint authenticates the admin session, re-checks the
 * request parameters, and streams the upstream response back with hardening
 * headers (and only the body/headers we explicitly allow).
 */

const SESSION_RE = /^\d{8}$/;
const FILENAME_RE = /^[a-z0-9_.-]+\.tar\.gz$/;
const KINDS = ["html", "screenshot", "metadata", "raw"] as const;
type CacheKind = (typeof KINDS)[number];

const HTML_CSP =
  "sandbox; default-src 'none'; script-src 'none'; img-src https: http: data:; style-src https: http: 'unsafe-inline'; font-src https: http: data:; base-uri https: http:; form-action 'none'";

function isCacheKind(value: string): value is CacheKind {
  return (KINDS as readonly string[]).includes(value);
}

function fallbackContentType(kind: CacheKind): string {
  switch (kind) {
    case "html":
      return "text/html; charset=utf-8";
    case "screenshot":
      return "image/png";
    case "metadata":
      return "application/json; charset=utf-8";
    case "raw":
      return "application/gzip";
  }
}

export const GET: RequestHandler = async ({ locals, url, fetch }) => {
  if (!locals.user) {
    return new Response("Authentication required.", {
      status: 401,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }
  if (locals.user.role !== "admin") {
    return new Response("Admin access required.", {
      status: 403,
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  }

  const roaster = url.searchParams.get("roaster") ?? "";
  const bean = url.searchParams.get("bean") ?? "";
  const session = url.searchParams.get("session") ?? "";
  const filename = url.searchParams.get("filename") ?? "";
  const kind = url.searchParams.get("kind") ?? "";

  const invalid = (message: string) =>
    new Response(message, {
      status: 400,
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "cache-control": "private, no-store",
      },
    });

  if (!roaster || !bean) return invalid("Missing roaster or bean.");
  if (!SESSION_RE.test(session)) return invalid("Invalid session date.");
  if (!FILENAME_RE.test(filename)) return invalid("Invalid snapshot filename.");
  if (!isCacheKind(kind)) return invalid("Invalid content kind.");

  const token = env.KISSATEN_ADMIN_API_TOKEN;
  if (!token) {
    return new Response(
      "Cache viewer is not configured: KISSATEN_ADMIN_API_TOKEN is missing on the frontend server.",
      {
        status: 503,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "private, no-store",
        },
      },
    );
  }

  const base = resolveInternalApiBase(env);
  const params = new URLSearchParams({ session, filename, kind });
  const upstreamUrl = `${base}/v1/admin/cache/beans/${encodeURIComponent(
    roaster,
  )}/${encodeURIComponent(bean)}/content?${params.toString()}`;

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      headers: {
        accept: "*/*",
        "X-Kissaten-Admin-Token": token,
      },
    });
  } catch {
    return new Response("Could not reach the backend cache service.", {
      status: 502,
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "cache-control": "private, no-store",
      },
    });
  }

  if (!upstream.ok) {
    const detail = await upstream.text().catch(() => "");
    return new Response(
      detail || `Upstream cache request failed (HTTP ${upstream.status}).`,
      {
        status: upstream.status,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "private, no-store",
          "x-content-type-options": "nosniff",
          "referrer-policy": "no-referrer",
        },
      },
    );
  }

  // Build a fresh header set: never forward upstream Set-Cookie / CORS or
  // other hop-by-hop headers.
  const headers = new Headers();
  headers.set(
    "Content-Type",
    upstream.headers.get("content-type") ?? fallbackContentType(kind),
  );
  headers.set("Cache-Control", "private, no-store");
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "no-referrer");

  const disposition = upstream.headers.get("content-disposition");
  if (disposition) {
    headers.set("Content-Disposition", disposition);
  } else if (kind === "raw") {
    headers.set("Content-Disposition", `attachment; filename="${filename}"`);
  }

  if (kind === "html") {
    headers.set("Content-Security-Policy", HTML_CSP);
  }

  return new Response(upstream.body, {
    status: 200,
    headers,
  });
};
