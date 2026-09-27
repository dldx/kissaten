import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cacheDep,
  isHydrating,
  markHydrated,
  selectMode,
  serializePayload,
} from "./apiCache";

// Keep the import hermetic: the module's `db` is only touched inside the async
// cache helpers, and `$app/navigation` is only imported dynamically at runtime.
vi.mock("$lib/db/localdb", () => ({ db: {} }));
vi.mock("$app/navigation", () => ({ invalidate: vi.fn() }));

describe("cacheDep", () => {
  it("namespaces the dependency by the full url", () => {
    expect(cacheDep("/api/v1/roasters")).toBe("app:cache:/api/v1/roasters");
    expect(cacheDep("/api/v1/origins")).toBe("app:cache:/api/v1/origins");
  });
});

describe("selectMode", () => {
  it("defaults to network-first while hydrating", () => {
    expect(selectMode(undefined, true)).toBe("network-first");
  });

  it("defaults to cache-first after hydration", () => {
    expect(selectMode(undefined, false)).toBe("cache-first");
  });

  it("honours an explicit mode regardless of the hydration gate", () => {
    expect(selectMode("cache-first", true)).toBe("cache-first");
    expect(selectMode("network-first", false)).toBe("network-first");
  });
});

describe("hydration gate", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts hydrating in a browser context and flips idempotently", async () => {
    vi.stubGlobal("window", {});
    const mod = await import("./apiCache");

    expect(mod.isHydrating()).toBe(true);
    expect(mod.selectMode(undefined, mod.isHydrating())).toBe("network-first");

    mod.markHydrated();
    expect(mod.isHydrating()).toBe(false);
    expect(mod.selectMode(undefined, mod.isHydrating())).toBe("cache-first");

    // Idempotent: a later navigation must not throw or change state.
    mod.markHydrated();
    expect(mod.isHydrating()).toBe(false);
  });

  it("is not hydrating without a window (SSR-like context)", async () => {
    const mod = await import("./apiCache");
    expect(mod.isHydrating()).toBe(false);
    expect(markHydrated).toBeInstanceOf(Function);
    expect(isHydrating).toBeInstanceOf(Function);
  });
});

describe("serializePayload", () => {
  it("treats deep-equal payloads as unchanged", () => {
    expect(serializePayload({ a: 1, b: [2, 3] })).toBe(
      serializePayload({ a: 1, b: [2, 3] }),
    );
  });

  it("detects changed payloads", () => {
    expect(serializePayload({ a: 1 })).not.toBe(serializePayload({ a: 2 }));
  });
});
