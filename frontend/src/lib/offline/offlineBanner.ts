/**
 * Presentation-only debounce for the offline banner.
 *
 * The banner must never flash on a page load just because a raw
 * `navigator.onLine` sample is briefly false (startup races, SSR/client
 * desync). This controller delays *presentation only*: connectivity is
 * sampled via the injected `isOnline` getter, and a single grace timer runs
 * whenever a sample comes back offline. The banner is shown only if a fresh
 * re-sample at expiry is still offline. Any online sample cancels the timer
 * and hides the banner at once. No network reachability probes and no
 * ServiceWorker changes — callers keep their own connectivity side effects
 * (preload toggles, outbox flushes, sync) immediate.
 */

export const OFFLINE_BANNER_GRACE_MS = 1500;

export interface OfflineBannerOptions {
  /** Returns the current online state (defaults to `navigator.onLine`). */
  isOnline?: () => boolean;
  /** Called with the new visibility whenever it changes. */
  onVisibleChange: (visible: boolean) => void;
  /** Grace window a sample must stay offline for before the banner shows. */
  graceMs?: number;
  /** Injectable timer for tests. */
  setTimer?: (fn: () => void, ms: number) => ReturnType<typeof setTimeout>;
  clearTimer?: (timer: ReturnType<typeof setTimeout>) => void;
}

export interface OfflineBannerController {
  /**
   * Feed one fresh connectivity sample (mount or an online/offline event).
   * `online` is the connectivity at sample time.
   */
  sample(online: boolean): void;
  /** Cancel any pending grace timer; no further callbacks fire after this. */
  dispose(): void;
}

export function createOfflineBannerController(
  options: OfflineBannerOptions,
): OfflineBannerController {
  const { onVisibleChange, graceMs = OFFLINE_BANNER_GRACE_MS } = options;
  const isOnline = options.isOnline ?? (() => navigator.onLine);
  const setTimer = options.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
  const clearTimer = options.clearTimer ?? ((timer) => clearTimeout(timer));

  // Visibility starts false on both SSR and client — it only ever flips after
  // a sample and (for offline) the grace window.
  let visible = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  const setVisible = (next: boolean) => {
    if (disposed || next === visible) return;
    visible = next;
    onVisibleChange(next);
  };

  const cancelTimer = () => {
    if (timer !== null) {
      clearTimer(timer);
      timer = null;
    }
  };

  const onTimerExpired = () => {
    timer = null;
    if (disposed) return;
    // Re-sample at expiry: only a *still* offline connection shows the banner.
    if (!isOnline()) setVisible(true);
  };

  const sample = (online: boolean) => {
    if (disposed) return;
    if (online) {
      // Any online sample cancels the grace timer and hides immediately.
      cancelTimer();
      setVisible(false);
      return;
    }
    // Offline sample: schedule a single grace timer. An already-pending timer
    // is never postponed (repeated offline events don't reset it), and once
    // the banner is visible it stays visible while offline.
    if (timer === null && !visible) {
      timer = setTimer(onTimerExpired, graceMs);
    }
  };

  const dispose = () => {
    disposed = true;
    cancelTimer();
  };

  return { sample, dispose };
}
