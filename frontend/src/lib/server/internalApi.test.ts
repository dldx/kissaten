import { describe, expect, it } from "vitest";
import { resolveInternalApiBase, resolveInternalApiUrl } from "./internalApi";

describe("resolveInternalApiUrl", () => {
  const base = "http://127.0.0.1:8000";

  it("rewrites public /api/v1 paths to the backend", () => {
    expect(
      resolveInternalApiUrl(
        "https://kissaten.app/api/v1/roasters",
        base,
      )?.toString(),
    ).toBe("http://127.0.0.1:8000/v1/roasters");
  });

  it("preserves the query string", () => {
    expect(
      resolveInternalApiUrl(
        "https://kissaten.app/api/v1/beans/alchemy_coffee/colombia?convert_to_currency=GBP",
        base,
      )?.toString(),
    ).toBe(
      "http://127.0.0.1:8000/v1/beans/alchemy_coffee/colombia?convert_to_currency=GBP",
    );
  });

  it("works for a dev-server origin too", () => {
    expect(
      resolveInternalApiUrl(
        "http://localhost:5173/api/v1/origins",
        base,
      )?.toString(),
    ).toBe("http://127.0.0.1:8000/v1/origins");
  });

  it("accepts a URL instance", () => {
    expect(
      resolveInternalApiUrl(
        new URL("http://localhost:5173/api/v1/search?q=x"),
        base,
      )?.toString(),
    ).toBe("http://127.0.0.1:8000/v1/search?q=x");
  });

  it("leaves non-api/v1 requests untouched", () => {
    expect(
      resolveInternalApiUrl("https://kissaten.app/api/auth/session", base),
    ).toBeNull();
    expect(
      resolveInternalApiUrl("https://kissaten.app/static/data/x.png", base),
    ).toBeNull();
    expect(
      resolveInternalApiUrl("https://kissaten.app/_app/chunk.js", base),
    ).toBeNull();
    expect(
      resolveInternalApiUrl("https://kissaten.app/api/v1", base),
    ).toBeNull();
  });
});

describe("resolveInternalApiBase", () => {
  it("prefers INTERNAL_API_BASE and strips trailing slashes", () => {
    expect(
      resolveInternalApiBase({ INTERNAL_API_BASE: "http://10.0.0.5:9000/" }),
    ).toBe("http://10.0.0.5:9000");
  });

  it("uses the VITE_BACKEND_URL host when set (dev)", () => {
    expect(
      resolveInternalApiBase({ VITE_BACKEND_URL: "192.168.1.163" }),
    ).toBe("http://192.168.1.163:8000");
  });

  it("collapses 0.0.0.0 and empty to 127.0.0.1", () => {
    expect(resolveInternalApiBase({})).toBe("http://127.0.0.1:8000");
    expect(resolveInternalApiBase({ VITE_BACKEND_URL: "0.0.0.0" })).toBe(
      "http://127.0.0.1:8000",
    );
  });
});
