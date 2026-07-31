# Files

- [Operations](operations.md) - CLI commands, scheduled scraping, testing, database validation, proxy config, deployment, CI/CD, and maintenance scripts for Kissaten.
- [Scraper Log Analysis 2026-07](scraper-log-analysis-2026-07.md) - Prioritized issue list from the 2026-07-10 → 2026-07-29 scrape logs (proxy outage, out-of-stock clobbering, currency misdetection, 429s, refresh/validation failures).
- [Scraper Log Analysis 2026-07 (Post-Fix)](scraper-log-analysis-2026-07-post-fix.md) - Status of each issue after the proxy + listing-fetch-guard + validate-db fixes were deployed. 4 fixed, 6 partial, 7 not fixed; Playwright escalation not actually unblocking 429s.
- [Playwright 429 Escalation Investigation 2026-07](playwright-escalation-investigation-2026-07.md) - Root cause and recommended fix for the broken ShopifyJsonScraper → Playwright escalation: 35s of wasted backoff before upgrade, no Playwright retries, latent UnboundLocalError on a successful upgrade, and the shared-proxy architectural issue.
