# Review of `deep-dive.md` — Issues, Corrections, and Verification Log

**Date:** 2026-09-19
**Scope:** Full read of the 631-line report; every claim sourced from the local `podcast_data/` and `blog_data/` corpora checked against the actual transcripts/articles; externally-sourced regulatory and market-data claims checked against current web sources (USDA FAS GAIN, EUR-Lex, Kenya Law, Conab, Cecafé, Coffee Board of India, trade press).
**Overall verdict:** The argument is cohesive and ~90% of the factual apparatus verifies. Zero fabrications were found. The problems below are a punch-list, not a rewrite: one probable legal-instrument misidentification, one internal arithmetic contradiction, one outright factual error, a systematic embellishment pattern, unreliable timestamp citations, and a set of single-source statistics stated with too much confidence.

Issue entries reference line numbers in `deep-dive.md` and its footnote numbers (`[^n]`).

---

## 1. Confirmed or probable errors (fix first)

### 1.1 Ethiopia — "Directive No. 433/2019" is probably the wrong instrument (load-bearing)
- **Where:** lines 7, 20, 231–232, 244–246; footnotes [^9], [^10].
- **Problem:** The report repeatedly attributes the dismantling of mandatory ECX routing and the creation of direct-export/vertical-integration pathways to "Directive No. 433/2019" of the Council of Ministers. External verification indicates **Council of Ministers Regulation No. 433/2019 is the instrument that established/reorganized the Ethiopian Coffee and Tea Authority (ECTA)** — not the coffee-marketing/export reform directive. The direct-export reform is real, but it appears to rest on a different instrument (the Cafe Imports source [^27] itself refers only to "a 2017 proclamation (and a 2019 roll-out)" and never names 433/2019).
- **Action:** Check the primary Ethiopian legal text; re-cite the actual export-reform directive/proclamation, or reword to attribute the reform to "ECTA-era export reforms (2017 proclamation, 2019 implementation)".

### 1.2 Vietnam — "+143%" is arithmetically inconsistent with the figures quoted
- **Where:** line 434 (also echoed in exec summary line 10).
- **Problem:** "Average export prices rose from US$3,792/tonne in the 2023–24 crop to US$5,630/tonne in the first half of 2024/25 (+143%)". $3,792 → $5,630 is **+48.5%**, not +143%. The 143% is presumably a year-on-year half-crop comparison from USDA VM2025-0018 misattached to the two absolute figures.
- **Action:** Either drop the parenthetical or restate the comparison basis (e.g., "H1 2024/25 up ~143% year-on-year").

### 1.3 Brazil — "southeastern Minas" contradicts the cited source
- **Where:** line 183 (CAR reserve minimums, cited to [^70], Ep 67).
- **Problem:** The transcript locates Fazenda Mió (Monte Santo de Minas) in the **southwestern** region of Minas Gerais; the report says "southeastern Minas".
- **Action:** Correct to "southern/southwestern Minas" (the 20% reserve figure itself is confirmed).

### 1.4 Brazil — "$3.35/lb on 29 November 2024" date-price pairing unreliable
- **Where:** line 195, footnote [^105].
- **Problem:** That session's arabica high was closer to **$3.20–3.25/lb** (Reuters, 29 Nov 2024); $3.35/lb appears to belong to a different session/contract. "Highest since 1977" is fine.
- **Action:** Re-verify against ICE settlement data and correct the pairing.

### 1.5 India — CY2024 export value contested across series
- **Where:** line 390, footnote [^126].
- **Problem:** The report's "403,478 tonnes worth about $1.68 billion in calendar 2024 (+45% by value)" matches the cited Hindu BusinessLine piece, but other series put 2024 export value closer to **$1.3 billion** — likely a calendar-vs-fiscal-year confusion (FY2024-25 values are higher).
- **Action:** Keep the figure but state the period basis explicitly (CY2024, Coffee Board data) and note the discrepancy.

### 1.6 Brazil — Conab 2026 range and yield figure inconsistent
- **Where:** line 181, footnote [^93].
- **Problem:** "record 66–72 million bag crop expected in 2026 on 2.34 million hectares": the 72M upper bound is not substantiated as a Conab point estimate (Conab ≈66.2–66.7M), and 34.4 bags/ha is inconsistent with the stated area/production totals.
- **Action:** Use the Conab point estimate (~66.2–66.7M bags) and drop or source the 72M figure.

### 1.7 Brazil — Funcafé figure has a probable currency-unit problem
- **Where:** line 195, footnote [^92].
- **Problem:** "the Funcafé credit line distributed $1.17 billion for 2024/25" — external checks indicate ~R$5.9 billion was made *available* for 2024/25, with ~R$1.17 billion reported *disbursed/contracted* at the relevant point. The report likely conflates R$ with US$ and "available" with "distributed".
- **Action:** Verify against the USDA GAIN Brazil 2025/26 annual and state currency + basis.

---

## 2. Internal inconsistencies / cohesion defects

### 2.1 Ethiopia farmgate share: 55–65% vs 14–38% unreconciled
- **Where:** value table lines 235–240 (farmgate cherry seller 55–65% of FOB) vs line 250 and the actor matrix line 43 ("farmers are estimated to receive only 14–38% of export price over the past fifteen years" [^48]).
- **Problem:** The two figures sit side by side with no explicit reconciliation (different streams/eras: vertically-integrated-stream estimate vs 15-year all-channel average).
- **Action:** Add one clarifying sentence in either location stating which stream/era each figure describes.

### 2.2 Kenya — duplicated sentence and confusing Act dating
- **Where:** line 271 ("traditional commercial marketing agents were replaced by licensed brokers… They were replaced by CMA-licensed independent coffee brokers" — redundant); line 272 ("The Coffee Act 2023 (enacted March 2026)").
- **Note:** The dating is technically defensible — Senate Bill No. 10 of 2023 was assented 27 March 2026 as **Coffee Act No. 8 of 2026** (Kenya Law) — but as written it reads like an error.
- **Action:** Delete the duplicated sentence; reword to "the Coffee Act (Senate Bill 2023, enacted as Act No. 8 of 2026)".

### 2.3 Footnote [^21] orphan
- **Where:** works cited (lines 484+); "Additional sources consulted" (line 631).
- **Problem:** Numbering skips 21 in both text and works cited; a lone "> 21. Dissertation – eDiss" entry survives under "Additional sources consulted" — a renumbering artifact.
- **Action:** Either reintegrate the dissertation as footnote [^21] with an in-text citation, or delete the orphan entry.

### 2.4 Country ordering differs across the three tables/sections
- **Where:** comparative matrix (lines 17–27: Col, Per, Eth, Ken, Rwa, Gua, Bra, Ind, India, Viet), actor table (lines 37–44: Col, Per, Eth, Ken, Rwa, Indon, Gua, Bra, India, Viet), deep-dive order (Col, Per, Gua, Bra, Eth, Ken, Rwa, Indon, India, Viet).
- **Action:** Cosmetic; align on one order (the deep-dive order reads best).

