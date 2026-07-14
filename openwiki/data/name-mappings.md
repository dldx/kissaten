# Name Mappings & Canonical Reference Data

Kissaten normalises raw strings from 150+ roaster websites into canonical names for processing methods, varietals, tasting notes, farms, and regions. This page documents the mapping files, their structure, the AI categorizers that produce them, and the validation gates that enforce integrity.

All mapping files live under `src/kissaten/database/`. The AI categorizers that generate them live under `src/kissaten/ai/`.

---

## Mapping Files Overview

| File | Entries | Maps | Source |
|---|---|---|---|
| `processing_methods_mappings.json` | ~1,200 | Raw process strings → canonical process names | `ProcessCategorizer` |
| `varietal_mappings.json` | ~1,560 | Raw varietal strings → canonical varietal name(s) | `VarietalCategorizer` |
| `coffee_varietals.json` | 100 | Canonical varietal reference (WCR) | Static (World Coffee Research) |
| `farm_mappings.json` | ~500 | Normalised farm aliases → canonical farm name | Dedup pipeline |
| `taste_lexicon.json` | 21 category blocks | Three-tier flavour taxonomy | `TastingNoteCategorizer` + manual |
| `tasting_notes_categorized.csv` | ~2,700 rows | Raw tasting notes → primary/secondary/tertiary category | `TastingNoteCategorizer` |
| `region_mappings/*.json` | 48 country files | Raw region names → canonical admin region + geo data | `RegionSelector` + OpenCage |
| `countrycodes.csv` | 249 rows | ISO 3166-1 country code reference | Static |
| `roaster_location_codes.csv` | 49 rows | Roaster locations → region codes (incl. continent pseudo-codes) | Static |

---

## Processing Method Mappings

**File**: `src/kissaten/database/processing_methods_mappings.json` (~159K)

### Structure

```json
{
  "original_name": "Anaerobic Fermentation Natural",
  "common_name": "Anaerobic Natural",
  "confidence": 1.0
}
```

### Major Canonical Processes

| Canonical Name | Example Raw Names |
|---|---|
| **Washed** | `Washed`, `washed`, `WASHED`, `Fully washed`, `FULLY WASHED`, `Double Washed`, `Classic Washed`, `Traditional washed`, `Kenyan Washed` |
| **Natural** | `Natural`, `natural`, `Traditional Natural`, `Classic Natural`, `Sun-dried Natural` |
| **Pulped Natural** | `Pulped Natural`, `pulped natural` |
| **Honey** | `Honey`, `honey`, `Black Honey`, `Red Honey`, `Yellow Honey`, `White Honey`, `Honey Process`, `Honey Processed` |
| **Anaerobic Natural** | `Anaerobic Natural`, `anaerobic natural`, `Natural Anaerobic`, `Double Anaerobic Natural`, `Anaerobic Fermentation Natural` |
| **Anaerobic Washed** | `Anaerobic Washed`, `anaerobic washed`, `Double Anaerobic Washed`, `Washed Anaerobic`, `Anaerobic Washed Thermal Shock` |
| **Anaerobic Honey** | `Anaerobic Honey`, `anaerobic honey`, `Double Anaerobic Honey`, `Anaerobic Red Honey`, `Anaerobic Honey Co-Fermented` |
| **Anaerobic Fermentation** | `Anaerobic`, `Anaerobic Fermentation`, `anaerobic fermentation` |
| **Carbonic Maceration** | `Carbonic Maceration`, `Carbonic Maceration Natural`, `Carbonic Maceration Washed`, `Carbonic Macerated` |
| **Co-Ferment** | `Co-Ferment`, `Co-ferment`, `Co-Fermented`, `Co-fermented`, `Co-Fermented Natural`, `Washed, Co-Ferment` |
| **Thermal Shock** | `Thermal Shock`, `thermal shock washed`, `Washed Thermal Shock`, `Double Anaerobic Thermal Shock` |
| **Semi-Washed** | `Semi-Washed`, `Semi-washed`, `Semi Washed`, `Semiwashed` |
| **Wet-Hulled** | `Wet Hulled`, `Wet-hulled`, `Wethull` |
| **Sugarcane EA Decaf** | `Sugarcane Decaf`, `Sugarcane EA Decaf`, `EA Decaf`, `EA Sugarcane Decaf`, `Sugar cane decaf` |
| **Swiss Water Decaf** | `Swiss Water`, `Swiss Water Decaf`, `Swiss Water Process` |
| **Mountain Water Decaf** | `Mountain Water Decaf`, `Mountain Water Process` |
| **Advanced Process** | `Advanced`, `Advanced Process`, `Advanced Controlled Fermentation`, `Advanced Fermentation Natural` |

