# Files

- [curl_cffi Swap — 2026-08-01](curl-cffi-swap-2026-08.md) - Why the scraper HTTP client switched from bare httpx to a curl_cffi-backed shim, what changed, probe results, and known caveats.
- [Orphaned diffjson Cleanup — 2026-08](diffjson-orphan-cleanup-2026-08.md) - Removed 413 .diffjson files from data/roasters that were skipped by refresh as 'no matching bean found for URL' (no backing *.json bean), referenced from logs/refresh.log.
- [Operations](operations.md) - CLI commands, scheduled scraping, testing, database validation, proxy config, deployment, CI/CD, and maintenance scripts for Kissaten.
- [Playwright 429 Escalation Investigation — 2026-07-30](playwright-escalation-investigation-2026-07.md)
- [Scraper Log Analysis — July 2026 (Post-Fix)](scraper-log-analysis-2026-07-post-fix.md)
- [Scraper Log Analysis — July 2026](scraper-log-analysis-2026-07.md)
- [Scraper Rerun Recipe — 2026-07-31](scraper-rerun-recipe-2026-07.md) - How to identify today's failed scrapers and rerun them one at a time after a code-side fix lands. Documents the canonical 3-step recipe and the failure-signature taxonomy.
- [Scraper Token Consumption Investigation — Terarosa & Bluebird — 2026-08-10](scraper-token-consumption-investigation-2026-08.md) - Why the Terarosa and Bluebird scrapers burned so many AI tokens (optimized mode on unpruned 140-490 KB pages + a never-saved/re-scraped-every-run loop) and the implemented fixes: Bluebird Elementor pruning (~490->~5 KB), Terarosa product-box pruning (~137->~4 KB), Terarosa discovery-time junk filter (bag appears on all 6 category grids), the Terarosa lazy-load screenshot fix (origin sheet is image-only; 15,615px spec wall was blank in captures), and live verification against stored *.json incl. a full end-to-end rerun.
- [Tasting Notes Non-Flavour Audit — 2026-08](tasting-notes-non-flavour-audit-2026-08.md) - Audit of tasting_notes_categorized.csv and bean JSON tasting-notes arrays: identified 76 non-flavour metadata tokens (numbers, times, places, varieties, species, processes, field labels) mis-tagged as flavour notes, plus the 50 affected bean files.
- [UK Roasters Checklist](uk_roasters_checklist.md)