### 2.5 Two-wave assembly seams
- **Where:** exec summary (lines 5, 10) and conclusions (line 480) both narrate "the four origins added to this analysis/report".
- **Note:** Transparent rather than wrong, but if the report is meant to stand as a single document, these meta-references could be smoothed.

---

## 3. Claims not found in the cited local sources (re-source or delete)

Verified against `podcast_data/` and `blog_data/`. "Not in source" = the substance could not be located anywhere in the cited episode/article.

| # | Where in report | Claim | Cited source | Finding |
|---|---|---|---|---|
| 3.1 | line 214 | Growers from Guatemala to Peru price against "what Brazil is doing" | [^26] Feran, *The Cost of Quality, Revisited* | **Absent from the entire local corpus.** Re-source or delete. |
| 3.2 | lines 31, 38 (actor terminology framing) | Farmer/producer definitions "articulated by Alejandro Cadena (Caravela) and Kenean Dukamo (Daye Bensa)" | [^38] PDG, *Coffee farmer vs. producer* | **Cited article is not in `blog_data/` at all** — the framing section rests on an unverifiable citation. Obtain the article or re-source. |
| 3.3 | line 183 | CAR / "Cadastro Ambiental Rural" name + perimeter-declaration mechanism | [^70] Ep 67 | Reserve percentages confirmed, but the episode **never names CAR** or the perimeter mechanism. Add a CAR source (e.g., [^116] covers it) and decouple from [^70]. |
| 3.4 | line 183 | Pickers "paid per *caixa*" | [^70] Ep 67 | "Caixa" never appears in the episode. Re-source (CEPEA per-caixa benchmarking at line 193 is separately cited to [^103]). |
| 3.5 | line 187 | "Virtually all arabica is prepared as natural or *pulped natural* (*descascado*)" | [^70]/[^91] | "Descascado"/"pulped" never said in Ep 67; rely on [^91] (Wikipedia) or add a source. |
| 3.6 | line 187 | Wet mills re-sort cherry "by weight, Brix, and **color**" | [^70] Ep 67 | Weight and Brix confirmed; "color" not in the episode. |
| 3.7 | line 390 | "chicory-blended South Indian filter-coffee tradition… never quality-driven" | [^120] Ep 56 | "Chicory" appears **zero times** in Ep 56 (and Eps 34/62). The volume/quality framing exists elsewhere; re-source the chicory characterization. |
| 3.8 | line 226 | Naturals dried "on raised bamboo beds (*jenfel*)" | [^27] Cafe Imports Ethiopia | No mention of jenfel/bamboo/raised beds in that article. Re-source. |
| 3.9 | line 68 | "the *contribución cafetera*" (name) | [^26] Feran | The 6% export levy is confirmed; the Spanish name is not in the source. Minor — the name is externally standard, but add a source. |
| 3.10 | line 402 | CCRI "bred Kent, S.795, Selection 9, and Chandragiri"; "unromantic" numbering | [^122] Thipaiah guest post | Kent and S.795 never named (only "S9"); CCRI described as having "identified" cultivars; "unromantic" is from Ep 56 [^120], not [^122]. Split the citation. |
| 3.11 | line 206 | Daterra "founder admitted most volume is ordinary"; "pioneered mechanized quality separation" | [^110] Ep 14 | The "most of the coffee is not that good" judgment is **George Howell's**, not the founder's admission; no mechanization/pioneering claim in the episode. Reword attribution. |
| 3.12 | line 272 | Kenya growers "reliant on informal credit" | [^30] TW Ep 34 | The episode says only that farmers "need some access to finance"; credit/informal lenders never mentioned. Soften or re-source. |
| 3.13 | lines 8, 466 | "many 'direct trade' claims are overstated" attached to [^32] | [^32] TW Ep 47 (Benjamin Paz) | Paz documents intermediaries' real functions (QC, financing, matching) but never says direct-trade claims are overstated — that element is the report's inference. Keep the functions claim; attribute the "overstated" claim to [^25]/[^33] (which do support it). |
| 3.14 | line 231 | ECX reforms "publishing pre-trade lot information by region and process" | [^27] Cafe Imports Ethiopia | Article supports commingling/traceability loss but contains no "publishing pre-trade lot information" content. Re-source. |
| 3.15 | line 23 / 136 | "remittances worth an estimated 15 percent of GDP in 2024" | [^70] Ep 67 | The episode says "about 15% of the country's economy" — confirmed — but note it is a spoken practitioner estimate, not a 2024-dated statistic. Attribute as such. |
| 3.16 | line 447 | "specialty cups US$2.50–10 against a US$1 street *cà phê sữa đá*" | [^132] Ep 57 | Prices confirmed; the drink is described as "daily iced coffee with condensed milk" — the name *cà phê sữa đá* is never used. Cosmetic. |
| 3.17 | line 384 | "monsoon climate" / "harvest-time thunderstorms" framing split across [^115] and [^124] | Eps 34/62 | "Monsoon" never said in Ep 34 (word used is "thunderstorms"); Ep 62 says "rains". Cherry-splitting and semi-wash content both confirmed, but the weather vocabulary is the report's. |

---

## 4. Hedged or second-hand material stated as firm fact

- **Line 206 [^109] (TW Ep 30):** CoE 1999 "Best of Brazil" details (11 lots, Solberg & Hansen bought 7, $2.50–3.00/lb) are all hedged in the source ("I think", "if I don't remember wrong", "maybe"). Content matches; add "as recalled by" framing or corroborate.
- **Line 173 [^89] (TW Ep 36):** José Morales's "125 kilos of cherry… the bag looks half full" is similarly hedged ("let's say… I don't remember").
- **Line 214 / line 10:** the 78–85% Brazil farmgate-capture estimate is the report's own directional estimate — it is labeled as such in the Brazil table (line 195) but stated more flatly in the exec summary (line 10) and conclusions (line 480). Keep the "estimated here" qualifier everywhere.
- **Line 167:** ANACAFÉ's "close to 99 percent of coffee acreage verified deforestation-free" is a **self-reported ANACAFÉ claim** — say so (the 136,000-site ANATEC/GIS figure is USDA-reported and fine).
- **Line 136:** ACODIHUE "roughly 80 percent of member coffee grown by indigenous, largely Mam-speaking women" is an organizational/marketing estimate, not a verified sector statistic — attribute it.

---

## 5. Single-source or unverifiable statistics stated too flatly

These are mostly *attributed in the works cited* but stated in the text without flagging their evidentiary basis. External verification could not independently confirm them; each should carry "estimated/reported by X" framing or gain a second source.

