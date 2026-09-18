import { describe, expect, it } from "vitest";
import {
  isOfflineError,
  OFFLINE_ERROR_MESSAGE,
  OfflineError,
} from "./offlineError";

describe("OfflineError", () => {
  const url =
    "/api/v1/varietals/typica/beans?page=2&per_page=20&sort_by=date_added&sort_order=desc&convert_to_currency=GBP";

  it("keeps the API url out of the user-facing message", () => {
    const error = new OfflineError(url);

    expect(error.message).toBe(OFFLINE_ERROR_MESSAGE);
    expect(error.message).not.toContain("/api/");
    expect(error.message).not.toContain("?");
  });

  it("retains the url as a property for debugging", () => {
    const error = new OfflineError(url);

    expect(error.url).toBe(url);
    expect(error.name).toBe("OfflineError");
    expect(error).toBeInstanceOf(Error);
  });

  it("isOfflineError matches only OfflineError instances", () => {
    expect(isOfflineError(new OfflineError(url))).toBe(true);
    expect(isOfflineError(new Error("Failed to fetch"))).toBe(false);
    expect(isOfflineError(new TypeError("Failed to fetch"))).toBe(false);
    expect(isOfflineError(undefined)).toBe(false);
    expect(isOfflineError({ name: "OfflineError" })).toBe(false);
  });
});