Additional canonical names include: Anaerobic Koji Honey, Anaerobic Slow Dry, Anaerobic Nitrogen Washed, Lactic Fermentation Washed, Lactic Washed, Lactic Natural, Koji Natural, Koji Process, Mossto Anaerobic, Mosto Anaerobic Natural, Double Fermentation, Double Fermented Washed, Extended Fermentation Washed, Experimental Washed/Natural/Honey, Yeast Fermentation, Yeast Inoculated Washed/Natural, Nitrogen Washed, Nitrogen Natural, Carbonic Natural, Carbonic Honey, Cold Fermentation, Cold Ferment Natural, DRD (Dark Room Dry), Hydro Honey, Hydro Natural, Hydro Washed, Symbiotic Process, Inverted Process, Supernatural, Alchemy Process, Enzyflow, Bioreactor, and more.

### How It Works (`ai/processing_method_categorizer.py`)

The `ProcessCategorizer` uses three PydanticAI agents (all `gemini-3.5-flash`):

1. **Categorization agent** — Maps raw names to canonical names. System prompt rules:
   - Only merge names referring to the *exact same* process.
   - Never merge different base processes (Natural vs Washed vs Honey vs Semi-washed), different fermentation types (aerobic vs anaerobic), different drying methods, or different decaf methods (EA vs Swiss Water vs CO₂).
   - Word ordering, adverbs ("carefully", "slowly"), time/duration info, punctuation, and abbreviations do NOT block merging.
   - `"Fully Washed"` = `"Washed"`. `"Honey"` = `"Pulped Natural"`.

2. **Merge agent** — Reviews existing canonical names for further merge opportunities.

3. **Conflict resolution agent** — Resolves cases where different originals map to the same canonical. Flags over-merging (e.g. Black Honey ≠ Red Honey, lychee co-ferment ≠ mango co-ferment).

Pipeline: batched categorisation (50 names/batch) → conflict detection → conflict resolution → merge review → save to JSON.

---

## Varietal Mappings

**File**: `src/kissaten/database/varietal_mappings.json` (~271K)

### Structure

```json
{
  "original_name": "Bourbon, Caturra, Catuai",
  "canonical_names": ["Bourbon", "Caturra", "Catuai"],
  "confidence": 0.8,
  "is_compound": true,
  "separator": ", "
}
```

### Major Canonical Varietals

