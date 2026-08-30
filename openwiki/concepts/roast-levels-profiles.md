---
type: concept
title: Roast Levels & Roast Profiles
description: Domain guide to roast levels (Extra-Light through Dark) and roast profiles (Espresso, Filter, Omni, Both), what they mean for flavour, and how Kissaten models and filters them.
tags: [roast-level, roast-profile, espresso, filter, specialty-coffee, kissaten]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-672470a76e59ca3e2d2c64ec
    resource: repo://frontend/src/lib/components/RoastProfileBar.svelte
  - id: openwiki-source-24225342590a035226d3afa6
    resource: repo://frontend/src/lib/components/search/SearchFilters.svelte
  - id: openwiki-source-3caf6a98926cd5705188c6a2
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%2Bpage.svelte
  - id: openwiki-source-7bed188005b136e8204477d7
    resource: repo://src/kissaten/ai/extractor.py
  - id: openwiki-source-f5f31640f5410e2338a4b6da
    resource: repo://src/kissaten/api/beanconqueror_share.py
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-a91bd1e17d487f691b479d46
    resource: repo://src/kissaten/schemas/coffee_bean.py
  - id: openwiki-source-dda104ebf8fb951b79d769b0
    resource: repo://src/kissaten/schemas/search.py
  - id: openwiki-source-889354d966b1963415f92972
    resource: repo://src/kissaten/scrapers/naughty_dog.py
  - id: openwiki-source-4180340b56127183b5c7c731
    resource: repo://src/kissaten/scrapers/square_mile.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Roast Levels & Roast Profiles

Roast degree and roast intent are two distinct pieces of information about a coffee. **Roast level** describes *how dark* the bean was roasted — a position on a spectrum from Extra-Light to Dark. **Roast profile** describes *what the roast is for* — whether it is intended for espresso extraction, filter brewing, both, or a single roast that suits both methods. Kissaten records both as separate fields on every `CoffeeBean`, exposes them as search facets, and uses roast level as an ordered scale for relevance scoring and similarity recommendations.

## The roast level spectrum

Roast level is a finite, ordered set of six buckets defined by the `RoastLevel` enum in `src/kissaten/schemas/coffee_bean.py`:

```python
class RoastLevel(Enum):
    """Roast level enum."""

    EXTRA_LIGHT = "Extra-Light"
    LIGHT = "Light"
    MEDIUM_LIGHT = "Medium-Light"
    MEDIUM = "Medium"
    MEDIUM_DARK = "Medium-Dark"
    DARK = "Dark"
```

