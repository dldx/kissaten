/**
 * Server-side API URL routing.
 *
 * The public origin (https://kissaten.app) sits behind Cloudflare, which
 * challenges the frontend server's own requests back through the edge
 * (`cf-mitigated: challenge` → 403). Server-side rendering therefore cannot
 * fetch its own API via the public hostname. The reverse proxy (nginx in
 * production, Vite in dev) strips the `/api` prefix and forwards `/v1/*` to the
 * FastAPI service on :8000, so SSR talks to that service directly instead.
 *
 * `/api/v1/beans/x` → `<internalBase>/v1/beans/x`
 */

const DEFAULT_BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = 8000;

/**
 * Resolve the internal (direct-to-backend) URL for a server-side API request.
 * Returns `null` for anything that isn't an `/api/v1/*` call, so unrelated
 * server-side fetches (e.g. better-auth under `/api/auth/*`) are left
 * untouched.
 */
export function resolveInternalApiUrl(
  requestUrl: string | URL,
  internalBase: string,
): URL | null {
  const url = typeof requestUrl === "string" ? new URL(requestUrl) : requestUrl;
  if (!url.pathname.startsWith("/api/v1/")) return null;
  const path = url.pathname.replace(/^\/api/, "");
  return new URL(internalBase.replace(/\/+$/, "") + path + url.search);
}

/**
 * The backend base URL for SSR fetches. Prefers `INTERNAL_API_BASE`, then the
 * dev-only `VITE_BACKEND_URL`, then localhost. `0.0.0.0`/empty collapse to
 * `127.0.0.1` (0.0.0.0 is a bind address, not a connect address).
 */
export function resolveInternalApiBase(env: {
  INTERNAL_API_BASE?: string;
  VITE_BACKEND_URL?: string;
}): string {
  if (env.INTERNAL_API_BASE) return env.INTERNAL_API_BASE.replace(/\/+$/, "");
  const host = env.VITE_BACKEND_URL;
  const resolved = !host || host === "0.0.0.0" ? DEFAULT_BACKEND_HOST : host;
  return `http://${resolved}:${BACKEND_PORT}`;
}
