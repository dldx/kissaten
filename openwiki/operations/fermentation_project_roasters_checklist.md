---
type: "Reference"
title: "The Fermentation Project — Roaster Checklist"
description: "Checklist of the ~120 roasters selling the James Hoffmann x Lucia Solis 'Fermentation Project' tasting kit, per thefermentationproject.com/buy-a-tasting-kit — ticked entries have a Kissaten scraper implemented."
---

# The Fermentation Project — Roaster Checklist

Source: [thefermentationproject.com/buy-a-tasting-kit](https://www.thefermentationproject.com/buy-a-tasting-kit)
(the James Hoffmann × Lucia Solis "Fermentation Project" tasting-kit retailer list).

- **[x]** = scraper implemented and registered in
  [`src/kissaten/scrapers/registry.py`](../../src/kissaten/scrapers/registry.py) —
  see the linked roaster profile in `openwiki/roasters/`.
- **[ ]** = no scraper yet (candidate for a new module + registry entry + tests).

Progress: **119 / 121 implemented** — complete: all roasters with a real website are scraped; the 2 open rows are Instagram-only (no website). Final attribution corrections: FUNK → Canada/CAD, Massimo → Kazakhstan/KZT, Exploradores → Mexico/MXN, Peak and Bean → Guatemala/GTQ, Candycane → Czechia/CZK, Savage → France, Mundos → US, Ómra → UK. Caveats: kits sold out at YES PLZ/Despiertoo/Savage/San Agustín (picked up on restock); Brass Horn storefront hydration intermittently flaky; Cofmos Cloudflare solve ~50% headless; Sweet Maria's roasted-only by policy. (Shopify waves 1-A/C/E + non-Shopify wave 2-A; corrections: Ómra → UK/GBP, Mundo Novo → Spain/EUR, Casa Landino → Colombia/COP, The Brew Company → Denmark/EUR, Critical Beans → Belgium confirmed; Sweet Maria's roasted-only by policy; Cofmos needs Playwright for its Cloudflare challenge).

## United Kingdom (12/17)