| # | Where | Claim | Status |
|---|---|---|---|
| 5.1 | line 195, [^106] | "$7 billion in margin calls in a single month" (Brazil, late 2024) | Bloomberg-syndicated press estimate; no primary substantiation. Keep only as attributed press figure. |
| 5.2 | line 290, [^53] | Kenya: 15 CMA-licensed brokers; top five handle ~80% of NCE volumes | Unverified against CMA/NCE lists. |
| 5.3 | line 290, [^54] | Kenya: exchange-side fees capped at 1.8% of gross sale value | Unverified against the CMA (Coffee Exchange) (Fees) Regulations 2025 text. |
| 5.4 | line 272 | Stanbic Bank Kenya approved as additional DSS provider in 2026 | Unverified against CMA/CBK notice. |
| 5.5 | line 292, [^55] | 2026 pledge: five-day payment with ≥80% of each sale to the farmer | Verify against the actual reform instrument; present as pledge, not rule. |
| 5.6 | line 26 / 390, [^118] | India: top-20 exporters control ~86% of exports | From the 2019 *Economic Affairs* article; not publicly auditable. Label as 2019 study estimate. |
| 5.7 | line 329, [^56] | Rwanda: six firms controlled ~70% of exports; RTC/Westrock 33 stations, Rwacof/Sucafina 30 | Company-reported/undated; label with source and date. |
| 5.8 | line 128, [^47] | Peru: top-10 exporters ≈45% of export value | Single trade-press (Agronline/ADEX) figure; add date. |
| 5.9 | line 128, [^46] | Peru: cooperatives defaulted on ~100,000 bags in 2024 | StoneX estimate via Algrano; attribute explicitly. |
| 5.10 | line 250, [^48] | Ethiopia: farmers received 14–38% of export price over 15 years; >500 exporters vs <50 | HKS student-policy-analysis study; fine as cited, but flag as study-specific (and see 2.1). |
| 5.11 | line 329, [^57] | Rwanda: US$36M sector working capital (TechnoServe, undated); co-ops borrow at up to 24%; ICO ~25% farmer margin vs ~10% CWS | Undated/contested — the report itself notes the contest; keep that framing. |
| 5.12 | line 24 / 418, [^135] | Vietnam "over 40% of the world's robusta" vs [^139] "42%" | Both fine as estimates; align on one phrasing. |
| 5.13 | line 24 / 189 | "Cooxupé alone controls the largest share of arabica exports" / "world's largest coffee cooperative… 22,000+ members" | Broadly supported; membership counts vary by year (18,000+ in 2022 SCS study vs 22,000+ in 2026 Cooxupé release) — the report already uses the 2026 figure, fine. |
| 5.14 | line 402 | Kerehaklu "exporting about 55% of production to North America by 2023" | Confirmed in Ep 56 — but it is one estate's account; the report already frames it as illustrative. OK. |
| 5.15 | line 68 | "in 2024 a producer selling through the FNC stood to profit roughly $0.35/lb versus about $0.53/lb through a private exporter" | Confirmed verbatim in [^26] — but it is a June-2024 point-in-time figure from one analyst; the report's year-stamping convention covers this. OK. |

---

## 6. Timestamp citations to re-anchor (podcast sources)

Roughly half the mm:ss ranges point to chunk/segment starts or generic show intros rather than the actual content. Substance was verified for all of these; only the anchors are wrong. Fix if the report's citations are meant to be followed.

| Citation | Cited range | Actual content location |
|---|---|---|
| [^68] Ep 73 (Guatemala civil war / 40% Maya / 2.5-month harvest) | 00:08–00:19 | ~10:01–10:41 and ~34:19 |
| [^70] Ep 67 ("in Guatemala it's not very common" dry mills) | 07:28–08:00 | ~09:44–09:50 |
| [^70] Ep 67 (remesa 15%) | 36:29–37:10 | ~37:46 |
| [^70] Ep 67 (ANACAFÉ conference ~50% Brazilian researchers) | 36:29–37:10 | ~47:31–47:39 |
| [^73] Ep 54 ("entire towns where there's just only women") | 45:38–46:10 | ~48:56 |
| [^81] Ep 69 (FTC camps / 100% open patios / Dec–Apr dry season) | 05:03–06:00 | ~06:21–07:25 |
| [^80] Ep 14 (Raúl / Finca La Soledad) | 00:00–00:30 | ~02:55 |
| [^109] TW Ep 30 (CoE 1999 Best of Brazil) | 32:05–48:06 | 40:06–48:06 |
| [^104] TW Ep 35 (ECOM trainee / Capricornio / Fazenda California) | 10:24–21:45 | 01:30–02:47 |
| [^88] TW Ep 33 (Cobán microorganism farm visit) | 45:00–70:00 | ~71:43–71:46 |
| [^89] TW Ep 36 (Morales cherry-density quote) | 52:10–53:30 | ~54:45–55:10 |
| [^115] Ep 34 (65–70° slopes; third-round strip/green-only) | 00:43–00:48 | 37:05–42:25 |
| [^115] Ep 34 (mechanical drying) | 00:28–00:37 | ~28:05–28:20+ |
| [^120] Ep 56 (all four cited ranges) | 00:17–00:28, 00:28–00:33, 01:10–01:12, 01:13–01:17 | intro-only; content at 07:07–77:27 (estate labor ~70:30–72:25; domestic→55% export ~28:07–30:45; variety names ~07:07–10:46 and 73:22–77:27) |
| [^124] Ep 62 (cherry splitting; semi-wash) | 00:17–00:28, 01:18–01:24 | 17:30–28:08 and 78:25–84:08 |
| [^139] Ep 52 (carbonic-maceration harshness/mucilage mechanism) | 04:46–08:49 | ~75:29–77:05 (the 42%/31M-bags figure *is* nearby at 07:25–08:48) |
| [^132] Ep 57 ("add to, not replace" culture; $1 street coffee) | 00:00–06:02, 23:27–31:53 | ~10:14–10:19 and ~17:45–23:26 (in uncited gaps) |

---

## 7. Smaller wording/qualification fixes

- **Line 44 (actor matrix):** "None since ETK abolition (2021)" for Indonesia's regulatory gatekeeper — directionally right, but NIB/OSS licensing and ICO certificates of origin are complementary requirements, not strict substitutes for ETK. Slight rewording recommended.
- **Line 146:** USDA's "unnecessary additional trade barrier" — attribute the adjective to USDA explicitly (the report does quote it; keep the quote marks).
- **Line 171:** "C price touched $0.86/lb — down roughly 60 percent from its 2015 level" — $2.20/lb was a 2015 *high*, not the representative average; note the basis.
- **Line 128:** "the world's largest Fairtrade/organic arabica producer" (Peru) — too broad unqualified; tie to a certification/export category.
- **Line 404:** "world's largest tribal coffee cooperative" (Araku/SAMTFMACS) — promotional superlative; attribute it.
- **Line 82:** SICA "contains polygon mapping and structural data for nearly every coffee farm nationwide" — needs a current coverage figure or "near-universal coverage (per FNC)" framing.
- **Line 388:** "Coffee Act VII of 1942" — conventionally cited as the Coffee Act, 1942; the 1993/1994 quota percentages (30% / 70–100%) vary across accounts — note the basis.
- **Line 136:** "Decree 177" and the 1871–77 compression — distinguish the individual 1870s instruments if precision matters.
- **Line 462–470 (commodity-vs-specialty table):** "Low-to-moderate farmgate FOB share (50–65%)" for commodity — inconsistent with the report's own origin tables for Colombia (75–82%), Brazil (78–85%), India (70–80%), Vietnam (70–80%). Reconcile or qualify as "multi-tier intermediary chains".
- **Line 418:** "an estimated four to five million mostly Kinh settlers into the Central Highlands after 1975" — externally plausible but sourced to Wikipedia [^134]; acceptable, flag as estimate (already "estimated").

