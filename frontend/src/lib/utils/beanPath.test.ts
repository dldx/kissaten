import { describe, expect, it } from "vitest";
import { parseBeanPath } from "./beanPath";

describe("parseBeanPath", () => {
  it("parses a bean_url_path without a route prefix", () => {
    expect(parseBeanPath("/kaffer_ven/ethiopia-guji")).toEqual({
      roasterSlug: "kaffer_ven",
      beanSlug: "ethiopia-guji",
      path: "/kaffer_ven/ethiopia-guji",
    });
  });

  it("drops the public /roasters route prefix", () => {
    expect(parseBeanPath("/roasters/kaffer_ven/ethiopia-guji")).toEqual({
      roasterSlug: "kaffer_ven",
      beanSlug: "ethiopia-guji",
      path: "/kaffer_ven/ethiopia-guji",
    });
  });

  it("accepts a full URL, trailing slash, query, and hash", () => {
    expect(
      parseBeanPath(
        "https://kissaten.app/roasters/kaffer_ven/ethiopia-guji/?ref=admin#top",
      ),
    ).toEqual({
      roasterSlug: "kaffer_ven",
      beanSlug: "ethiopia-guji",
      path: "/kaffer_ven/ethiopia-guji",
    });
    expect(parseBeanPath("kaffer_ven/ethiopia-guji?ref=admin")).toEqual({
      roasterSlug: "kaffer_ven",
      beanSlug: "ethiopia-guji",
      path: "/kaffer_ven/ethiopia-guji",
    });
  });

  it("decodes percent-encoded slugs", () => {
    expect(parseBeanPath("/kaffer%5Fven/ethiopia%2Dguji")).toEqual({
      roasterSlug: "kaffer_ven",
      beanSlug: "ethiopia-guji",
      path: "/kaffer_ven/ethiopia-guji",
    });
  });

  it("rejects missing or malformed paths", () => {
    for (const input of [
      "",
      "   ",
      null,
      undefined,
      "/kaffer_ven",
      "/roasters",
      "/kaffer_ven/ethiopia-guji/extra",
      "/kaffer ven/ethiopia-guji",
      "/kaffer_ven/ethiopia%2Fguji",
      "not a path",
    ]) {
      expect(parseBeanPath(input)).toBeNull();
    }
  });
});
