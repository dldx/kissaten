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

Progress: **17 / 40 implemented**.

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

## Checklist

- [x] [Aviary](https://www.aviary.coffee) → scraper `aviary`, [profile](../roasters/aviary.md)
- [ ] [Arcane Estate](https://arcaneestatecoffee.com) (New York, café at 37 Cornelia St)
- [ ] [Base Coat](https://basecoatcoffee.com) (roasts nordic/extra light)
- [ ] [Bean's Beans](https://beansbeans.coffee)
- [x] [Black & White Coffee Roasters](https://www.blackwhiteroasters.com) → scraper `black-white-coffee-roasters`, [profile](../roasters/black-white-coffee-roasters.md)
- [x] [Blendin Coffee Club](https://blendincoffeeclub.com) → scraper `blendin-coffee-club`, [profile](../roasters/blendin-coffee-club.md)
- [x] [Botz](https://botz-coffee.com) → scraper `botz`, [profile](../roasters/botz.md)
- [ ] [Brandywine Coffee Roasters](https://www.brandywinecoffeeroasters.com)
- [ ] [Ceto](https://ceto.coffee)
- [ ] [Coffee with Dongze](https://coffee-with-dongze.myshopify.com) (Shopify default domain — no custom domain)
- [ ] [Corvus Coffee Roasters](https://www.corvuscoffee.com) (Denver)
- [x] [Flower Child Coffee](https://flowerchildcoffee.com) → scraper `flower-child-coffee`, [profile](../roasters/flower-child-coffee.md) (more developed roast profile than UL)
- [x] [Hex](https://hex.coffee) → scraper `hex`, [profile](../roasters/hex.md)
- [x] [H&S Coffee Roasters](https://hscoffeeroasters.com) → scraper `h-s-coffee-roasters`, [profile](../roasters/h-s-coffee-roasters.md)
- [x] [Ilse](https://ilsecoffee.com) → scraper `ilse`, [profile](../roasters/ilse.md)
- [x] [Intelligentsia](https://www.intelligentsia.com) → scraper `intelligentsia`, [profile](../roasters/intelligentsia.md) (thread says "special selection only")
- [ ] [King's Arms Coffee Co.](https://kingsarmscoffee.com) (Tampa, FL; the thread commenter said "cincy")
- [ ] [Lantern Coffee Bar and Lounge](https://lanterncoffee.com) (Grand Rapids, MI)
- [ ] [Love Letters](https://love-letter-coffee.square.site) (Squarespace site brands itself "Love Letter Coffee")
- [ ] [Lume Roasters](https://lumeroasters.coffee)
- [ ] [Merit Coffee Co.](https://meritcoffee.com) (Texas)
- [ ] [Moonwake Coffee Roasters](https://moonwakecoffeeroasters.com) (Austin)
- [ ] [Movement Coffee](https://movementcoffee.com) (recommended for Panama light roasts)
- [x] [Native Coffee Company](https://www.thenativecoffeecompany.com) → scraper `native-coffee-company`, [profile](../roasters/native-coffee-company.md)
- [ ] [Norml (norml coffee ppl)](https://normlppl.coffee)
- [ ] [One Line Coffee](https://www.onelinecoffee.com) (Columbus, OH)
- [x] [Onyx Coffee Lab](https://onyxcoffeelab.eu) → scraper `onyx-coffee`, [profile](../roasters/onyx-coffee.md)
- [ ] [Patch](https://patchcoffee.shop) ("a roasting project")
- [x] [Passenger](https://passengercoffee.com) → scraper `passenger`, [profile](../roasters/passenger.md)
- [x] [Prodigal Coffee](https://getprodigal.com) → scraper `prodigal-coffee`, [profile](../roasters/prodigal-coffee.md)
- [x] [Proud Mary Coffee USA](https://proudmarycoffee.com) → scraper `proud-mary`, [profile](../roasters/proud-mary.md)
- [ ] [Red Rooster Coffee](https://www.redroostercoffee.com) (Floyd, VA)
- [ ] [Roosevelt Coffeehouse](https://rooseveltcoffee.org) (Columbus, OH)
- [ ] [Second Spin Roasting Co.](https://secondspinroasting.com) ("somewhere in California" per the thread)
- [x] [Sey Coffee](https://www.seycoffee.com) → scraper `sey-coffee`, [profile](../roasters/sey-coffee.md)
- [x] [Shoebox Coffee](https://shoebox.coffee) → scraper `shoebox-coffee`, [profile](../roasters/shoebox-coffee.md)
- [x] [S&W Roasting](https://www.swroasting.coffee) → scraper `sw-roasting`, [profile](../roasters/sw-roasting.md)
- [ ] [Superlost Coffee](https://www.superlost.com) (Brooklyn — Supernatural / New Light / COM lines)
- [ ] [Superthing Coffee Roasters](https://superthingcoffee.com) (Austin)
- [ ] [Thankfully Coffee](https://thankfullycoffee.com) (offers light and extra light profiles)
