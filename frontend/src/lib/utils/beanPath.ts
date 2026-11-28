/**
 * Parse a Kissaten bean reference into the `(roaster, bean)` slugs used by the
 * cached-page endpoints.
 *
 * Accepts the shapes admins encounter in the admin queues:
 *   - `/roaster/bean` (bean_url_path)
 *   - `/roasters/roaster/bean` (public route)
 *   - `roaster/bean`
 *   - `https://kissaten.app/roasters/roaster/bean`
 *
 * Returns `null` for anything that doesn't contain exactly two path segments.
 */
export interface ParsedBeanPath {
  roasterSlug: string;
  beanSlug: string;
  /** Normalized `/roaster/bean` path for display. */
  path: string;
}

const SLUG_SEGMENT = /^[^\s/?#]+$/;

function safeDecode(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

export function parseBeanPath(
  input: string | null | undefined,
): ParsedBeanPath | null {
  if (!input) return null;

  let raw = input.trim();
  if (!raw) return null;

  if (/^https?:\/\//i.test(raw)) {
    try {
      raw = new URL(raw).pathname;
    } catch {
      return null;
    }
  } else {
    raw = raw.split(/[?#]/, 1)[0] ?? "";
  }

  let segments = raw.split("/").filter(Boolean);
  // `/roasters/<roaster>/<bean>` is the public route; the API uses the
  // un-prefixed `<roaster>/<bean>` form (`bean_url_path`).
  if (segments[0] === "roasters") segments = segments.slice(1);
  if (segments.length !== 2) return null;

  const [roasterSlug, beanSlug] = segments.map(safeDecode);
  if (!SLUG_SEGMENT.test(roasterSlug) || !SLUG_SEGMENT.test(beanSlug)) {
    return null;
  }

  return {
    roasterSlug,
    beanSlug,
    path: `/${roasterSlug}/${beanSlug}`,
  };
}