---

## 8. What verified cleanly (no action needed)

So re-review effort is not duplicated, the following were checked and **verified against the cited local sources** (substance verbatim or near-verbatim):

- **Ep 67 [^70]:** Brazil ~30% of global output; 8M jobs; 330,000 properties; <5 ha–5,500 ha range; 7,000 t/yr > Panama/Bolivia output; 1,500-ha Mió layout (400 coffee/400 forest); 20–70% biome reserves; 6.1→29.1 bags/ha, 4.9→2.2M ha, 29→54.7M bags (1960–2023); Mió own wet+dry mill and UK arm opened Sept 2020; 2024 winter 30–31°C and "consistent 84 points"; vibration-tuned harvesters; wet-mill re-sort by weight/Brix; Projects Sombra (Assembly/Volcano) and Baja (Watch House), Dr. Lucas Lozada, IFES.
- **Ep 14 [^80]/[^110]:** Guatemala second CoE country; ~20 years of competitions; El Injerto concentration; Howell's 50%-domestic-consumption remark; Caturra in COE Brazil top 10; Daterra Brix rejection.
- **Ep 57 [^132]:** Frith's centrality; closed-loop market ("the best Vietnamese coffee is still in Vietnam"); $2.50–10 specialty cups; six-hour-drive arabica; "most consistent bidder"; strip-picking reputation; Đà Lạt cut-flower double wages; aging farmers / 10-year horizon / agroforestry; provenance-over-terroir.
- **Ep 52 [^139]:** Vietnam 42% of world robusta / 31M bags.
- **Ep 53 [^142]:** Finca Rosenheim micro-lots to Vietnam (first Asia shipment).
- **Ep 71 [^141]:** "better coffee for more people".
- **Ep 34 [^115]:** Kerehaklu 270 acres / 205–210 coffee / 70-30 arabica-robusta + boundary liberica; first washed robusta (2021); São Paulo fine-robusta anecdote.
- **Ep 56 [^120]:** ~100% domestic 2020–2022 → ~55% export to North America; "80 people working for you"; variety-numbering complaint (Selection 5/5B/6/9).
- **Ep 27 [^35]:** "cooperativas by name"; certify-6-hectares-sell-600 organic gaming; Peru roya collapse vs Brazil volume keeping prices down.
- **Ep 58 [^33]:** Colombia direct export "almost impossible" + FNC export services; Antigua over-selling / Honduran re-labeling across the border; direct-trade skepticism.
- **Ep 76 [^90]:** Brazil volume leader ahead of Vietnam, Indonesia, Ethiopia.
- **TW Ep 33 [^88]:** José Morales big wet mill, conventional + organic farms; Caballeros "in control… hallmark of Caballero coffee", new dry mill with color sorters; Nov 2023 tour, Benjamin Paz for Robnil.
- **TW Ep 34 [^30]:** pooled/averaged FCS payouts arriving ~April; first-payment/cherry-advance not yet functioning.
- **TW Ep 35 [^104]:** "fantastic quality in incredible volume… so much work to make a coffee that's 86".
- **TW Ep 41 [^31]:** broker/marketing-agent re-badging; 2% fee ceiling (report's "1–2%" adds an unstated lower bound).
- **TW Ep 42 [^143]:** Vietnam deforestation/land-grabbing; EUDR polygon mechanics; post-2020 cutoff.
- **Feran [^25]:** middlemen aggregation/QC/trade-financing; direct-trade critique. **[^26]:** 2018 FNC below production cost; $0.35 vs $0.53 (June 2024); 6% export levy; 1997 crash + Vietnamese/Brazilian surges. **[^114]:** Maragogipe from Bahia in Scott Labs germplasm (1930s). **[^137]:** Treaty of Saigon 1862; Réunion 1887; Borel brothers; Poilane Khe Sanh Chari; 96B excelsa since 2021; 12-m trees; Davis et al. Aug 2025 *C. dewevrei* reinstatement.
- **Cafe Imports [^27]:** 40,000+ Yirgacheffe-union producers → 3 micro-lot-capable farms; 2015–19 lapse; Lulo Coffee revival; smallholders lacking credit/infrastructure; Cafe Imports' first import 1993 single Brazilian producer. **[^28]:** Rwanda average ~1 ha. **[^29]:** Asman Gayo/Frinsa/Tuang/Karana named and located. **[^83]:** Funcafé + GRACES 2025 recipients; second-highest food insecurity.
- **PDG [^99]:** IAC/Alcides Carvalho/CATIE 1973 Fazenda Santa Elisa/AC1-3 identified 26 years later. **[^82]:** honey processing spreading (Guatemala, Vietnam, Myanmar, Peru, Uganda); robusta pulp sugar; Vietnam mild-robusta quote. **[^113]:** December 2024 drought/maturation study. **[^37]:** ~560,000 Colombian farmers (report's "500,000–560,000 families" — see 7 below, minor unit drift).
- **External:** EUDR Reg. 2025/2650 dates (30 Dec 2026 / 30 Jun 2027); Impl. Reg. 2025/1093 (22 May 2025) benchmarking — Guatemala standard-risk; low-risk = Costa Rica, India, Kenya, Rwanda, Vietnam; 3% standard-risk check rate. India 1942 Act → 1993 ISQ → 1994 FSQ → Sept 1996 pooling abolition. ANACAFÉ Decree 19-69; Fideicomiso Decree 31-2001/Banrural. Feb 2013 roya emergency (59–70% area estimates). Vietnam Decision 1392/QD-BNN-TT (19,000 ha / 11,000 t by 2030). IBC abolished 1990. Kenya Coffee Act assented 27 March 2026 (Act No. 8 of 2026); 10% FCS deduction cap present. Rwanda floor-price series 410/480/600/750 RWF consistent with NAEB announcements; zoning repeal (2016 → June 2023) consistent. Guatemala USDA figures (125,000 producers; 97%/44%; 376,000 ha; 261/340 municipalities; 81% SHB; April 2026 reference prices; $21–22 cherry; $140–160/$250 parchment; $18→$3 differential; $1.284B MY24/25; ~$994M H1-2025; 210 agents/27,500 growers; FEDECOCAGUA 1969/148/20,000/70%/33; CoE $143.10/lb; Feb 2024 ANACAFÉ–JDE Peet's–Enveritas MOU). Vietnam USDA figures (730,000 ha; 92%/90%; $3,792/t and $5,630/t levels; VND 125,000/kg +130%; −23% H1 exports; EU 41%; Germany $3,390/t; Philippines $4,424/t; MARD 136,000 ha; Simexco/EDE; 2013–14 127 firms/VND 8T/$379M/60%; 8.8%→9.6% processed). India structure (366,242 holdings; 99% <10 ha; 75%/70% vs 25%/30%; Karnataka 54%/69%; Kerala 19%/22%; 400/300 man-days; ~60% labor; ₹305 (2017–18); 80%/20% wet-processing; 50% outturn; ₹89/kg vs ₹129,850/t vs ₹164,000/t; 1.3M bags 70% soluble; +45%/+66% farmgate). Colombia (95% <5 ha; 1.5–2 ha avg; carga 125 kg FR-94; 33 co-ops). Kenya (70/30 smallholder/estate; <1 ha; 200–300 trees). Rwanda (400k households; ~300 CWS). Peru (220k families; >85% <5 ha). Ethiopia (2.2M households; >95% smallholder). Brazil 2025/26 (65M bags; 40.9/24.1; MG ≈1.22M ha; ES ≈433k ha/70%; Rondônia ≈95k ha; Atlantica/CafeBras restructuring late Nov 2024; top-5 2024 destinations US 15/DE 14/IT 7/BE 6/JP 6).

---

## 9. Recommended fix order

1. §1.1 Ethiopia directive instrument (load-bearing).
2. §2.1 Ethiopia farmgate-share reconciliation; §1.2 Vietnam +143%.
3. §1.3–1.7 factual corrections (Minas, $3.35 date, India $1.68B basis, Conab 72M, Funcafé currency).
4. §3 table — re-source or delete the 17 embellishments (especially 3.1 "what Brazil is doing" and 3.2 the missing PDG article [^38]).
5. §5 — add attribution/qualification to the 12 single-source statistics.
6. §6 — re-anchor podcast timestamps.
7. §2.2–2.4, §7 — mechanical and wording cleanup.

---

## 10. Round 2 — follow-up verification of the unsubstantiated claims (2026-09-19)

Method: four parallel web-research agents on the HTML/news/regulatory citations; primary PDFs (USDA GAIN ×6, HKS, Thünen, ICO, GCP, KAMI, EFI) downloaded and text-extracted locally; bot-protected sources (Scribd [^9], MDPI [^51], PDG [^38]) opened in a real browser. The full Scribd document was also obtained as a .docx and read end-to-end (it matches the browser extraction). Note: the Mbakop PDF (`agriculture-13-00368.pdf`) could not be read by the user's PDF tool — it was verified via the MDPI website in a browser instead.

### 10.1 Ethiopia "Directive 433/2019" — RESOLVED: faithful to its source, but the source compresses three instruments (revises §1.1)

The report's own cited source [^9] (Ermias Wodajo, *Ethiopia new coffee export procedure…*, Scribd/ResearchGate) literally states: *"The Council of Ministers promulgated a new directive No. 433/2019 and ECTA introduced coffee sale procedure in April 2020."* The report did not invent the designation. However, the same document shows the reform actually rests on a chain of instruments:

1. **Coffee Marketing and Quality Control Proclamation No. 1051/2017** — "new articles" addressing ECX's shortcomings (this matches Cafe Imports [^27]: "a 2017 proclamation (and a 2019 roll-out)", and HKS [^48]: "the 2017 Vertical Integration reforms");
2. **Council of Ministers Regulation/Directive No. 433/2019** — which re-established ECTA (elsewhere documented as the ECTA establishment regulation);
3. **ECTA's coffee sale procedure (April 2020)** — the operational vertical-integration rules; direct delivery bypassing ECX grading/weighing "began in January, 2021" with an ECTA authorization letter.

**Fix:** attribute the reform to the full chain ("Proclamation 1051/2017, implemented through ECTA's 2019–2020 coffee sale procedure"), not to "Directive No. 433/2019" alone. Severity downgraded from "probable misidentification" to "oversimplification faithful to a compressing source".

### 10.2 NEW ERROR — Ethiopia's 22% premium is attributed to the wrong grades (upgrades to §1)

- **Where:** line 232: "Export-eligible grades 1 to 4 traded via vertical integration pathways have been reported to achieve price premiums of up to 22% over base ECX floor prices".
- **What the cited source [^9] actually says:** vertical integration for **grades 1–4** is capped at **"up to 5 percent above the Premium price in the ECX"**; it was **commercial coffee (grades 5–10 plus undergrade)** that "started to be sold for **up to 22 percent** increments over the ECX premium price".
- The report inverted the grades. Ironically it hedges the claim ("a single-study estimate that could not be verified against primary research") while its own footnote [^9] contains the contradicting text.
- **Fix:** "vertical integration caps grades 1–4 at up to 5% over ECX premiums; commercial grades 5–10+UG have traded at up to 22% increments, diverting volume from the ECX floor".

### 10.3 Mbakop et al. [^51] — framing issue (add to §3)

The paper (*Traceability, Value, and Trust in the Coffee Market: A Natural Experiment in Ethiopia*, Agriculture 2023, 13(2):368) studies the **introduction of mandatory ECX trading**, finding "after coffee was forced to be traded via the ECX, traceable coffee export prices increased more than the reported price of nontraceable coffee". The report's "traceable lots gained more from the post-ECX reforms" sits in a paragraph about the 2019 *dismantling* of ECX routing and misleads: the premium Mbakop measures arose under mandatory commingling, not after its removal. Reword to "after coffee was forced through the ECX, traceable lots commanded rising premiums over non-traceable lots".

### 10.4 PDG farmer-vs-producer [^38] — EXONERATED (remove item 3.2 from §3)

The article exists and was read in full: *"Is there a difference between a coffee producer and a farmer?"* (Perfect Daily Grind, Aug 2022, perfectdailygrind.com/?p=98473 → /2022/08/the-difference-between-a-coffee-producer-and-farmer/). It features **Alejandro Cadena (co-founder/CEO, Caravela Coffee)**, **Kenean Dukamo (export manager, Daye Bensa Coffee)**, and Ernest Igual (Saint Dreux). It supports the report's usage: Dukamo — "A farmer is someone who owns or works on a farm, collects the cherry, and makes an income from the coffee grown on the land"; the producer role as "more focused on post-harvest processing and commercial operations… a producer may not even grow coffee at all", including buying from "neighbouring farms". The citation is valid; it is simply not in the local `blog_data/` corpus.

### 10.5 Vietnam "+143%" — RESOLVED: it is USDA's own (internally inconsistent) wording (revises §1.2)

USDA VM2025-0018 itself states: *"The average export price reached $5,630 per ton in the first half of MY 2024/25, up 143 percent compared to MY 2023/24"* — while elsewhere giving the MY 2023/24 crop-year average as $3,792/t (per VICOFA). The two USDA figures are mutually inconsistent (+48.5%); the 143% can only be an H1-on-H1 comparison. The deep-dive copied USDA's sentence but juxtaposed it directly after the $3,792 figure, manufacturing the contradiction. **Fix:** drop the parenthetical or write "up 143 percent compared to the same period of MY 2023/24 (USDA)".

### 10.6 Primary-PDF confirmations (no action; recorded to close §5 items)

- **Vietnam (VM2025-0018):** EU 41% of exports; Simexco Đắk Lắk traceability + EDE EUDR-compliant EU exports; MARD monitoring 136,000 ha; specialty program (2021) 19,000 ha (3%) / 11,000 t by 2030 under VICOFA promotions; MY2025/26 forecast 31M bags; 730,000 ha; Central Highlands 92% of area / 90% of output; WASI; H1 2024/25 exports −23% (Vietnam Customs/GSO); Germany $3,390/t, Philippines $4,424/t; VND 125,000/kg +130%; farmers retaining stocks, exporters on "just-in-time, buy-to-sell"; processed 8.8%→9.6% (green ~90%); >500,000 coffee shops.
- **Guatemala (GT2024-0004 / GT2025-0007 / GT2026-0003):** 376,000 ha remap (101 surveyors; 136,547 production sites edited; up from 305,000); "permanent lack of labor (migration driven)"; export-license gatekeeping "an unnecessary additional trade barrier"; larger farms pay 10% above middlemen with farm-delivery condition; cherry $21–22/100 lb MY2023/24; parchment $140–160 (none) to $205–250 (Organic+Rainforest Alliance); specialty differential "used to be above $18… dropped to $3" per 100 lb; 210 extension agents serving 663 organizations and 27,476 growers; ~125,000 smallholder farmers; trust fund Decree 31-2001 administered by BANRURAL at 2% (small) / 3% (large) — **refinement:** GT2025 says the fund "manages approximately $65 million", GT2026 says "$108 million in capital and $46 million in interest" (2001–2025), so the report's "$65–100 million in capital" is a loose synthesis of two different USDA statements; producer split 97/2.9/0.1% confirmed in text (the 44/31/25 output split is likely in an unextractable figure — unverified but plausible); export value $1.284B MY2024/25 with prices above $300/bag; 261/340 municipalities; 81% SHB; April 2026 reference prices exact (green $247.53–256.53 / parchment $190.41–197.33 / cherry $32.72–38.93).
- **Peru (PE2025-0018):** "Private banks in Peru often reject untitled land as collateral, forcing many farmers to rely on buyers or informal lenders… burdensome fixed-price contracts" — confirms line 126 verbatim-substance.
- **HKS Ethiopia [^48]:** "in the last 15 years, farmers have only captured 14-38% of the export price" ✓; "Prior to the 2017 Vertical Integration reforms, there were less than 50 coffee exporting companies" ✓; "Only 2 of 55 farmers we interviewed understood the current quality grading criteria" ✓; credit to agriculture "dipping below 5% 2017 onwards" ✓. **BUT the report's "more than 500 firms" exporter count does NOT appear in [^48]** — misattribution; needs a source (add to §3).
- **Thünen WP 284 [^49]:** "only 10 per cent of coffee farmers in Ethiopia are members of agricultural cooperatives" ✓; "Unions keep 30 percent and return 70 percent of their net profits to cooperatives" ✓; dividend "paid to members about three [months]" after base price ✓; "cooperatives purchase about one-third of the country's red cherries" ✓.
- **ICO Rwanda [^57]:** "farmers boast 25% profit margin" and "coffee washing stations generally achieve a 10% profit margin" ✓ (report's contested-framing is appropriate).
- **GCP/TechnoServe Indonesia quick-scan [^59]:** "Industry experts estimate that up to 20% of value is lost through poor post-harvest [practice]" ✓ and "Farmers receive a high portion of the export price (80%)" for robusta smallholders ✓ — **closes §7-item and the LatAm agent's "unverifiable" in the report's favor.**
- **KAMI [^63]:** "land smaller than four hectares, a single geolocation coordinate is sufficient… larger than four hectares polygons must be collected" ✓.
- **EFI/ECTA EUDR guide [^50]:** ECTMS (Ethiopia Coffee Traceability and Management System) with first-mile module ✓; Second-Level Land-Use Certificates (SLLC) scanned into ECTMS ✓; "1st Largest rural cadaster in Africa, covering more than 32 million [parcels]" ✓.
- **India (IN2024-0021):** "Approximately 80 percent of Arabica and 20 percent of Robusta coffees are wet processed" ✓; "400-man days per hectare per year for Arabica… 300… for Robusta… labor costs constitute about 60 percent of the total cost of production" ✓; domestic consumption "1.3 million 60-kilogram bags (79,200 MT)" with soluble ~70% ✓; "parchment and Robusta cherry have increased by 45 and 66 percent, respectively" ✓. (All four were marked "unverifiable" by the round-2 India agent from HTML sources; the USDA PDF settles them in the report's favor.)

### 10.7 Kenya — mostly resolved in the report's favor; one miscitation

- **Stanbic DSS:** CONFIRMED. CMA release (28 May 2026): Stanbic Bank Kenya approved as DSS provider, "the second DSS provider coming after Cooperative Bank, which has been the sole DSS service provider since August 2023". The report's claim was right.
- **15 brokers / top-5 ~80%:** CONFIRMED. Kilimo News [^53]: 15 licensed brokers; 2023/24 volume shares Alliance Berries 27%, New KPCU 19%, Kirinyaga Slopes 18%, KCCE-MA 7%, Kipkelion 6% = 77% ("roughly 80%" fair).
- **1.8% fee cap [^54]:** still UNVERIFIED — Kenya Law returned 403; obtain the Gazette PDF of the CMA (Coffee Exchange) (Fees) Regulations 2025.
- **5-day payment / ≥80% to farmer [^55]:** confirmed as a **presidential announcement** (Ruto, per KBC 22 June 2026) — the report's "reform pledge" framing is correct.
- **10% cap / 14-day DSS [^34]:** supported by the Alakonya legal commentary; primary Act text inaccessible (403) — verify against the Gazette when possible.
- **MISCITATION:** the "~60% of auction price" farmer-retention figure comes from the **Alakonya** commentary, not from the cited Intelligence Coffee article [^52] (which supports the agent-abuse narrative but not the 60% figure). Re-point the citation.

### 10.8 Rwanda — miscitations confirmed; floor-price series needs primary sources

- New Times [^58] (16 June 2023) covers the zoning repeal but does **not** contain the 410/480/600/750 RWF floor series or the >1,000 RWF market prices — the price claims are unattached to the cited article. Farmers Review Africa [^36]: the cited article could not be located. Find the NAEB announcements or New Times price stories for each season.
- Gerard et al. (Food Policy 2022) [^56] is about zoning's effect on buyer–farmer relationships; it does **not** contain RTC/Westrock 33 stations, Rwacof/Sucafina 30, or six-firms-70% — those need company/industry sources.
- Still unverified: Bank of Kigali "IKOFI" × Rwacof interest-free loans up to 80% of crop value; cooperatives borrowing at up to 24%; EU taking >60% of Rwanda's coffee exports (compute from Comtrade/ITC with year and HS code).

### 10.9 Brazil — resolutions and one new confirmed error

- **$3.35/lb (§1.4):** contract/date conflation confirmed — the December 2024 contract had expired before 29 Nov; the >$3.35 print belonged to the next active contract earlier that week. Reuters (29 Nov 2024) says only "highest in nearly half a century" / "more than $3 per lb". Re-anchor the figure to ICE settlement data.
- **$7B margin calls [^106]:** the Bloomberg headline exists ("Coffee Traders Cough Up $7 Billion in Margin Calls in Wild Month", 3 Dec 2024); body text paywalled — keep as attributed press estimate (report already cites the syndication).
- **Atlantica/CafeBras [^107]:** CONFIRMED with date correction — the companies announced debt restructuring on **Wednesday 27 Nov 2024** (Reuters, 29 Nov), citing "poor crops and a high volume of rollovers and defaults", and said they were owed ~900,000 bags by farmers who had not delivered. The report's "on 29 November 2024" is the article date, not the announcement date.
- **Conab 2026 (§1.6):** Conab's figures are 66.2M (Feb) → **66.7M bags** (second survey), 2.34M ha planted, 34.4 bags/ha. The 72M+ numbers are **private estimates** (Rabobank 73.3M, StoneX 75.3M, Hedgepoint 75.8M). The report's "66–72 million" conflates Conab with private forecasters — split the attribution.
- **Funcafé (§1.7):** currency error confirmed — the figure is **R$1.17 billion** (per USDA/DCN's own ambiguity resolved against the Brazilian program), not US$1.17B; and "made available/allocated", not "distributed".
- **NEW ERROR — Forest Code reserves:** the statutory legal-reserve minimums (Law 12.651/2012, art. 12) are **80% Amazon / 35% Cerrado / 20% other biomes**. The report's "up to 70% toward the Amazon" propagates the podcast guest's misrecollection. Fix to 80% (keeping the guest's 20% for southern Minas, which is correct).
- **Cooxupé:** own page confirms "mais de 21 mil cooperados, em sua maioria pequenos produtores" — use "21,000+, mostly smallholders"; the ">97% smallholders" and "largest arabica exporter for consecutive years" need the SCS 2023 study / Cecafé ranking citation.
- **Labor rescues:** 302 (2023) is the strongest figure; 214 (2024), the Mata Verde case, and the 24-worker 2025 rescue need the MTE/SmartLab/MPT records or the cited press articles (Public Eye, Agenda do Poder) — keep attributed.

### 10.10 India — series confusion resolved in the report's favor; one figure still blocked

- Babu et al. [^118] supports **all** figures attributed to it (366,242 holdings; 99% <10 ha; 75/70 vs 25/30; >90% farmgate sales in the study districts; top-20 exporters 86%; 50% outturn; ₹89/kg; ₹129,853/t; ₹164,000/t; ₹34,147/t; GI 2019 + Monsooned Malabar 2008; blockchain pilot; FPOs; ₹305/man-day; 73% of variable cost) — with the caveat that they are Coffee Board secondary data and a 60-planter Chikmagalur/Hassan study.
- **CY2024 $1.684B / 403,478 t:** CONFIRMED (BusinessLine, Coffee Board data). The rival ~$1.29B figure is **FY2023-24** — a different series, not a contradiction. The report should state "calendar 2024 (Coffee Board)" and move on (§1.5 downgraded to a wording fix).
- Italy top buyer (78,048 t) ✓; the 51.5% top-three share remains unverified (Moneycontrol blocked).
- EUDR low-risk + Coffee Board polygon mapping for plots >4 ha ✓ (ET, 23 June 2025).
- Consumption: USDA MY2024/25 = 1.3M bags (79,200 MT) vs Coffee Board CY2024 estimate = 96,000 MT — different series; the report uses USDA, which is fine if labeled.
- PLA 1951 applies to coffee and is subsumed into the OSH Code 2020 (commencement-dependent) — fine as written.
- Araku/SAMTFMACS scale claims (2007, 10,000+ families, 500+ villages, "world's largest tribal cooperative", Paris/Bangalore flagships) still unverified from accessible primary pages — cite Naandi/Araku documentation.

### 10.11 Guatemala (non-USDA) — Mare Terra and EUR-Lex confirmed; the 99% claim is not on the ANACAFÉ page

- Mare Terra [^78]: all three claims verbatim (container value doubled; ~$400M additional working capital; 2025 harvest 10–15% below 2024) — interview statements, frame as such.
- ANACAFÉ [^85]: confirms the 21 Feb 2024 MOU, "first country in Latin America", JDE Peet's-funded reforestation, and "96% of Guatemalan coffee growers" — but **does not state** "close to 99% of coffee acreage verified deforestation-free". That result-claim needs its own source or deletion.
- EUR-Lex 2025/1093 annex: Costa Rica, Kenya, Rwanda, Vietnam, India all low-risk; Guatemala absent → standard risk ✓.
- ACODIHUE "~80% of member coffee grown by indigenous, largely Mam-speaking women" — unverified from accessible Sucafina/DR Wakefield/Sustainable Harvest pages; keep attributed to the producer profiles or find the document.
- Tridge [^77] ($994M H1-2025) was blocked; the figure is consistent with ANACAFÉ press coverage — verify via ANACAFÉ or Prensa Libre.

### 10.12 Vietnam (non-USDA), Peru, Indonesia, Colombia — remaining deltas

- Vietnam Wikipedia [^134] supports the historical figures (1857/1888; 1920s zones; Đổi mới 1986; 4–5M migrants; 97% robusta; Ede–Kinh inequality; 500k Đắk Lắk smallholders; 2011 WB 30–40% warning; 2013–14 insolvencies 127 firms / VND 8T / $379M / 60%; 2025 drought −2%) but the page carries a "needs more citations" warning — cite the underlying studies where possible. GCR [^136] confirms +2,100% (WCR), WCR robusta breeding due 2025, Nguyen Coffee Supply 2018, Diaz "C+ prices". VICOFA non-regulatory ✓.
- Peru: Algrano [^46] confirms the StoneX 100,000-bag default estimate (secondary summary — attribute to StoneX via Algrano). Agronline [^47] confirms top-10 ≈45% but for **Q1 2026**, and the top four are Olam, Romex, CICA, **Valley Coffee Trading** — Volcafé is sixth; fix the report's "led by Olam, Romex, CICA, and Volcafe". Algrano's superlative is "world's leading exporter of organic coffee" — the report's "world's largest Fairtrade/organic arabica producer" should be narrowed to that.
- Indonesia: ETK abolition confirmed on the Ditjen Daglu page [^62] (post-ETK procedures: SKA/CoO Form ICO, quarantine, customs) but without regulation numbers; NIB/OSS framing acceptable.
- Colombia: carga 125 kg / FR-94 and the 6% levy are convention-accurate; "33 regional cooperatives" and SICA "nearly every coffee farm" remain unverified — find FNC sources or soften; the 500,000–560,000-families range needs one dated FNC/USDA source.

### 10.13 Still unresolved after two rounds (genuine remaining research gaps)

1. "What Brazil is doing" price-anchor claim (§3.1) — unfound anywhere; replace with sourced wording (e.g., Brazil's weight in the C-market and origin differentials) or delete.
2. "Jenfel" raised beds (§3.8) — terminology unverified; raised beds are documentable, the Amharic term needs an ECTA/academic source or deletion.
3. Chicory-blended South Indian filter coffee (§3.7) — only a Wikipedia placeholder so far; find a Coffee Board/press source.
4. Rwanda cherry floor series (410/480/600/750) and >1,000 RWF 2024 market prices — need the NAEB/New Times season announcements.
5. IKOFI × Rwacof loan terms (80%, interest-free); Rwandan co-op borrowing at 24%; EU >60% of Rwanda's exports.
6. Kenya 1.8% fee cap — needs the Gazette text of the CMA (Coffee Exchange) (Fees) Regulations 2025 (Kenya Law 403'd).
7. ACODIHUE 80% figure; Araku/SAMTFMACS scale claims; Cooxupé ">97% smallholders" and consecutive-year export leadership.
8. Brazil labor-rescue counts for 2024 (214) and 2025 (24) and the Mata Verde/Nestlé-supplier attribution — need MTE/SmartLab/MPT or the cited press.
9. India top-3 destinations 51.5% of 2024 export value (Moneycontrol blocked).
10. Colombia "33 cooperatives" and SICA coverage percentage; 500,000–560,000 families single dated source.
11. Ethiopia ">500 exporters" count (not in [^48]).
12. Vietnam Decision 1392/QD-BNN-TT original text (figures confirmed via USDA, but the decision number itself is unverified).

### 10.14 Updated fix-list deltas (supersedes parts of §9)

- §1.1 → downgrade to "oversimplification"; fix by citing the 1051/2017 → 433/2019 → April-2020-procedure chain (§10.1).
- §1.2 → wording fix per §10.5.
- **Add to §1 as 1.8:** Ethiopia 22%/5% grade inversion (§10.2) — the round's most substantive new error.
- **Add to §1 as 1.9:** Forest Code "up to 70%" → 80% Amazon (§10.9).
- §1.5 → downgrade to "state the period basis" (§10.10).
- §1.6 → split Conab (66.7M) from private estimates (73–76M) (§10.9).
- §3.2 → remove (exonerated, §10.4). §3 gains: Mbakop framing (§10.3); Ethiopia ">500 firms" misattribution (§10.6); ANACAFÉ 99% not on cited page (§10.11); Kenya ~60% retention miscited to [^52] instead of [^34] (§10.7); Rwanda floor-series and Gerard concentration-figure miscitations (§10.8).
- §5: remove items resolved in the report's favor — Indonesia 20% value-loss and 80% robusta share (§10.6), Kenya Stanbic and 15-brokers/80% (§10.7), India USDA cluster (§10.6), Peru 100,000-bag default (§10.12, keep attribution), Vietnam specialty-program figures (§10.6).
- Peru "led by … Volcafe" → top four are Olam, Romex, CICA, Valley Coffee Trading; and date the 45% to Q1 2026 (§10.12).
- Atlantica/CafeBras: announcement date 27 Nov 2024 (not 29 Nov) (§10.9).

---

## 11. Round 3 — Kenya Law primary texts + fixes applied (2026-09-19)

### 11.1 Kenya resolved against primary sources (kenyalaw.org became accessible)

- **1.8% exchange-fee cap — VERIFIED.** The Capital Markets (Coffee Exchange) (Fees) Regulations (Legal Notice 9 of 2025, published 7 Feb 2025, commenced 30 Jan 2025 — titled "…(Fees) Regulations, **2024**"): reg. 4(1) caps total fees at "one-point-eight per cent of the gross value of coffee sold at a coffee exchange", deducted through the DSS; reg. 4(2) requires apportionment **within twenty-four hours** of buyer funds. First Schedule breakdown: broker 1%, exchange 0.3%, DSS provider 0.3%, CMA statutory 0.2%. The report's claim was accurate; the fixed text now carries the breakdown.
- **10% FCS deduction cap — VERIFIED.** Coffee Act No. 8 of 2026, s. 70(1)(a): a cooperative society or union "shall in charging a fee to its growers, adhere to the society's budget and not exceed ten percent of the gross earnings from the coffee sales".
- **14-day DSS payment — VERIFIED.** Coffee Act s. 74(3): exchange-sale proceeds "shall be deposited in a central settlement system… and paid to a grower's account within 14 days".
- The fixed text now cites s. 70(1)(a) and s. 74(3) directly. Remaining Kenya item: the five-day/80% pledge stays framed as a June 2026 presidential pledge (correct as written).

### 11.2 Fixes applied to deep-dive.md (summary of the session's edits)

All fix-list items from §9 and §10.14 were applied (62 counted replacements, all verified by exact-match):

- Ethiopia: reform chain re-attributed (1051/2017 → 433/2019 → April 2020 procedure, direct delivery Jan 2021) in exec summary, matrix, §3, §4; the 22%-premium grade inversion corrected (grades 1–4 capped at 5%; commercial grades 5–10+UG up to 22%); Mbakop framing fixed; ">500 firms" removed; 14–38% vs 55–65% reconciled; *jenfel* term dropped; ECX pre-trade-lot parenthetical removed.
- Vietnam: +143% reworded to the H1-on-H1 basis; Decision 1392 number dropped (program retained per USDA); *cà phê sữa đá* → "iced milk coffee".
- Brazil: Conab 66.7M vs private 73–76M split; Forest Code legal-reserve minimums corrected (20% southern Minas / 35% Cerrado / 80% Amazon, citing [^116]); *caixa* re-anchored to CEPEA/ESALQ; "color" dropped from sort criteria; Cooxupé "21,000+, overwhelmingly smallholders"; $3.35/lb reworded to intraday-prints-that-week + >$3/lb on 29 Nov; Atlantica/CafeBras dated 27 Nov with reasons and 900,000-bag deliveries; Funcafé → "R$1.17 billion available"; Daterra attribution fixed (Howell's judgment); "what Brazil is doing" quote removed.
- Kenya: Act dated correctly (Senate Bill 2023 → Act No. 8 of 2026); duplicated sentence merged; "informal credit" softened; 1.8% cap verified with statutory breakdown; 10% cap and 14-day DSS cited to the Act; ~60% retention re-pointed from [^52] to [^34]; [^52] re-attached to the abuse allegations.
- Rwanda: floor-price series hedged as "reported"; RTC/Rwacof counts attributed to "buyer and industry accounts" with Gerard et al. kept for the governance study; EU ">60%" softened to "majority"; IKOFI terms hedged ("reported").
- Guatemala: remesa "15 percent of the economy" (per practitioner account); trust-fund figures split ($65M under management 2025 / $108M capital + $46M interest 2026); ANACAFÉ 99%-verified claim removed (not on the cited page).
- Peru: top-10 concentration dated Q1 2026 with corrected top-3 (Olam, Romex, CICA; Volcafe sixth); "world's leading exporter of certified organic coffee".
- Colombia: "more than 560,000 coffee-growing families" (per [^37]); FNC cooperatives hedged ("roughly 33"); SICA softened ("great majority").
- India: 51.5% hedged ("reported at"); CCRI "identified and disseminated"; [^120] added for "unromantic".
- Indonesia: ETK framed as abolished 2021 (past tense), citing [^62].
- Direct trade (commodity/specialty table): functions claim and "overstated" claim re-attributed ([^25][^32] vs [^25][^33]).
- Works cited: 16 podcast timestamp ranges re-anchored to verified content locations; [^38] resolved to the live PDG URL; footnote-21 orphan block deleted.

### 11.3 Post-fix integrity check

- Footnotes: 142 defined, 142 used, none dangling, none orphaned (numbering skips 21 by design, no longer referenced anywhere).
- All 18 error-strings from the fix list verified absent; all 20 replacement strings verified present.
- Diff: 50 insertions / 53 deletions.