| Canonical Name | Example Raw Names |
|---|---|
| **Bourbon** | `Bourbon`, `BOURBON`, `Bourbon Arabica` |
| **Red Bourbon** | `Bourbon Red`, `Bourbon Rojo`, `RED BOURBON` |
| **Yellow Bourbon** | `Bourbon Yellow`, `Bourbon Amarillo`, `YELLOW BOURBON` |
| **Typica** | `Typica`, `TYPICA`, `Arabica Typica`, `Arabika Typica`, `Tipica` |
| **Caturra** | `Caturra`, `Cattura`, `Catiurra`, `Dwarf Caturra` |
| **Catuai** | `Catuai`, `Catuaí`, `catuai`, `Catuai Amarillo` |
| **Geisha** | `Geisha`, `Gesha`, `GEISHA`, `Giesha`, `Geisha/Gesha`, `Panama Gesha` |
| **SL28** | `SL28`, `SL-28`, `SL 28`, `sl28` |
| **SL34** | `SL34`, `SL-34`, `SL 34` |
| **Pacamara** | `Pacamara`, `Yellow Pacamara`, `Red Pacamara` |
| **Mundo Novo** | `Mundo Novo`, `Mondo Novo`, `Mundo Nuvo` |
| **Castillo** | `Castillo`, `Castle`, `Castillo Naranjal` |
| **Maragogipe** | `Maragogipe`, `Maragogype`, `Yellow Maragogype`, `Red Maragogipe` |
| **Pink Bourbon** | `PINK BOURBON`, `Pink Bourbon`, `Rosado`, `Borbón Rosado` |
| **Bourbon Ají** | `AJI B`, `Bourbon Ají`, `Aji`, `Ají`, `Aji Bourbon`, `Bourbon Aji` |
| **Bourbon Sidra** | `Bourbon Cider`, `Bourbon Cidra`, `Bourbon Sidra` |
| **Bourbon Pimienta** | `BOURBON PIMIENTA`, `Bourbon Pimenta`, `Pimienta` |
| **Ethiopian Heirloom** | `Heirloom`, `HEIRLOOM`, `Ethiopian Heirloom` |
| **Ethiopian Landrace** | `Ethiopia Landrace`, `Ethiopian Varieties`, `Local Landrace`, `Landraces` |
| **JARC selections** | `74110`, `74112`, `74158`, `JARC 74110`, `JARC 74112` |
| **Kurume** | `Kurume`, `kurume` |
| **Wolisho** | `Wolisho`, `Welisho` |
| **Batian** | `Batian`, `Batan`, `Batain` |
| **Ruiru 11** | `Ruiru 11`, `Riuru 11`, `Ruiru11`, `Ruiri 11` |
| **Chiroso** | `Chiroso`, `Bourbon Chiroso` |
| **Ombligon** | `Ombligon`, `Ombligón`, `OMBLIGON`, `Obligon` |
| **Laurina** | `Laurina`, `Laurina - Bourbon Pointu` |
| **Papayo** | `Papayo`, `Bourbon Papayo`, `Yellow Papayo` |
| **Sudan Rume** | `Sudan Rume`, `Sudanrume`, `Sudán Rumé` |
| **Wush Wush** | `Wush Wush`, `Wush wush` |
| **Tabi** | `Tabi`, `Tabi Amarillon` |
| **Villa Sarchi** | `Villa Sarchi`, `Villa Sachi`, `Villasarchi` |
| **Marsellesa** | `Marsellesa`, `Marasellesa`, `Marshell`, `Marshel` |
| **Java** | `Java`, `Java, USDA` |
| **CGLE17** | `CGLE-17`, `CGLE17`, `CGLE-17 (Hybrid of Geisha and Caturra)` |
| **Typica Mejorado** | `Arabica Typica Mejorada`, `Typica Mejorado`, `Mejorada`, `Mejorado` |

### Compound Splitting

Entries with multiple varietals are flagged `is_compound: true` with a `separator` field (`,`, `&`, `+`, `/`, `and`, `x`). The `ensure_compound_split` model validator catches cases where the LLM detects a separator but returns a single string — it auto-splits the string at the separator.

### Reference: `coffee_varietals.json` (100 entries)

