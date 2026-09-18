import { afterEach, describe, expect, it, vi } from "vitest";
import {
  createModuleLoadReloader,
  isRouteModuleError,
} from "./routeModuleError";

function stubBrowser({
  online = true,
  storage = new Map<string, string>(),
  storageThrows = false,
} = {}) {
  const reload = vi.fn();
  vi.stubGlobal("location", { href: "http://localhost:3000/origins", reload });
  vi.stubGlobal("navigator", { onLine: online });
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => {
      if (storageThrows) throw new Error("storage disabled");
      return storage.get(key) ?? null;
    },
    setItem: (key: string, value: string) => {
      if (storageThrows) throw new Error("storage disabled");
      storage.set(key, value);
    },
  });
  return { reload, storage };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("isRouteModuleError", () => {
  it.each([
    "Failed to fetch dynamically imported module: http://localhost:3000/.svelte-kit/generated/client/nodes/41.js",
    "error loading dynamically imported module",
    "Importing a module script failed.",
    // bare network-level failures from `load_data`'s `__data.json` fetch
    "Failed to fetch",
    "NetworkError when attempting to fetch resource.",
    "Load failed",
  ])("recognizes %s regardless of current connectivity", (message) => {
    expect(isRouteModuleError(new TypeError(message))).toBe(true);
  });

  it.each([
    new TypeError("element2.getAttribute is not a function"),
    new Error("Internal Error"),
    null,
    "Failed to fetch dynamically imported module",
  ])("does not hide unrelated errors: %s", (error) => {
    expect(isRouteModuleError(error)).toBe(false);
  });
});

describe("createModuleLoadReloader", () => {
  it("reloads on reconnect for a module-load error", () => {
    const { reload } = stubBrowser();
    const reloader = createModuleLoadReloader(() => true);
    reloader.onOnline();
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("reloads on mount when the connection is already back", () => {
    const { reload } = stubBrowser({ online: true });
    createModuleLoadReloader(() => true).onMount();
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("does not reload on mount while offline", () => {
    const { reload } = stubBrowser({ online: false });
    createModuleLoadReloader(() => true).onMount();
    expect(reload).not.toHaveBeenCalled();
  });

  it("never reloads for other errors", () => {
    const { reload } = stubBrowser();
    const reloader = createModuleLoadReloader(() => false);
    reloader.onOnline();
    reloader.onMount();
    expect(reload).not.toHaveBeenCalled();
  });

  it("reloads at most once per URL across attempts and page instances", () => {
    const { reload, storage } = stubBrowser();
    const first = createModuleLoadReloader(() => true);
    first.onOnline();
    first.onOnline();
    expect(reload).toHaveBeenCalledTimes(1);

    // A new page instance after the reload sees the same guard.
    const second = createModuleLoadReloader(() => true);
    second.onMount();
    second.onOnline();
    expect(reload).toHaveBeenCalledTimes(1);
    expect([...storage.values()]).toEqual(["http://localhost:3000/origins"]);
  });

  it("leaves the reload to the user when sessionStorage is unavailable", () => {
    const { reload } = stubBrowser({ storageThrows: true });
    const reloader = createModuleLoadReloader(() => true);
    reloader.onOnline();
    reloader.onMount();
    expect(reload).not.toHaveBeenCalled();
  });
});
