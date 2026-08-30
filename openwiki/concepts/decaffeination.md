---
type: concept
title: Decaffeination
description: How Kissaten models decaffeination (the is_decaf boolean), the major decaffeination methods, why decaf matters for accessibility, and how the search filter surfaces it end to end.
tags: [decaf, coffee-bean, search-filters, accessibility, data-model]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-4735c40fd9ffe1e0754310f9
    resource: repo://frontend/src/lib/api.ts
  - id: openwiki-source-35aacac0c5c266af35e7486b
    resource: repo://frontend/src/lib/components/search/FilterTags.svelte
  - id: openwiki-source-24225342590a035226d3afa6
    resource: repo://frontend/src/lib/components/search/SearchFilters.svelte
  - id: openwiki-source-b9b678dc2f547df4edcc8159
    resource: repo://frontend/src/lib/stores/search.ts
  - id: openwiki-source-6fefffdc53af3312d4de54c1
    resource: repo://frontend/src/routes/(main)/search/%2Bpage.ts
  - id: openwiki-source-f5f31640f5410e2338a4b6da
    resource: repo://src/kissaten/api/beanconqueror_share.py
  - id: openwiki-source-b6db435ba1198be65f340e6b
    resource: repo://src/kissaten/api/db.py
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-50b79375ebd5a7c434d39354
    resource: repo://src/kissaten/schemas/ai_search.py
  - id: openwiki-source-0d95f608f6d7d340f981a2cc
    resource: repo://src/kissaten/schemas/api_models.py
  - id: openwiki-source-a91bd1e17d487f691b479d46
    resource: repo://src/kissaten/schemas/coffee_bean.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Decaffeination

Decaffeination — the removal of caffeine from green coffee before roasting — is a first-class concern in Kissaten because it is primarily an **accessibility** question. Many people are advised or required to limit caffeine (pregnancy, anxiety, cardiac arrhythmia, sleep disorders, certain medications), and for them "decaf vs regular" is not a flavour preference but a hard constraint. Surfacing decaf options reliably is therefore as important as surfaging allergen information.

This page documents how Kissaten models decaffeination, why the model is deliberately simple, the real-world methods the boolean abstracts over, and how the flag flows from the database through the API to the frontend filter.

## Why a simple boolean, not a method enum

The canonical data model stores decaffeination as a single boolean, `is_decaf`, rather than capturing *which* method was used (Swiss Water, CO2, ethyl acetate, methylene chloride, etc.). There are two reasons, both grounded in data reality:

1. **Roasters do not consistently specify the method.** Product pages vary widely: some proudly state "Swiss Water Process", others say only "decaffeinated", and many say nothing at all even when the bean is decaf. A method enum would be sparsely populated and unreliable, and missing values would be indistinguishable from "unknown method".
2. **The primary user need is filtering, not method selection.** A caffeine-sensitive user needs to *exclude* caffeinated beans; whether the decaf was water- or solvent-processed is a secondary, usually optional, concern. A boolean matches the actual decision the filter supports.

The boolean therefore optimises for coverage and filterability over depth. Method information, when present, is expected to live in the free-text `description` or `tasting_notes`, where full-text search can find it for the curious minority who care.

## Data model

### `CoffeeBean` (authoritative schema)

In the strict, authoritative schema the field is a plain boolean that defaults to `False`:

```python
is_decaf: bool = Field(False, description="Whether the coffee is decaffeinated")
```

This is the contract scrapers and diffjson updates are expected to satisfy: a bean is decaf (`True`) or not (`False`), with `False` as the safe default for the overwhelming majority of regular coffee.

### Lenient / API variants (`bool | None`)

Several surrounding schemas relax the field to `bool | None`:

- **`CoffeeBeanDiffUpdate`** — partial updates via diffjson allow `is_decaf: bool | None`; `None` means "do not change this field".
- **`CoffeeBeanOptional`** — the lenient schema for user-submitted or partial data makes every field optional, including `is_decaf: bool | None`.
- **`APICoffeeBean`** — the API response model overrides `is_decaf` to `bool | None` explicitly **for backward compatibility with existing data**. Older rows may carry `NULL` rather than a populated boolean, and the API must not reject them.

This `None` tolerance is the bridge between the strict authoring contract (`bool`, default `False`) and the messier reality of historical/partial data. The database layer closes the gap with `COALESCE`.

### Database persistence

The `coffee_beans` table declares the column as a nullable boolean:

```sql
is_decaf BOOLEAN,
```

Because the column is nullable, historical or partial inserts can leave it `NULL`. The load/insert path therefore normalises with `COALESCE(is_decaf, false)` so that beans with missing decaf status are treated as regular coffee rather than being silently dropped from "caffeinated only" queries. New data defaults to `False` via this `COALESCE` rather than a column default, which keeps the logic in one place and resilient to pre-existing rows.

## Major decaffeination methods

These are the real-world processes that the single `is_decaf = True` value abstracts over. Kissaten does not model them individually, but they explain why decaf beans often taste different and are roasted differently (see [roast-levels-profiles](/openwiki/concepts/roast-levels-profiles.md)).

