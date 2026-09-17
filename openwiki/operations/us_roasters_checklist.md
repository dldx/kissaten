---
type: "Reference"
title: "US Roasters Checklist"
description: "Checklist of the 40 US coffee roasters recommended in the r/pourover thread \"'Must try' US roasters?\" (saved 2026-09-15) — ticked entries have a Kissaten scraper implemented."
---

# US Roasters Checklist

Source: r/pourover thread ["Must try" US roasters?](https://www.reddit.com/r/pourover/comments/1wgoqfe/must_try_us_roasters/)
(UK-based OP visiting family in Ohio, brews ultralights; saved copy 2026-09-15).

- **[x]** = scraper implemented and registered in
  [`src/kissaten/scrapers/registry.py`](../../src/kissaten/scrapers/registry.py) —
  see the linked roaster profile in `openwiki/roasters/`.
- **[ ]** = no scraper yet (candidate for a new module + registry entry + tests).

Progress: **40 / 40 implemented** (plus Counter Culture Coffee, added later on
request — it wasn't mentioned in the thread). Previously **17 / 40**.

Batch notes (2026-09-16 implementation wave):

- **Patch** (`patch-coffee`): the store (`patchcoffee.shop`) is currently
  **down** — Shopify edge IP but TLS refused across curl, curl_cffi,
  Playwright and an external relay (server-side pause/unmapping, not a bot
  block). The scraper targets root `/products.json` and will start working
  when the store returns; its fixture is a structurally-exact Shopify-shape
  stub, flagged as such in the test docstring.
- **Arcane Estate** (`arcane-estate-coffee`): no collection endpoint serves
  content and the 4 real Panamanian estate coffees are currently unpublished
  (only a subscription is listed) — the scraper will pick them up once the
  store publishes them.
- **Thankfully** (`thankfully-coffee`): Shopify with **JSON routes disabled**
  (`/products.json` 404s) — implemented as a `BaseScraper` over the
  server-rendered `/collections/coffee` + product pages. Light vs extra-light
  roast profiles are variants of the same product.
- **Roosevelt** (`roosevelt-coffeehouse`): shop lives at `roosevelt.coffee`
  (WooCommerce Store API), not on the `rooseveltcoffee.org` WordPress site.
- **Love Letter** (`love-letter-coffee`): Square Online — bean products are
  Square "hidden" items omitted from the store API listing; discovery goes
  through `sitemap.xml` + `__BOOTSTRAP_STATE__`. Only 7 whole-bean coffees.
- **Red Rooster** (`red-rooster-coffee`): Next.js/Vercel + Sanity with Shopify
  Collective commerce — data lives in `__NEXT_DATA__` JSON islands; sold-out
  coffees move to `/archive` (not scraped, noted in the docstring).
- **Kings Arms / One Line / Brandywine / others**: scraping-proxy egress is
  GBP-geo-located (`cart.js` reports GBP) and several Shopify edges reject the
  default libcurl TLS fingerprint — all scrapers pin `store_currency="USD"`
  + `country=US` market params and rebuild the client with
  `impersonate="chrome"` where needed.

Notes:

- **September Coffee Company** was also recommended in the thread but is Canadian;
  it is already implemented as scraper `september-coffee`.
- **Le Dunce Dönuts** (Dunkin' joke) and **Skyline Chili / Graeter's** (Cincinnati
  food-collab jokes) are excluded — not roasters.
- **Bean's Beans** (beansbeans.coffee) is not the same roaster as the already
  implemented Bean & Bean Coffee Roasters (`bean-and-bean`).
- **Onyx Coffee Lab** is a Northwest Arkansas roaster; the registered scraper
  (`onyx-coffee`) points at its EU storefront.
- **Native Coffee Company** (Dallas roastery + showroom) is registered with
  country Colombia in the registry.
- **Counter Culture Coffee** was implemented on request after the thread
  extraction (not a thread mention) — `counter-culture-coffee`.

## Checklist

- [x] [Aviary](https://www.aviary.coffee) → scraper `aviary`, [profile](../roasters/aviary.md)
- [x] [Arcane Estate](https://arcaneestatecoffee.com) → scraper `arcane-estate-coffee` (New York, café at 37 Cornelia St)
- [x] [Base Coat](https://basecoatcoffee.com) → scraper `base-coat-coffee` (roasts nordic/extra light)
- [x] [Bean's Beans](https://beansbeans.coffee) → scraper `beans-beans`
- [x] [Black & White Coffee Roasters](https://www.blackwhiteroasters.com) → scraper `black-white-coffee-roasters`, [profile](../roasters/black-white-coffee-roasters.md)
- [x] [Blendin Coffee Club](https://blendincoffeeclub.com) → scraper `blendin-coffee-club`, [profile](../roasters/blendin-coffee-club.md)
- [x] [Botz](https://botz-coffee.com) → scraper `botz`, [profile](../roasters/botz.md)
- [x] [Brandywine Coffee Roasters](https://www.brandywinecoffeeroasters.com) → scraper `brandywine-coffee-roasters`
- [x] [Ceto](https://ceto.coffee) → scraper `ceto`
- [x] [Coffee with Dongze](https://coffee-with-dongze.myshopify.com) → scraper `coffee-with-dongze` (Shopify default domain — no custom domain)
- [x] [Corvus Coffee Roasters](https://www.corvuscoffee.com) → scraper `corvus-coffee` (Denver)
- [x] [Flower Child Coffee](https://flowerchildcoffee.com) → scraper `flower-child-coffee`, [profile](../roasters/flower-child-coffee.md) (more developed roast profile than UL)
- [x] [Hex](https://hex.coffee) → scraper `hex`, [profile](../roasters/hex.md)
- [x] [H&S Coffee Roasters](https://hscoffeeroasters.com) → scraper `h-s-coffee-roasters`, [profile](../roasters/h-s-coffee-roasters.md)
- [x] [Ilse](https://ilsecoffee.com) → scraper `ilse`, [profile](../roasters/ilse.md)
- [x] [Intelligentsia](https://www.intelligentsia.com) → scraper `intelligentsia`, [profile](../roasters/intelligentsia.md) (thread says "special selection only")
- [x] [King's Arms Coffee Co.](https://kingsarmscoffee.com) → scraper `kings-arms-coffee` (Tampa, FL; the thread commenter said "cincy")
- [x] [Lantern Coffee Bar and Lounge](https://lanterncoffee.com) → scraper `lantern-coffee` (Grand Rapids, MI)
- [x] [Love Letters](https://love-letter-coffee.square.site) → scraper `love-letter-coffee` (Squarespace site brands itself "Love Letter Coffee")
- [x] [Lume Roasters](https://lumeroasters.coffee) → scraper `lume-roasters`
- [x] [Merit Coffee Co.](https://meritcoffee.com) → scraper `merit-coffee` (Texas)
- [x] [Moonwake Coffee Roasters](https://moonwakecoffeeroasters.com) → scraper `moonwake-coffee` (Austin)
- [x] [Movement Coffee](https://movementcoffee.com) → scraper `movement-coffee` (recommended for Panama light roasts)
- [x] [Native Coffee Company](https://www.thenativecoffeecompany.com) → scraper `native-coffee-company`, [profile](../roasters/native-coffee-company.md)
- [x] [Norml (norml coffee ppl)](https://normlppl.coffee) → scraper `norml`
- [x] [One Line Coffee](https://www.onelinecoffee.com) → scraper `one-line-coffee` (Columbus, OH)
- [x] [Onyx Coffee Lab](https://onyxcoffeelab.eu) → scraper `onyx-coffee`, [profile](../roasters/onyx-coffee.md)
- [x] [Patch](https://patchcoffee.shop) → scraper `patch-coffee` ("a roasting project")
- [x] [Passenger](https://passengercoffee.com) → scraper `passenger`, [profile](../roasters/passenger.md)
- [x] [Prodigal Coffee](https://getprodigal.com) → scraper `prodigal-coffee`, [profile](../roasters/prodigal-coffee.md)
- [x] [Proud Mary Coffee USA](https://proudmarycoffee.com) → scraper `proud-mary`, [profile](../roasters/proud-mary.md)
- [x] [Red Rooster Coffee](https://www.redroostercoffee.com) → scraper `red-rooster-coffee` (Floyd, VA)
- [x] [Roosevelt Coffeehouse](https://rooseveltcoffee.org) → scraper `roosevelt-coffeehouse` (Columbus, OH)
- [x] [Second Spin Roasting Co.](https://secondspinroasting.com) → scraper `second-spin-roasting` ("somewhere in California" per the thread)
- [x] [Sey Coffee](https://www.seycoffee.com) → scraper `sey-coffee`, [profile](../roasters/sey-coffee.md)
- [x] [Shoebox Coffee](https://shoebox.coffee) → scraper `shoebox-coffee`, [profile](../roasters/shoebox-coffee.md)
- [x] [S&W Roasting](https://www.swroasting.coffee) → scraper `sw-roasting`, [profile](../roasters/sw-roasting.md)
- [x] [Superlost Coffee](https://www.superlost.com) → scraper `superlost-coffee` (Brooklyn — Supernatural / New Light / COM lines)
- [x] [Superthing Coffee Roasters](https://superthingcoffee.com) → scraper `superthing-coffee` (Austin)
- [x] [Thankfully Coffee](https://thankfullycoffee.com) → scraper `thankfully-coffee` (offers light and extra light profiles)
