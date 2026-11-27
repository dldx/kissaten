import { afterEach, describe, expect, it, vi } from "vitest";
import {
  formatDevVerificationCode,
  printDevVerificationCode,
} from "./dev-login-code";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("formatDevVerificationCode", () => {
  it("includes the email", () => {
    expect(
      formatDevVerificationCode("tester@kissaten.app", "123456"),
    ).toContain("tester@kissaten.app");
  });

  it("includes the OTP", () => {
    expect(
      formatDevVerificationCode("tester@kissaten.app", "654321"),
    ).toContain("654321");
  });

  it("includes the expiry note", () => {
    expect(
      formatDevVerificationCode("tester@kissaten.app", "123456"),
    ).toContain("expires in 5 minutes");
  });

  it("makes the code easy to spot", () => {
    const banner = formatDevVerificationCode("tester@kissaten.app", "123456");
    expect(banner).toContain("code:  123456");
  });
});

describe("printDevVerificationCode", () => {
  it("logs the formatted banner via console.log", () => {
    const spy = vi.spyOn(console, "log").mockImplementation(() => {});
    printDevVerificationCode("tester@kissaten.app", "123456");
    expect(spy).toHaveBeenCalledWith(
      formatDevVerificationCode("tester@kissaten.app", "123456"),
    );
  });
});
