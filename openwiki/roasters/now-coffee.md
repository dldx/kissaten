---
type: "Reference"
title: "Now Coffee — Roaster Profile"
description: "Durban coffee lab, drive-through and roastery on a Shopify storefront priced in ZAR — roasts on Thursdays, dispatches on Fridays, with an 'Above Ground' mushroom-coffee sideline."
---

# Now Coffee — Roaster Profile

## Overview

Now Coffee is a coffee lab, drive-through and roastery in Durban (Glenashley),
South Africa, selling on a Shopify storefront priced in ZAR. The bean line-up
comprises single origins (Ethiopia and Costa Rica, including special releases
and decafs) and house blends (Inception, Just Now, Zonke), alongside barista
training courses, coffee drip bags and an "Above Ground" mushroom-coffee
sideline. The team describes itself as "just a bunch of coffee nerds driven
by sharing our experience of coffee with the world" running "a coffee lab,
drive through's and a roastery".

## Address

- 36 Newport Avenue, Glenashley, Durban, South Africa 4051 (shop location,
  coffee lab and drive-through per the contact page; the drive-through is
  above the Ramp with exit to the underground parking, and there is a second
  drive-through at 2 Norfolk Place).

## Schedules & Shipping

- "We roast on | Thursdays" and "dispatch on | Fridays" (site-wide banner).
- Free local shipping on orders over R700 (site-wide banner).

## Philosophy & Quirks

- Community-focused branding: "We aim to better this world through coffee and
  community. We are a community, a family and the best versions of ourselves."
- Beyond beans the store sells barista training courses (home barista,
  foundation, full barista) and a mushroom-coffee line with a dedicated
  "mushroom extract benefits" page.
- Enquiries via info@nowcoffee.co.za.

## Scraping Quirks

- The beans live across two curated collections — `single-origins` and
  `blends` — so the scraper fetches both; `collections/all` additionally
  carries barista training courses, socks and mushroom coffee, which are
  excluded via `exclude_slugs` as a safety net.
- The `coffee-drip-bags` product in `single-origins` is a single-serve sachet
  format (not whole beans) and is excluded via `exclude_slugs` ("drip-bag").
- Product URLs are canonicalised to the no-collection `/products/<handle>`
  form the live site serves.
- The store runs Shopify Markets with currency geolocation, so the scraper
  pins `store_currency` to ZAR and removes the `Accept-Language` header so a
  datacenter IP is never stamped with converted prices.

## Sources

- https://nowcoffee.co.za
- https://nowcoffee.co.za/pages/who-are-we
- https://nowcoffee.co.za/pages/contact
