import { describe, expect, it } from "vitest";
import type { ApiCacheEntry } from "$lib/db/localdb";
import {
  buildOptions,
  buildOptionsFromCache,
  hasUsableOptions,
} from "./layoutOptions";

function entry(json: any): ApiCacheEntry {
  return { key: "test", json, savedAt: Date.now(), ttlClass: "long" };
}

const countriesBody = {
  success: true,
  data: [{ country_code: "CO", country_name: "Colombia" }],
};
const roastersBody = { success: true, data: [{ slug: "roaster-a" }] };
const locationsBody = {
  success: true,
  data: [{ code: "CO", location: "Colombia", roaster_count: 3 }],
};

describe("buildOptions", () => {
  it("maps raw API bodies to option lists", () => {
    const options = buildOptions({
      countries: countriesBody,
      roasters: roastersBody,
      roasterLocations: locationsBody,
    });

    expect(options.originOptions).toEqual([
      { value: "CO", text: "Colombia" },
    ]);
    expect(options.allRoasters).toEqual([{ slug: "roaster-a" }]);
    expect(options.roasterLocationOptions).toEqual([
      { value: "CO", text: "Colombia (3)" },
    ]);
    expect(hasUsableOptions(options)).toBe(true);
  });

  it("falls back to the country code when no name is present", () => {
    const options = buildOptions({
      countries: { success: true, data: [{ country_code: "CO" }] },
    });

    expect(options.originOptions).toEqual([{ value: "CO", text: "CO" }]);
  });
});

describe("buildOptionsFromCache", () => {
  it("unwraps ApiCacheEntry.json instead of reading the wrapper", () => {
    const options = buildOptionsFromCache(
      entry(countriesBody),
      entry(roastersBody),
      entry(locationsBody),
    );

    expect(options.originOptions).toEqual([
      { value: "CO", text: "Colombia" },
    ]);
    expect(options.allRoasters).toHaveLength(1);
    expect(options.roasterLocationOptions).toEqual([
      { value: "CO", text: "Colombia (3)" },
    ]);
    expect(hasUsableOptions(options)).toBe(true);
  });

  it("reports failed/corrupt bodies as unusable", () => {
    const options = buildOptionsFromCache(
      entry({ success: false, data: null }),
      entry(roastersBody),
      entry(locationsBody),
    );

    expect(options.originOptions).toEqual([]);
    expect(hasUsableOptions(options)).toBe(false);
  });
});