- [x] [Bell's Beans](https://bellsbeans.co.uk/products/the-fermentation-project-quartet) → scraper `bells-beans`, [profile](../roasters/bells-beans.md)
- [x] [Copperopolis Coffee](https://copperopolis.coffee/product/the-fermentation-project/) → scraper `copperopolis` (WooCommerce)
- [x] [Craft Decaf](https://craftdecaf.com/products/fermentation-kit-hoffmann) (project kit is caffeinated) → scraper `craft-decaf` (no kit currently listed, range scraped)
- [x] [Dark Pony](https://darkponycoffee.com/collections/coffee/products/the-fermentation-project-kit) → scraper `dark-pony` (page-scrape mode — Shopify JSON body_html is empty)
- [x] [Established Coffee](https://established.coffee/products/the-fermentation-project-with-lucia-solis-james-hoffmann) → scraper `established`, [profile](../roasters/established.md)
- [x] [Glen Lyon Coffee Roasters](https://www.glenlyoncoffee.co.uk/products/james-hoffmanns-the-fermentation-project-quartet-box) → scraper `glen-lyon`, [profile](../roasters/glen-lyon.md)
- [x] [Method Coffee Roasters](https://methodroastery.com/products/fermentation-project) → scraper `method-coffee` (no kit currently listed, range scraped)
- [x] [Oddkin Coffee](https://www.oddkincoffee.com/collections/hoffman) → scraper `oddkin-coffee`
- [x] [Perky Blenders](https://perkyblenders.com/products/fermentationproject) → scraper `perky-blenders`, [profile](../roasters/perky-blenders.md)
- [x] [Plot](https://plotroasting.com/products/fermentation-project-james-hoffman-x-lucia-solis) → scraper `plot-roasting`, [profile](../roasters/plot-roasting.md)
- [x] [Skylark Coffee](https://www.skylark.coffee/products/james-hoffmann-and-lucia-solis-fermentation-project-sample-pack) → scraper `skylark-coffee`, [profile](../roasters/skylark-coffee.md)
- [x] [Square Mile Coffee Roasters](https://shop.squaremilecoffee.com/collections/the-fermentation-project) → scraper `square-mile`, [profile](../roasters/square-mile.md)
- [x] [Taith Coffee](https://taithcoffee.com/shop/p/pre-sale-the-fermentation-project) → scraper `taith-coffee`, [profile](../roasters/taith-coffee.md)
- [x] [The Coffee Apothecary](https://shop.thecoffeeapothecary.co.uk/products/fermentation-project) → scraper `the-coffee-apothecary`, [profile](../roasters/the-coffee-apothecary.md)
- [x] [The Lost Barn](https://lostbarncoffee.co.uk/product/the-fermentation-project/) → scraper `the-lost-barn`, [profile](../roasters/the-lost-barn.md)
- [x] [Thomson's Coffee](https://www.thomsonscoffee.com/products/fermentation-project) → scraper `thomsons`, [profile](../roasters/thomsons.md)
- [x] [Wogan Coffee](https://wogancoffee.com/products/james-hoffmanns-fermentation-project) → scraper `wogan`, [profile](../roasters/wogan.md)

## USA & Canada (4/51)

- [x] [802 Coffee](https://802coffee.com/products/the-fermentation-project) → scraper `802-coffee`
- [x] [94 Celcius](https://94celcius.com/en/products/pre-vente-james-hoffman-ft-94-celcius) → scraper `94-celcius`, [profile](../roasters/94-celcius.md)
- [x] [Aero Coffee Roasters](https://www.aerocoffeeroasters.com/product-page/the-fermentation-project-set) → scraper `aero-coffee` (Wix, not Squarespace)
- [x] [Arrowroot Coffee](https://arrowrootcoffee.com/products/pre-order-the-fermentation-project-tasting-kit) → scraper `arrowroot-coffee`
- [x] [Brainwave Coffee Roasters](https://brainwaveroasters.com/products/james-hoffman-fermentation-project) → scraper `brainwave-coffee`
- [x] [Brass Horn Coffee Roasters](https://www.brasshorncoffee.com/product/-pre-sale-brass-horn-x-james-hoffman-fermentation-project-x-kit/OWS3NJHI5IXZ77GBXWGXZWHZ) → scraper `brass-horn-coffee` (Square Online, Playwright — storefront hydration is intermittently flaky)
- [x] [Brewtus Roasting](https://brewtusroasting.com/collections/coffee/products/the-fermentation-project) → scraper `brewtus-roasting`
- [x] [Brio Coffeeworks](https://www.briocoffeeworks.com/pages/the-fermentation-project-brio-x-james-hoffmann) → scraper `brio-coffeeworks`
- [x] [Cafe Domestique](https://cafedomestique.bigcartel.com/product/pre-order-fermentation-project-tasting-kit-cafe-pickup-or-shipping) → scraper `cafe-domestique` (Big Cartel)
- [x] [City Boy Coffee](https://cityboycoffee.com/product/pre-order-fermentation-project/) → scraper `city-boy-coffee` (WooCommerce; kit hidden while out of stock — picked up when restocked)
- [x] [Common Time Coffee](https://commontimecoffee.com/products/thefermentationproject) → scraper `common-time-coffee`
- [x] [Copper Door Coffee](https://copperdoorcoffee.com/collections/coffee/products/the-frementation-project-kit) → scraper `copper-door-coffee`
- [x] [Craft 42 Coffee Roasters](https://craft42roasters.ca/products/the-james-hoffman-fermentation-project) → scraper `craft-42-roasters`
- [x] [Curious Coffee](https://www.curious-coffee.com/product-page/the-fermentation-project) → scraper `curious-coffee` (Wix; verified: Ann Arbor, MI)
- [x] [DOMA Coffee](https://www.domacoffee.com/products/the-fermentation-project) → scraper `doma-coffee`
- [x] [Dorothea Coffee](https://dorotheacoffee.com/products/fermentation-project-kit) → scraper `dorothea-coffee`
- [x] [Driftaway](https://store.driftaway.coffee/products/fermentation-project-kit-by-james-hoffmann) → scraper `driftaway`
- [x] [Driftwood Coffee](https://www.driftwood.coffee/product/the-fermentation-project-tasting-kit/LV6KNVBAUIX33ZPCXGABNI7M) → scraper `driftwood-coffee` (Square Online via Weebly store API; verified: Corpus Christi, TX)
- [x] [Eachother](https://eachother.rocks/products/the-fermentation-project-kit) → scraper `eachother` (verified: Rockford, IL — United States)
- [x] [Eiland Coffee](https://www.eilandcoffee.com/fermentationproject) → scraper `eiland-coffee` (Squarespace; verified: Richardson, TX)
- [x] [Found Coffee](https://www.found.coffee/the-fermentation-project) → scraper `found-coffee` (Square Online via Weebly store API; verified: Toronto, CA)
- [x] [FUNK Coffee](https://funk.coffee/products/the-fermentation-project) → scraper `funk-coffee` (verified: Vancouver, BC — Canada/CAD)
- [x] [Geva Coffee](https://www.gevacoffee.com/products/the-fermentation-project-kit) → scraper `geva-coffee`
- [x] [Gost Coffee Roasters](https://www.gostcoffee.com/product-page/pre-order-james-hoffmann-lucias-solis-fermentation-project) → scraper `gost-coffee` (Wix + sitemap discovery; verified: New Lenox, IL)
- [x] [Herman's Boy Coffee](https://hermans-boy.square.site/product/presale-the-fermentation-project-tasting-kit/GOY3QUCTPE764Y7UHZGQIHOY) → scraper `hermans-boy` (Square Online)
- [x] [HEX Coffee Roasters](https://hex.coffee/products/fermentation-project-preorder) → scraper `hex-coffee`, [profile](../roasters/hex.md)
- [x] [Higher Grounds](https://www.highergroundstrading.com/products/fermentation-project) → scraper `higher-grounds`
- [x] [Jersey City Roasters](https://jerseycityroasters.com/products/fermentation) → scraper `jersey-city-roasters` (kit is a waitlist product — kept)
- [x] [Julius Coffee](https://juliuscoffee.com/en/products/le-projet-fermentation-de-james-hoffmann) → scraper `julius-coffee` (verified: Bromont, QC; scrapes `cafes` + `cafe-de-specialite` — the latter holds the kit)
- [x] [Kustomcoffee](https://kustomcoffee.com/products/the-fermentation-project-tasting-set) → scraper `kustom-coffee` (verified: US-based)
- [x] [La Barba Coffee](https://labarbacoffee.com/products/fermentation-project-collection) → scraper `la-barba`
- [x] [LiB's Market](https://www.libsmarket.com/fermentation-project) → scraper `libs-market` (Square Online — sitemap discovery + Playwright)
- [x] [Lohner Coffee](https://lohnercoffee.com/products/fermentation-project) → scraper `lohner-coffee`
- [x] [Moongoat](https://moongoat.com/products/james-hoffmann-fermentation-project-set-moongoat-coffee) → scraper `moongoat`
- [x] [Mundos Roasting](https://www.mundosroastingco.com/coffee/p/fermentation-box-set) → scraper `mundos-roasting` (Squarespace; verified: Traverse City, MI — US, not Canada)
- [x] [New Heights Coffee Roasters](https://newheightscoffee.com/products/fermentation-project-set-pre-sale) → scraper `new-heights-coffee`
- [x] [Nucleus Coffee](https://nucleuscoffee.com/en/products/kit-du-projet-fermentation-de-james-hoffmann) → scraper `nucleus-coffee`
- [x] [Quills Coffee](http://www.quillscoffee.com/fermentation) → scraper `quills-coffee`
- [x] [Regalia](https://regaliacoffee.com/products/pre-sale-james-hoffmann-fermentation-project-x-regalia) → scraper `regalia-coffee`
- [x] [Rogue Wave Coffee](https://roguewavecoffee.ca/products/pre-order-james-hoffman-lucia-solis-the-fermentation-project-tasting-kit-4x-100g-bags) → scraper `rogue-wave-coffee`, [profile](../roasters/rogue-wave-coffee.md)
- [x] [Rosso Coffee Roasters](https://www.rossocoffeeroasters.com/products/fermentation-project-with-james-hoffmann-tasting-kit) → scraper `rosso`, [profile](../roasters/rosso.md)
- [x] [Salt Winds Coffee](https://saltwindscoffee.com/pages/fermentation-project) → scraper `salt-winds-coffee` (verified: Canada/CAD)
- [x] [Square One Coffee](https://shop.squareonecoffee.com/products/fermentation-project) → scraper `square-one-coffee`
- [x] [Steel Oak Coffee](https://steeloakcoffee.com/products/james-hoffmann-fermentation-project) → scraper `steel-oak-coffee` (verified: United States/USD)
- [x] [Stone Creek Coffee](https://www.stonecreekcoffee.com/products/the-fermentation-project) → scraper `stone-creek-coffee`
- [x] [Sweet Bloom](https://sweetbloomcoffee.com/products/the-fermentation-project) → scraper `sweet-bloom`
- [x] [Sweet Marias (Green Coffee Set)](https://www.sweetmarias.com/products/fermentation-project-green-coffee-set) → scraper `sweet-marias` (**roasted-only** — green/unroasted beans intentionally not tracked; the green-coffee catalogue and green blends are not fetched)
- [x] [Talavera Coffee](https://www.talaveracoffee.com/the-fermentation-project) → scraper `talavera-coffee` (Squarespace; verified: Conroe, TX)
- [x] [Three Keys Coffee](https://threekeyscoffee.com/products/fermentation-frequency) → scraper `three-keys-coffee`
- [x] [Tinker Coffee](https://www.tinkercoffee.com/collections/adventurous/products/fermentation-project) → scraper `tinker-coffee` (no kit currently listed, range scraped)
- [x] [YES PLZ](https://www.yesplz.coffee/product/fermentation-project) → scraper `yes-plz` (Next.js; kit currently pre-sale sold out — picked up on restock)

## Europe (9/40)

- [x] [19 Grams](https://19grams.coffee/products/the-fermentation-project-kaffee-kit-von-mit-james-hoffmann) → scraper `19-grams`
- [ ] [Altura CoRoasters](https://www.instagram.com/altura.coroasters/) — SKIPPED: Instagram-only, no website to scrape
- [x] [Kafina](https://kafinacoffee.fr/products/fermentation-project-by-james-hoffmann) → scraper `kafina`
- [x] [Savage Roasters](https://www.savageroasters.coffee/products/the-fermentation-project-by-james-hoffmann-lucia-solis-testing-kit) → scraper `savage-roasters` (verified: Paris, France — not Greece; kit currently sold out)
- [x] [Banibeans](https://banibeans.si/products/the-fermentation-project-tasting-kit) → scraper `banibeans`
- [x] [Bean Machine](https://www.beanmachine.dk/shop/nyristet-kaffe/the-fermentation-project-tasting-kit-4-x-200-gr/) → scraper `bean-machine` (WooCommerce + JetEngine)
- [x] [Kaffe Brenneri](https://bergenkaffebrenneri.no/products/the-fermentation-project) → scraper `bergen-kaffebrenneri`
- [x] [Candycane Coffee](https://www.candycane.coffee/produkty/the-fermentation-project-james-hoffmann-x-lucia-solis) → scraper `candycane-coffee` (bespoke Laravel+Livewire; verified: Czechia/CZK — not Poland)
- [x] [Cofmos](https://cofmos.lt/produktai/fermentation-project/) → scraper `cofmos` (WooCommerce behind Cloudflare challenge — Playwright)
- [x] [Critical Beans](https://criticalbeansit.be/shop/blind-tasting-set) → scraper `critical-beans` (custom React SPA + JSON API; Belgium confirmed)
- [x] [D Stands For](https://decaf.at/thefermentationproject) → scraper `d-stands-for`, [profile](../roasters/d-stands-for.md)
- [x] [Despiertoo](https://www.despiertoo.com/product-page/fermentation-project) → scraper `despiertoo` (Wix; verified: Granada, Spain; kit pre-sale sold out)
- [x] [Drip Roasters](https://driproasters.ch/fermentation-project) → scraper `drip-roasters`, [profile](../roasters/drip-roasters.md)
- [x] [Espresso Winkel](https://www.espressowinkel.nl/koffie/the-fermentation-project-van-james-hoffmann/) → scraper `espresso-winkel`
- [x] [Farmhand Coffee](https://www.farmhandcoffee.ie/collections/filter-coffee-beans/products/the-fermentation-project-with-james-hoffmann-lucia-solis) → scraper `farmhand-coffee`
- [x] [Father's Coffee Roastery](https://fathers.cz/kava/filtr/the-fermentation-project) → scraper `fathers`, [profile](../roasters/fathers.md)
- [x] [Friedhats Coffee](https://friedhats.com/products/fermentation-box) → scraper `friedhats`, [profile](../roasters/friedhats.md)
- [x] [GourmoNauten (DE)](https://gourmonauten.club/) → scraper `gourmonauten`
- [x] [Gringo Nordic](https://www.gringonordic.se/product/the-fermentation-project-box/) → scraper `gringo-nordic`
- [x] [Ief & Ido](https://iefido.nl/the-fermentation-project/) → scraper `ief-ido`
- [x] [Kaffa Roastery](https://kaffaroastery.fi/en/products/the-fermentation-project-with-james-hoffmann-limited-edition) → scraper `kaffa`, [profile](../roasters/kaffa.md)
- [x] [KaffeRäven](https://www.kafferaven.se/products/the-fermentation-project-med-james-hoffman) → scraper `kafferaven`, [profile](../roasters/kafferaven.md)
- [x] [Manhattan Coffee Roasters](https://manhattancoffeeroasters.com/product/coffees/fermentation-project-tasting-kit/) → scraper `manhattan-coffee`, [profile](../roasters/manhattan-coffee.md)
- [x] [Mundo Novo Coffee](https://mundonovocoffee.com/pages/the-fermentation-profect) → scraper `mundo-novo` (verified: Spain, not Latin America)
- [x] [Muttley & Jack's Coffee Roasters](https://muttleyandjacks.se/collections/our-coffees/products/the-fermentation-project-with-james-hoffmann-and-lucia-solis) → scraper `muttley-jacks`
- [x] [Ómra Coffee](https://omra.coffee/products/james-hoffmann-fermentation-project-coffee-tasting-set) → scraper `omra-coffee` (verified: Derry, UK — not Republic of Ireland)
- [x] [Onoma Kaffee](https://onoma.coffee/products/fermentation-project-set-4-kaffees-je-50g) → scraper `onoma-kaffee`
- [x] [PS Coffee Roasters](https://pscoffeeroasters.com/products/the-fermentation-project-james-hoffmann-collaboration) → scraper `ps-coffee-roasters`
- [x] [purpur Café & Kaffeerösterei](https://purpur.coffee/products/fermentation-project-probierset) → scraper `purpur-coffee`
- [x] [Ripsnorter Coffee](https://ripsnorter.nl/products/guatemala-james-hoffmans-fermentation-project-tasting-box) → scraper `ripsnorter`, [profile](../roasters/ripsnorter.md)
- [x] [Roasted Brown](https://www.roastedbrown.com/pages/the-fermentation-project-with-james-hoffmann-lucia-solis) → scraper `roasted-brown`
- [x] [Roastopus](https://roastopus.com/hu/termekeink/kaveink-filter/the-fermentation-project-100117) → scraper `roastopus`
- [x] [San Augustín Tostadores De Café](https://sanagustin.com/producto/fermentation-project-james-hoffmann/) → scraper `san-agustin` (WooCommerce; kit currently sold out — handled by OOS path)
- [ ] [San Diego Cafe](https://www.instagram.com/sandiego.cafe/) — SKIPPED: Instagram-only, no website to scrape
- [x] [Solo Brewing](https://solobrewing.pt/products/the-fermentation-project) → scraper `solo-brewing`
- [x] [Sprout Coffee Roasters](https://sproutcoffeeroasters.art/products/the-fermentation-project) → scraper `sprout-coffee` (verified: Netherlands/EUR)
- [x] [Suedseite](https://suedseite.coffee/collections/alle-bohnen/products/the-fermentation-project-james-hoffmann-lucia-solis-guatemala) → scraper `suedseite`
- [x] [The Brew Company](https://brew-company.com/products/the-fermentation-project-kit) → scraper `the-brew-company` (verified: Denmark, sells in EUR)
- [x] [The God Shot](https://www.thegodshot.be/shop/guatemala-the-fermentation-project-1693) → scraper `the-god-shot` (Odoo)
- [x] [ZEFF Coffee](https://zeffcoffee.com/products/presale-zeff-x-the-fermentation-project-tasting-pack) → scraper `zeff`, [profile](../roasters/zeff.md)

## Middle East (1/2)

- [x] [Archers Coffee](https://archerscoffee.com/collections/coffee-academy/products/the-fermentation-project-kit) → scraper `archers-coffee`, [profile](../roasters/archers-coffee.md)
- [x] [Massimo Coffee](https://icoffee.store/products/the-fermentation-project-set) → scraper `massimo-coffee` (verified: Almaty, Kazakhstan/KZT — Ecwid storefront)

## Central Asia (0/0)

- (no roasters listed)

## Asia & Australia (1/7)

- [x] [Buon Caffe](https://buoncaffe.com.tw/products/the-fermentation-project/) → scraper `buon-caffe` (WooCommerce, zh-TW, translate-to-EN)
- [x] [Garage Roasters](https://garageroasters.com.au/products/fermentation-project-tasting-kit) → scraper `garage-roasters`
- [x] [Good Cup](https://goodcup.ph/fermentationproject) → scraper `good-cup` (no kit currently listed, range scraped)
- [x] [Micrology Coffee Roasters](https://micrology.com.au/products/the-fermentation-project-4-pack-tasting-set) → scraper `micrology` (no kit currently listed, range scraped)
- [x] [NiR Coffee](https://nircoffee.id/shop) → scraper `nir-coffee`
- [x] [That's Whyld Coffee Roasters](https://www.thatswhyld.com.au/shop/p/hoffmanproject) → scraper `thats-whyld` (Squarespace)
- [x] [Zest Specialty Coffee Roasters](https://www.zestcoffee.com.au/products/4-pack-tasting-set-the-fermentation-project) → scraper `zest`, [profile](../roasters/zest.md)

## Central & South America (0/4)

- [x] [Casa Landino](https://casalandino.com/pages/evento-de-james-hoffman) → scraper `casa-landino` (verified: Colombia/COP, not Guatemala)
- [x] [Coffea Cafés Especiales](https://www.coffea.gt/fermentationproject) → scraper `coffea-cafes-especiales` (Lovable/React SPA + Playwright; reservation-based, kit Q450)
- [x] [Exploradores Club de Cafe](https://www.grupoexploradores.com/tienda/p/the-fermentation-project-james-hoffmann-x-luca-sols-kit-de-cata) → scraper `exploradores-club-de-cafe` (verified: CDMX, Mexico/MXN — not Guatemala)
- [x] [Peak and Bean](https://www.peakandbeans.com/thefermentationproject) → scraper `peak-and-bean` (Odoo; verified: Guatemala/GTQ)

## Coverage audit (2026-09-15): full catalogues, not kit-only

All 94 scrapers target **complete roasted-coffee catalogues** (verified by
enumerating every store's collections and diffing against the targeted ones).
Two gaps found and fixed:

- **julius-coffee**: was scraping only `cafes`; the Fermentation kit lives in
  `cafe-de-specialite` — that collection added.
- **19-grams**: was excluding `geschenkbox` handles, which dropped two coffee
  bundles (Geschenkbox mit Projekt-Kaffees, Weihnachtsgeschenkbox with mugs +
  coffee). Gift-box exclusion removed; bundles flow through for downstream
  tasting-kit flagging. Pure merch (mugs alone), pods, subscriptions and
  events are still excluded.

Legit non-coffee exclusions verified by reading live product data: Stone
Creek cold-brew filter packs, 19grams subscriptions/pods/events, Muttley &
Jack's subscription boxes, Sweet Bloom/Moongoat product-type filters.

Scope exclusions by policy: **green (unroasted) coffee is never scraped**
(Sweet Maria's roasted-only; Buon Caffe excludes greenbeans; Julius's
`green-coffee` collection not fetched).

## QA pass (2026-09-15, post-implementation)

Full `tests/unit/` + shared-file test run after all waves integrated: **41
failures found and fixed, final state green** (pre-existing
`test_proxy_configuration` failure is environmental — the sandbox `.env`
configures a proxy the test doesn't clear; unrelated to this work):

- **Currency pinning (real bug):** 17 Shopify scrapers (wave 1-E) relied on
  lazy geo-detection, which the base-class display-name lookup silently
  falls back to GBP for. All now pin `store_currency` + `_currency_detected`
  (verified home currencies).
- **Test-only fixes:** MRO-patched `fetch_page` fakes missing the bound
  `self`; gost's `_probe_fetch` coroutine double-call; steel-oak/regalia
  market-param stubs returning a list instead of `{"products": ...}`; the
  `"page=1" in url` substring matching `per_page=100` (buon-caffe,
  city-boy); mundos fixture `};\n</script>` split; espresso-winkel page-1
  fixture declaring 1 page; talavera double-narrowing assertion.
- **Small production hardening:** dedup in the WooCommerce page walks
  (buon-caffe, city-boy, copperopolis); Squarespace variant formatter falls
  back to the `product:price:currency` og-meta when the variant JSON omits
  the currency (talavera, eiland); critical-beans `/shop/` fetch now tries
  the authoritative API detail even when the SPA shell fetch fails.

## Implementation notes

To tick a new box, follow the standard new-scraper flow
(see the `shopify-scraper` / `squarespace-scraper` / `non-shopify-scraper`
skills and [../scrapers/scraping-system.md](../scrapers/scraping-system.md)):

1. Create `src/kissaten/scrapers/<roaster_name>.py` inheriting from `BaseScraper`
   (or `ShopifyJsonScraper` when the storefront is Shopify — many of the
   unticked shops above are, e.g. Copperopolis, Dark Pony, Oddkin, Square One).
2. Decorate with `@register_scraper(...)` from `src/kissaten/scrapers/registry.py`
   and confirm the `country` is in
   `src/kissaten/database/roaster_location_codes.csv`.
3. Add tests in `tests/unit/test_<roaster>.py`.

Note: kit/sampler products like these tasting kits must **not** be excluded —
they are extracted and flagged `is_tasting_kit = true` /
`requires_review = true` so they land in the admin review queue
(see [../../docs/KIT_REVIEW.md](../../docs/KIT_REVIEW.md)).