The six members map to the canonical string values `Extra-Light`, `Light`, `Medium-Light`, `Medium`, `Medium-Dark`, and `Dark`, which are what scrapers emit, what is stored in the `roast_level` DuckDB column, and what the frontend renders. An `Enum` is used here rather than a `Literal` because roast level is a small, stable, standardised categorisation: every bean must fall into exactly one of these buckets (or be `None`), the set is finite and shared across the extractor prompt, the Beanconqueror export mapping, and the UI, and the values participate in ordered comparisons (see [Closeness scoring](#closeness-scoring)) below).

### What each degree means for flavour

Roast degree trades origin character for roast character. As beans spend longer in the roaster and reach higher temperatures, the balance shifts from the coffee's intrinsic chemistry toward the chemistry of the roasting process itself:

| Level | Flavour emphasis |
|-------|------------------|
| **Extra-Light / Light** | Maximum origin character: pronounced acidity, florals, delicate fruit, and high clarity. Green/tea-like notes can appear at the extreme light end. |
| **Medium-Light / Medium** | Balance: origin character retained with increased sweetness and body, rounded acidity. |
| **Medium-Dark / Dark** | Roast character dominates: bittersweet chocolate, caramelised sugars, toasted nuts, lower acidity, heavier body, and roasted/bitter notes. |

This relationship matters for two adjacent domains. Because lighter roasts preserve delicate aroma compounds, they tend to carry the floral, citrus, and stone-fruit descriptors catalogued in the [tasting-note taxonomy](/openwiki/concepts/tasting-note-taxonomy.md); roast level therefore strongly influences which tasting notes are likely to appear on a bean. And because cupping evaluates coffees roasted relatively light to highlight origin quality, lighter roasts often score higher on the SCA 100-point scale documented in [cupping-scores.md](/openwiki/concepts/cupping-scores.md). Darker roasts, by contrast, may mask defects but also obscure the very origin character that cupping rewards.

## Roast profiles

While roast level is a spectrum, roast profile is a small categorical statement of brewing intent. Kissaten models it as a `Literal` rather than an `Enum`:

```python
roast_profile: Literal["Espresso", "Filter", "Omni", "Both"] | None = Field(
    None,
    description="Is it for espresso or filter? If both with the same beans, use 'Omni'. "
    "If espresso and filter profiles are offered as separate options on the same page, use 'Both'.",
)
```

A `Literal` is appropriate here because the four values are roaster-facing terminology rather than a standardised industry scale. The distinction between `Omni` and `Both` in particular is a modelling convention for how a roaster presents a product, not a universally agreed coffee category, so a lighter-weight typed-string constraint is a better fit than a named enum. The same `Literal["Espresso", "Filter", "Omni", "Both"]` appears verbatim on the canonical `CoffeeBean`, the `CoffeeBeanDiffUpdate` diff-update schema, and the `v1` API bean model, keeping the allowed vocabulary identical across ingestion, updates, and serving.

The four profiles encode two orthogonal ideas — *is this for espresso, filter, or both* — and *how "both" is presented*:

- **Espresso** — the roast is developed dark enough to extract well under the pressure and short contact time of espresso. Typically a darker roast with more body and lower acidity.
- **Filter** — a lighter roast aimed at pour-over and immersion brewing, where longer contact times and no pressure favour clarity, acidity, and aromatic delicacy.
- **Omni** — a single roast of the same beans that the roaster considers suitable for both espresso and filter. There is one product/bean, roasted once, intended to work across methods.
- **Both** — the roaster offers distinct espresso *and* filter roasts of the same coffee as separate options on the same product page. This is a presentation signal rather than a roast recipe: there are effectively two profiles behind one listing.

The `Both` distinction matters for filtering: a bean marked `Both` is genuinely suitable for either method, so the search UI treats it as matching whichever profile category the user selects (see [Roast profile filtering](#roast-profile-filtering)).

### How scrapers assign roast profile

Roast profile is normally extracted by the AI extractor, but several scrapers override or derive it from authoritative source data:

- **Square Mile** reads the product `tags` array and sets `Both` when both `espresso` and `filter` tags are present, `Espresso` for espresso-only, and `Filter` for filter-only, overriding the AI-extracted value because the tags are authoritative.
- **April Coffee** and **Assembly Coffee** set `Filter` or `Espresso` based on the collection/usage the product belongs to.
- **Picky Chemist** hard-codes `Omni`.
- **Naughty Dog** parses a "usage" string via `_roast_profile`, mapping `omni`/`espresso`/`filter` substrings to the corresponding `Literal` value.

These per-roaster rules illustrate why the field is a `Literal`: the value is whatever the roaster's site expresses, normalised into one of four labels, rather than a value drawn from a centralised enum registry.

## How Kissaten models the two fields

Both fields are optional (`... | None`) on every bean, because a roaster's page may not state a roast level or profile. They are stored as plain `VARCHAR` columns in DuckDB (`roast_level`, `roast_profile`) and carried through the `v1` API responses unchanged. Because the `CoffeeBean` model is configured with `use_enum_values=True`, the `RoastLevel` enum serialises to its string value in JSON, so the wire format and the stored format are the canonical strings, not enum names.

Both fields are also present on the partial-update `CoffeeBeanDiffUpdate` schema, so a diffjson can correct a roast level or profile without re-scraping the whole bean.

### External mapping: Beanconqueror export

When a bean is shared to the Beanconqueror app, Kissaten maps its internal roast values onto Beanconqueror's protobuf enums. The roast level is mapped to the nearest Beanconqueror `Roast` enum value (`Extra-Light`→Cinnamon, `Light`→American, `Medium-Light`→City+, `Medium`→Full City, `Medium-Dark`→Full City+, `Dark`→French), defaulting to `UNKNOWN_ROAST` (0) when absent. The roast profile is mapped to Beanconqueror's `bean_roasting_type` with `Filter`→1, `Espresso`→2, and both `Omni` and `Both`→3 (Beanconqueror's `OMNI` value covers the kissaten sense of "both").

## Closeness scoring

Because roast level is an ordered scale, Kissaten uses it for more than exact-match filtering. In `build_coffee_bean_filters` (when `use_scoring=True`), a plain roast-level string — with no wildcard or boolean operators — is scored by *closeness* rather than equality. Both the candidate's and the target's roast levels are mapped to integers on the same scale:

```
Extra-Light → 0, Light → 1, Medium-Light → 2, Medium → 3, Medium-Dark → 4, Dark → 5
```

The closeness contribution is `1.0` for an exact match, `0.5` for a one-level difference, and `0.2` for a two-level difference, multiplied by the configurable `roast_level` weight. This is what powers bean-to-bean "similar roasts" recommendations: a Light bean will rank a Medium-Light candidate above a Dark one even though neither is an exact match. Unknown roast levels map to `NULL` on the candidate side (and to `3`, Medium, on the target side) to avoid false proximity matches. When the roast-level filter *does* contain wildcards or boolean operators (`|`, `&`, `!`, `*`, `?`, `()`), it falls back to the generic boolean text filter against `cb.roast_level` instead of the closeness scale.

## Roast level and roast profile in search

Both fields are first-class search facets exposed through the same `build_coffee_bean_filters` builder and the `FilterParams` dataclass, which carries `roast_level` and `roast_profile` as free-text string parameters. They flow from the `roast_level` and `roast_profile` query parameters on the search endpoints (e.g. `GET /v1/search/coffee-beans`) into the SQL filter/scoring layer.

### Roast level filtering

In the frontend, roast level is a free-text `Input` in `SearchFilters.svelte` (id `roastLevelFilter`) with the placeholder `Light|Medium-Light|Medium|Medium-Dark|Dark`, signalling that it accepts the boolean query syntax (`|` OR, `&` AND, `!` NOT, `*`/`?` wildcards). The value is serialised to the `roast_level` URL parameter and rendered as a removable filter tag ("roast level") in `FilterTags.svelte`. On the backend, a simple single value triggers the closeness scoring path described above; a query containing operators triggers the boolean `ILIKE` filter path against `cb.roast_level`.

### Roast profile filtering

Roast profile is exposed as two checkboxes — **Filter** and **Espresso** — plus an **"Include omni roasts"** checkbox that appears once either is selected. The `SearchFilters.svelte` component translates these UI selections into a boolean-OR query string:

- Selecting *Filter* alone produces `Filter|Both|Omni` (when omni is included).
- Selecting *Espresso* alone produces `Espresso|Both|Omni`.
- Selecting both produces `Filter|Espresso|Both|Omni`.

`Both` is always appended when either category is chosen, because a `Both` bean is suitable for either method. `Omni` is appended only when "include omni" is checked (which is the default). With neither box checked the filter is cleared entirely. The resulting string is sent as the `roast_profile` URL parameter and rendered as a "roast profile" filter tag. On the backend, `roast_profile` is always handled by the generic boolean search filter (`add_boolean_search_filter` against `cb.roast_profile`); unlike roast level, it has no closeness scoring because it is not an ordered scale.

## The RoastProfileBar component

On the roaster detail page, the `RoastProfileBar.svelte` component renders a stacked horizontal bar showing the distribution of a roaster's beans across roast levels. Despite its name ("Roast Profile"), it visualises **roast level**, not the Espresso/Filter profile.

Key behaviours:

- **Five buckets, not six.** The bar collapses the six-value spectrum into five visual buckets — Light, Medium-Light, Medium, Medium-Dark, Dark — by folding `Extra-Light` into `Light` (and normalising spelling variants such as `Medium Light` / `Medium light` into `Medium-Light`). This keeps the bar compact; the rare Extra-Light bucket is aggregated with Light for display.
- **Proportional segments.** Each bucket's width is its share of the roaster's total bean count; segments below 5% hide their inline label and reveal it via an above-bar callout with a leader line on hover.
- **Colour gradient.** Buckets are coloured from light amber (`bg-amber-100`) for Light through to near-black (`bg-stone-800`) for Dark, giving an intuitive light-to-dark visual.
- **Deep-link to search.** Each segment is an `<a>` linking to `/search?roaster=<name>&roast_level=<bucket>`, so clicking a segment filters that roaster's beans by roast level. When no roaster context is supplied the link falls back to `/search`.
- **Accessibility.** The bar is marked `role="img"` with an `aria-label` enumerating each visible segment's label and percentage, and each segment anchor carries a title and aria-label with the bean count and percentage.

The component is mounted on the roaster page only when the roaster has sufficient roast data; otherwise the page falls back to a flavour-profile-only view.

## Summary of modelling choices

- **`RoastLevel` is an `Enum`** because it is a finite, standardised, ordered set of categories shared across extraction, storage, export, and UI, and its ordering is exploited for closeness scoring.
- **`roast_profile` is a `Literal`** because its four values are roaster-facing terminology for brewing intent (including the presentation-only `Both`), not a centralised industry scale, and a typed-string constraint is the lighter, more honest fit.
- **Both are optional `VARCHAR`s in DuckDB** and flow through diffjson updates and the `v1` API unchanged.
- **Roast level is an ordered scale** used for similarity/relevance scoring; **roast profile is a categorical facet** used only for boolean filtering, with `Both` always included when either Espresso or Filter is selected.
