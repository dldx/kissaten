---
type: "Operations"
title: "Orphaned diffjson Cleanup — 2026-08"
description: "Removed 413 .diffjson files from data/roasters that were skipped by refresh as 'no matching bean found for URL' (no backing *.json bean), referenced from logs/refresh.log."
---

# Orphaned diffjson Cleanup — 2026-08

## Context

`logs/refresh.log` had thousands of recurring lines of the form:

```
Skipping .../xxx.diffjson: no matching bean found for URL <url>
```

These appear when `apply_diffjson_updates` (in `src/kissaten/api/db.py`) tries to apply a partial `.diffjson` update but can find no bean — in the database or on disk — whose URL matches. They are pure noise: the target is a non-coffee product (drip bags, filters, bundles, tea), a delisted item, or a product that never produced a base `*.json` bean file. Because each daily scrape regenerates a fresh copy of the same product diffjson, the same URLs were re-skipped every run.

## Scope of the Cleanup

- **Source of truth for selection:** the `.diffjson` paths flagged with *"no matching bean found"* in `logs/refresh.log`.
- **Count:** 413 unique `.diffjson` files, ~0.07 MB, all confirmed orphaned (no `*.json` bean with a matching URL existed for the roaster).
- **Deleted:** `data/roasters/<roaster>/<session_date>/...diffjson`.

This was deliberately **narrower** than deleting every diffjson lacking a same-dir json. A valid diffjson commonly lives in a later session dir than its base json (it is a stock/partial update), so orphan detection was scoped to files the refresh log actually reported, not a broad filesystem sweep.

## Outcome

Future `kissaten refresh --incremental` runs no longer re-process these dead updates, so the refresh log and Logfire spans are cleaner. The 435,758 valid `.diffjson` files (those with a backing json bean) were left untouched.

## Lessons / Notes

- A repeated *"no matching bean found for URL"* skip for the same base URL across many session dates is the signature of a non-bean or delisted product that will keep being re-scraped. Consider adding a roaster-level allowlist/denylist for such product URLs at the scraper level to avoid generating them in the first place.
- If datura-style roasters keep producing diffjson-only sessions (no json beans in that session dir), treat roaster-wide URL matching as the definition of "has a backing bean", not same-directory pairing.