- **Swiss Water Process (SWP).** Chemical-free. Green beans are soaked in water saturated with the flavour compounds of coffee (Green Coffee Extract); caffeine migrates out across a concentration gradient and is trapped by activated-carbon filters tuned to caffeine's molecular size. The result is 99.9% caffeine-free with no solvent residue. Common in specialty coffee and frequently the only method a roaster will voluntarily name.
- **CO2 Process (supercritical carbon dioxide).** Liquid/supercritical CO2 is circulated through water-soaked beans under high pressure; it selectively dissolves caffeine while leaving most flavour compounds behind. The caffeine is recovered from the CO2, which is recycled. Scalable and effective, but requires industrial-scale pressure vessels, so it tends to appear on larger-volume decafs.
- **Ethyl Acetate / Sugarcane Process.** Uses ethyl acetate as the solvent. When derived from fermented sugarcane (or other fruit) it is marketed as the "natural" or "sugarcane" process. The beans are steamed before and after to remove residual solvent. It can leave a faintly sweet, fruity character and is popular among roasters who want a "natural" label.
- **Methylene Chloride (MC).** The traditional solvent method. Methylene chloride selectively bonds to caffeine; beans are steamed repeatedly to strip residual solvent. Trace residues are typically well below regulatory limits, but the method is less common in specialty coffee and is declining as roasters and consumers favour water- and CO2-based processes.

All four reduce caffeine to the level legally required to be sold as "decaffeinated" (commonly 97–99.9% removed). Because each method subtly alters the green coffee's chemistry, decaf beans are frequently roasted **darker** than their caffeinated equivalents to compensate for flavour loss and to mask process-derived off-notes — which is why the decaf flag and the roast-level model are related concerns (see [roast-levels-profiles](/openwiki/concepts/roast-levels-profiles.md)).

## Search and filtering

### Backend: `is_decaf` is a hard filter

The `/v1/search` (and related list) endpoints expose `is_decaf` as an optional query parameter:

```python
is_decaf: bool | None = Query(None, description="Filter by decaf status")
```

- `None` (default) — no decaf constraint; both decaf and regular beans are returned.
- `True` — only decaf beans.
- `False` — only caffeinated beans ("Caffeinated only").

Crucially, `is_decaf` is treated as a **hard filter**, never a soft scoring component. When set, it is appended to `hard_conditions` as an exact `cb.is_decaf = ?` `WHERE` clause:

```python
if filter_params.is_decaf is not None:
    # is_decaf is always a hard filter - it should never be a soft score component
    # because showing beans with the wrong caffeine status is never useful
    hard_conditions.append("cb.is_decaf = ?")
    hard_params.append(filter_params.is_decaf)
```

The rationale is an accessibility invariant: showing a caffeine-sensitive user a caffeinated bean (or vice versa) because it scored highly on *other* dimensions is never useful. Decaf status is a hard requirement, not a preference to be traded off, so it bypasses the relevance-scoring machinery entirely. This mirrors `is_tasting_kit`, while softer attributes (origin, roast level, tasting notes) contribute to the relevance score.

The same `FilterParams.is_decaf: bool | None` field and `build_coffee_bean_filters` logic are reused across every bean-listing path (search, recommendations, discovery), so the hard-filter behaviour is consistent everywhere.

### AI search

The natural-language AI search schema mirrors the structured parameter set. `SearchParameters` (which extends `BasicSearchParameters`) carries:

```python
is_decaf: bool | None = Field(None, description="Filter by decaf status")
```

This lets the AI translate a query such as "decaf espresso beans" into `is_decaf=True` alongside the roast-profile filter, and the resulting `search_url` carries `is_decaf=true` exactly as if the user had toggled the filter manually. The AI never *softens* the constraint: the value is either set or absent, and once set it becomes a hard `WHERE` in the downstream search.

### Frontend: three-state radio toggle

The frontend models decaf as a tri-state `boolean | undefined`, matching the API's `bool | None`:

- `undefined` → no `is_decaf` query parameter sent (show all).
- `true` → `is_decaf=true` (Decaf only).
- `false` → `is_decaf=false` (Caffeinated only).

In `SearchFilters.svelte` this is rendered as a three-option radio group — **All / Decaf only / Caffeinated only** — bound to the `isDecaf` prop. Selecting any option immediately triggers `onSearch()`, so the constraint applies live rather than waiting on a separate "Apply" action.

The state is serialised to and from the URL by the search store and the route loaders: `is_decaf` is written as a query string (`is_decaf=true` / `is_decaf=false`) only when defined, and parsed back with the same three-way logic (`"true"` → `true`, `"false"` → `false`, absent → `undefined`). This keeps the filter shareable and bookmarkable.

`FilterTags.svelte` surfaces the active constraint as a removable chip — "Decaf only" (with a ban icon) or "Caffeinated only" (with a zap icon) — so the user can see, and clear, the current caffeine constraint at a glance.

### Discovery / recommendations

The discovery recommendations client (`getDiscoveryRecommendations`) supports an `isDecafSwap` option: when viewing a caffeinated bean, it can request recommendations with `is_decaf` set to the *opposite* of the current bean's `is_decaf`, surfacing "try the decaf equivalent" (or vice versa). When the source bean's `is_decaf` is unknown (`undefined`), the swap falls back to `is_decaf=true` so that a decaf alternative is still offered. This is one of the few places the flag drives *content selection* rather than a hard exclusion.

### External share format

The Beanconqueror share exporter maps `is_decaf` onto the target app's `decaffeinated` proto field, coercing it to a strict boolean (`bool(bean.is_decaf)`) so the downstream decoder never sees `undefined`. This is the boundary at which the lenient `bool | None` is collapsed back to the strict `bool` the external contract requires.

## Summary

Kissaten treats decaffeination as an accessibility-relevant hard constraint, modelled as a simple `is_decaf` boolean because roasters do not reliably specify the method and the user's primary need is to filter, not to select a process. The strict schema defaults to `False`; lenient and API schemas allow `None` for backward compatibility with historical data; and the database closes the gap with `COALESCE(is_decaf, false)`. In search, the flag is always a hard `WHERE` filter — never a soft score — and the frontend exposes it as a three-state All / Decaf only / Caffeinated only toggle that round-trips cleanly through the URL and the AI search schema.