Static reference sourced from [World Coffee Research](https://varieties.worldcoffeeresearch.org/). Each entry has `name`, `description`, `link`, and `species`.

| Category | Varietals |
|---|---|
| **Typica lineage** | Typica, Yellow Typica, Purple Leaf Typica, Maragogipe, Red/Yellow Maragogipe, Pacamara, Yellow/Red Pacamara, Pache, Villa Sarchi, Pluma Hidalgo |
| **Bourbon lineage** | Bourbon, Bourbon Mayaguez 139/71, Tekisic, Harar Rwanda, Mibirizi, Jackson 2/1257, Nyasaland, Caturra, Pacas, Catuai, Mundo Novo, Obata (Red) |
| **Catimor / Sarchimor** | Catimor 129, Catisic, Costa Rica 95, IHCAFE 90, Lempira, Marsellesa, Parainema, Paraiso, T5175, T5296, T8667, Cuscatleco |
| **F1 Hybrids** | Centroamericano, Casiopea, EC15, H3, Milenio, Mundo Maya, Starmaya, Evaluna, Esperanza |
| **SL selections (Kenya)** | SL28, SL34, SL14, K7, Batian, Ruiru 11 |
| **Indian selections** | S795, S4808, Sln.5B, Sln.6, Kartika 1 |
| **Java / other Arabica** | Java, AB3, BPL10, Anacafe 14, Caripe, Monte Claro, Fronton, Limani, Nayarita, Oro Azteca, Venecia, Peredenia |
| **Brazilian Arabica** | Catigua MG2, IAPAR 59, IPR 103, IPR 107 |
| **Robusta** | BP 534/936/939, BRS 1216–3220 (11 varieties), INIFAP 00-24/00-28/95-9/97-14/97-15, NARO-Kituza Robusta 1–10, Nemaya, Sln.1R/2R/3R, TR11/TR4/TR9, TRS1, Xanh lun, SA 237, Roubi 1–10 |

### How It Works (`ai/varietal_categorizer.py`)

The `VarietalCategorizer` uses three PydanticAI agents (all `gemini-3.5-flash`):

1. **Categorization agent** — System prompt injects the full `coffee_varietals.json` reference list. Rules:
   - Map to canonical names from the reference. Standardise spelling (`Geisha`→`Gesha`, `Cattura`→`Caturra`). Remove diacritics (`Catuaí`→`Catuai`). Standardise translations (`Bourbon Rosado`→`Pink Bourbon`).
   - Field blends and generic groups (`Mixed`, `Varios`, `Local Landraces`) → `Field Blend`.
   - Compound varietals → split with `is_compound=True` and separator.
   - Confidence: 1.0 exact match, 0.9 accent removal, 0.8 compound split, <0.7 uncertain.

2. **Merge agent** — Finds canonical names that are the same varietal (language/spelling/formatting variations). Does NOT merge distinct colours (Red Bourbon ≠ Yellow Bourbon), distinct codes (74110 ≠ 74112), or hybrids vs parents.

3. **Conflict resolution agent** — Verifies whether originals mapped to the same canonical are truly synonyms. If rejected, reverts each original to map to itself with confidence 0.5.

---

## Tasting Note Mappings

### Taste Lexicon (`taste_lexicon.json`)

Three-tier flavour taxonomy. The `TastingNoteCategorizer` loads this lexicon and injects it into the LLM system prompt.

| Primary Category | Secondary (if any) | Sample Flavours |
|---|---|---|
| **Taste Basics** | — | Sweet, Sour, Bitter, Salty |
| **Fruity** | Fruity | Dark Fruit, Gummy Candy, Jam, Plum, Purple Fruit, Tropical Fruit, Yellow Fruit |
| **Fruity** | Berry | Blackberry, Blackcurrant, Blueberry, Boysenberry, Cranberry, Gooseberry, Raspberry, Red Berry, Redcurrant, Strawberry |
| **Fruity** | Dried Fruit | Date, Dried Berry, Fig, Prune, Raisin |
| **Fruity** | Other Fruit | Apple, Apricot, Banana, Cherry, Coconut, Grape, Guava, Honeydew Melon, Kiwi, Lychee, Mango, Melon, Passion Fruit, Peach, Pear, Persimmon, Pineapple, Pomegranate, Stone Fruit, Watermelon |
| **Fruity** | Citrus Fruit | Bergamot, Grapefruit, Lemon, Lime, Orange, Pomelo, Yuzu |
| **Sour/Acid** | — | Sour Aromatics, Acetic Acid, Citric Acid, Malic Acid, Butyric Acid, Isovaleric Acid |
| **Alcohol/Fermented** | — | Alcohol, Whiskey, Winey, Fermented, Overripe/Near Fermented |
| **Green/Vegetative** | — | Olive Oil, Raw, Under-ripe, Peapod, Green, Fresh, Vegetative, Hay-like, Herb-like, Beany |
| **Stale/Papery** | — | Stale, Papery, Cardboard |
| **Earthy** | — | Woody, Musty/Earthy, Musty/Dusty, Moldy/Damp, Phenolic, Animalic, Meaty/Brothy |
| **Chemical** | — | Medicinal, Rubber, Petroleum, Skunky |
| **Roasted** | — | Tobacco, Pipe Tobacco, Acrid, Ashy, Burnt, Smoky, Roasted, Brown Roast |
| **Cereal** | — | Grain, Malt |
| **Spices** | — | Pungent, Pepper, Anise, Nutmeg, Brown Spice, Cinnamon, Clove |
| **Nutty** | — | Nutty, Almond, Hazelnut, Peanuts |
| **Cocoa** | — | Chocolate, Cocoa, Dark Chocolate |
| **Sweet** | — | Molasses, Maple Syrup, Brown Sugar, Caramelized, Honey, Vanilla, Vanillin, Sweet Aromatics, Overall Sweet |
| **Floral** | — | Floral, Rose, Jasmine, Chamomile, Black Tea |
| **Amplitude** | — | Overall Impact, Blended, Longevity, Body/Fullness |
| **Mouthfeel** | — | Mouth Drying, Thickness, Metallic, Oily |

### Categorised Tasting Notes (`tasting_notes_categorized.csv`)

~2,700 rows. Each row: `tasting_note`, `primary_category`, `secondary_category`, `tertiary_category`, `confidence`.

| tasting_note | primary | secondary | tertiary | confidence |
|---|---|---|---|---|
| Dark Chocolate | Cocoa | Cocoa | Dark Chocolate | 1.0 |
| Blueberry | Fruity | Berry | Blueberry | 1.0 |
| A Hint Of Lemon | Fruity | Citrus Fruit | Lemon | 0.95 |
| Brown Sugar | Sweet | | | 1.0 |
| Jasmine | Floral | | | 0.95 |
| Fresa (Spanish) | Fruity | Berry | Strawberry | 0.95 |
| 1850 M | None | None | None | 0.0 |

Includes foreign-language terms (Spanish `Alméndras`, `Cítricos`, `Fresa`), compound descriptions (`A Hint Of Lemon`), and non-flavour entries (`Altitude: 2170 M`, farm names) flagged with `None` categories and confidence 0.0.

### How It Works (`ai/tasting_note_categorizer.py`)

Three PydanticAI agents (all `gemini-3.5-flash`):

1. **Categorization agent** — Assigns primary/secondary/tertiary categories from the lexicon. Enforces strict hierarchy: tertiary requires secondary. Handles synonyms and translations (`Fresa`→`Strawberry`, `choc`→`Chocolate`).

2. **Naming agent** — Extracts canonical flavour words for lexicon expansion. If a word appears ≥3 times and isn't in the lexicon, it's added as a new tertiary flavour.

3. **Non-flavour check agent** — Flags non-flavour entries (product names, locations, marketing phrases, altitude values). Non-flavours are marked `primary_category="None"` with confidence 0.0.

---

## Farm Mappings

**File**: `src/kissaten/database/farm_mappings.json` (~89K)

### Structure

```json
{
  "country": "CO",
  "region": "",
  "canonical_farm_name": "Finca El Placer",
  "normalized_farm_names": ["el-placer", "el-placer-farms", "finca-el-placer"]
}
```

### Example Mappings

| Country | Canonical Farm Name | Normalised Aliases |
|---|---|---|
| CO | El Obraje | `el-obraje`, `hacienda-el-obraje` |
| CO | Finca El Placer | `el-placer`, `el-placer-farms`, `finca-el-placer` |
| CO | Finca La Negrita | `finca-la-negrita`, `la-negrita` |
| CO | Paraiso 92 | `paraiso-92` |
| CO | Granja Paraiso 92 | `granja-paraiso-92` |
| CO | Cafe Granja La Esperanza | `cafe-granja-la-esperanza` |
| CO | Diego Samuel Bermudez | `diego-bermudez` |
| CO | Wilder Lazo | `wilder-lazo` |
| CO | Nestor Lasso | `nestor-lasso` |

Primarily covers Colombia (CO), with entries also for Guatemala (GT), Honduras (HN), Peru (PE), Ethiopia (ET), and Kenya (KE). Special sentinel entries: `"Mixed"`, `"Various"`, `"Unknown"`, `"N/A"`, `"Null"`.

---

## Region Mappings

**Directory**: `src/kissaten/database/region_mappings/` (48 country files)

Each file (e.g. `ET.json`, `CO.json`) maps raw region names to canonical administrative regions with geocoded data.

### Structure (example from `ET.json` — Ethiopia)

```json
{
  "Yirgacheffe": {
    "canonical_state": "South Ethiopia Regional State",
    "confidence": 0.9,
    "reasoning": "...",
    "iso_3166_1_alpha_2": "ET",
    "iso_3166_1_alpha_3": "ETH",
    "iso_3166_2": null,
    "_category": "outdoors/recreation",
    "_type": "pitch",
    "state": "South Ethiopia Regional State",
    "state_district": "Gedeo",
    "town": "Yirga Cheffe",
    "bounds": { "northeast": {"lat": ..., "lng": ...}, "southwest": {"lat": ..., "lng": ...} },
    "geometry": { "lat": ..., "lng": ... }
  },
  "Sidamo": {
    "canonical_state": "Sidama",
    "confidence": 0.8,
    "iso_3166_2": "ET-SI"
  }
}
```

### Coffee-Producing Countries Covered

Largest files by entry count: Colombia (274KB), Ethiopia (164KB), Peru (115KB), Panama (108KB), Brazil (95KB), Kenya (63KB), Costa Rica (61KB), Rwanda (56KB), Guatemala (57KB), Honduras (44KB), Indonesia (45KB), India (46KB), Ecuador (47KB), El Salvador (45KB).

Historical/colloquial names are mapped to current administrative regions (e.g. `Sidamo` → `Sidama`, `Yirgacheffe` → `South Ethiopia Regional State`).

### How It Works (`ai/region_selector.py`)

The `RegionSelector` (Gemini 2.5 Flash Lite, `thinking_budget=0`) selects the best OpenCage geocoding result for a raw region name. Selection criteria in priority order:

1. **Administrative level** — Prefer state/province level, not districts or towns.
2. **Elevation match** — Coffee regions typically 800–2500m.
3. **OpenCage confidence score** — Prefer higher.
4. **Component completeness** — More admin components = more precise.
5. **Geographical accuracy** — Consider bounds and context.
6. **Name clarity** — Prefer disambiguated results.
7. **Coffee-growing relevance** — Prefer rural, coffee-producing areas.

Returns `None` for invalid regions (low confidence, wrong country, urban area, country name itself, typos).

---

## Geographic Reference Files

### `countrycodes.csv` (249 rows)

Standard ISO 3166-1 reference: `name, alpha-2, alpha-3, country-code, iso_3166-2, region, sub-region, intermediate-region, region-code, sub-region-code, intermediate-region-code`.

### `roaster_location_codes.csv` (49 rows)

Curated roaster location → region code mapping. Uses ISO 3166-1 alpha-2 for countries plus pseudo-codes for continents:

| Pseudo-Code | Region |
|---|---|
| `XA` | Asia |
| `XF` | Africa |
| `XE` | Europe |
| `XN` | North America |
| `XO` | Oceania |
| `XS` | South America |
| `EU` | European Union |

---

## Validation Gate

**File**: `src/kissaten/ai/validation_gate.py`

Enforces integrity of `processing_methods_mappings.json` and `varietal_mappings.json`:

1. **One canonical mapping per `original_name`** — No duplicate `original_name` entries (detected case-insensitively, matching the database's `LOWER()` join behaviour).
2. **Conflict vs redundant**:
   - **Conflict**: Same lowercased `original_name` maps to different canonical values. Dangerous — lookup is non-deterministic.
   - **Redundant**: Same lowercased `original_name` maps to the same canonical value. Harmless but dead weight.
3. **`allow_redundant` flag**: When `True`, redundant duplicates are filtered. Used in production loading paths. CLI `validate-mappings` uses strict mode (`False`).
4. **`raise_on_error` flag**: When `True` (default), raises `MappingValidationError`. When `False`, prints a warning.
5. **Missing file is not an error**: Returns empty list if the file doesn't exist yet.

---

## DuckDB Tables for Mappings

| Table | Purpose |
|---|---|
| `varietal_mappings` | Raw → canonical varietal name mappings (loaded from JSON) |
| `coffee_varietals` | Canonical varietal reference data (from `coffee_varietals.json`) |
| `tasting_notes_categories` | Three-tier tasting note classification (from CSV) |
| `origins` | Geographical hierarchy (country, region, farm, coordinates) |
| `country_codes` | ISO 3166 country code reference (from `countrycodes.csv`) |
| `roaster_location_codes` | Roaster location → macro-region mapping |

---

## Updating Mappings

To regenerate mappings from scratch or add new entries:

```bash
# Processing methods
uv run python -m kissaten.ai.processing_method_categorizer

# Varietals
uv run python -m kissaten.ai.varietal_categorizer

# Tasting notes
uv run python -m kissaten.ai.tasting_note_categorizer

# Validate both mapping files
uv run python -m kissaten.cli.main validate-mappings
```

Each categorizer queries DuckDB for unique raw names, batches them to the LLM, detects conflicts, resolves them, and writes the updated JSON. The validation gate runs as a post-flight check to ensure no duplicate or conflicting entries remain.
