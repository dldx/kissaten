import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createOfflineBannerController,
  OFFLINE_BANNER_GRACE_MS,
} from "./offlineBanner";

/**
 * Fake-timer regression tests for the banner debounce. The controller is pure
 * (injected online-state getter + visibility callback), so `vi.useFakeTimers`
 * drives the grace window deterministically without any browser or Svelte
 * harness.
 */

function makeController(initialOnline = true) {
  let online = initialOnline;
  const visible: boolean[] = [];
  const controller = createOfflineBannerController({
    isOnline: () => online,
    onVisibleChange: (v) => {
      visible.push(v);
    },
  });
  return {
    controller,
    visible,
    setOnline: (v: boolean) => {
      online = v;
    },
  };
}

describe("offlineBanner controller", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("stays hidden when the device is online from the start", () => {
    const { controller, visible } = makeController(true);
    controller.sample(true);
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS * 4);
    expect(visible).toEqual([]);
  });

  it("shows the banner only after the grace window for a stable offline state", () => {
    const { controller, visible } = makeController(false);
    controller.sample(false);
    expect(visible).toEqual([]);
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS - 1);
    expect(visible).toEqual([]);
    vi.advanceTimersByTime(1);
    expect(visible).toEqual([true]);
  });

  it("never shows when the device comes back online within the grace window", () => {
    const { controller, visible } = makeController(false);
    controller.sample(false);
    controller.sample(true);
    // Even if the timer were somehow still pending, advancing well past the
    // grace window must not fire a visibility change.
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS * 4);
    expect(visible).toEqual([]);
  });

  it("re-samples connectivity at expiry and stays hidden if back online", () => {
    const { controller, visible, setOnline } = makeController();
    controller.sample(false);
    setOnline(true); // connection recovered during the grace window
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS + 1);
    expect(visible).toEqual([]);
  });

  it("shows while stable offline, then hides immediately on an online sample", () => {
    const { controller, visible, setOnline } = makeController(false);
    controller.sample(false);
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS);
    expect(visible).toEqual([true]);
    // Once visible, further offline samples keep it visible.
    controller.sample(false);
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS * 2);
    expect(visible).toEqual([true]);
    setOnline(true);
    controller.sample(true);
    expect(visible).toEqual([true, false]);
  });

  it("does not reset the grace timer on repeated offline events", () => {
    const { controller, visible } = makeController(false);
    controller.sample(false);
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS - 500);
    controller.sample(false); // must NOT postpone the pending expiry
    vi.advanceTimersByTime(500);
    expect(visible).toEqual([true]);
  });

  it("dispose cancels pending grace work", () => {
    const { controller, visible } = makeController(false);
    controller.sample(false);
    controller.dispose();
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS * 4);
    expect(visible).toEqual([]);
    // Samples after dispose are no-ops too.
    controller.sample(false);
    vi.advanceTimersByTime(OFFLINE_BANNER_GRACE_MS);
    expect(visible).toEqual([]);
  });
});
