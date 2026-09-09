---
type: "Reference"
title: "Origin Coffee Roasting — Roaster Profile"
description: "Cape Town specialty pioneer (est. 2005) from a De Waterkant working warehouse — barista-academy powerhouse with a Yemeni limited-reserve 'Alchemy' line, priced in ZAR."
---

# Origin Coffee Roasting — Roaster Profile

## Overview

Origin Coffee Roasting opened in late 2005 in De Waterkant, Cape Town, with
the stated dream of "elevating the quality of coffee in South Africa to that
of the best in the world" — all coffees are hand-roasted in their "timeless,
working warehouse" in the city. Beyond the shop, Origin is a coffee-education
powerhouse: it founded the barista academy now run as the African School of
Coffee (ASC), has qualified 3,500 baristas and sent multiple South African
Barista Champions to World Barista Championship events between 2007 and 2018
(per their awards page). The catalogue spans single origins (Kenya, Burundi,
Colombia, Ethiopia, India), a seasonal Winter Blend, a decaf, and a Yemeni
limited-reserve line (Al Mahjar Peaberry, Maghrib Ans XV) sold in 40g jars.

## Address

- 28 Hudson Street, De Waterkant, Cape Town, 8001, South Africa — the
  flagship café and roasting warehouse share the address; the site describes
  all coffees as hand-roasted on site.

## Roasting & Equipment

- All coffees are "hand-roasted right here, at the southernmost tip of
  Africa"; no specific roasting hardware is published on site.
- Yemeni limited releases carry an "Alchemy Process" — described on product
  pages as "a precise form of coffee fermentation designed to enhance
  sweetness, clarity and aroma".

## Schedules & Shipping

- Orders are processed within 24 hours if placed before 14:00 (weekend orders
  from the following Monday); some equipment items add 24 hours.
- Free shipping on orders over R550 (ZAR).
- Within Cape Town: R80, 1–2 business days. Major SA city centres: R80,
  3–4 business days. Outlying/regional areas: calculated at checkout,
  4–5 business days. All delivery via third-party courier partners.
- International: ships to "all countries within courier reach"; fees on
  enquiry.

## Philosophy & Quirks

- "An unbroken chain of excellence" — Origin emphasises African coffee
  heritage ("the birthplace of coffee"), regular producer travel, and
  building a café culture through its academy rather than only selling beans.
- The store is far broader than coffee: a curated tea wall (green, oolong,
  rooibos, honeybush), a cascara cola ("CAS 4 Pack"), hand-poured brew gear
  from Hario/Chemex/Bialetti/Timemore and branded Miir drinkware.
- The footer ties Origin to the OTT Brand Group, whose brands share
  marketing sign-ups.

## Scraping Quirks

- The curated `collections/coffee-beans` endpoint is the bean catalogue
  (7 products on capture); `collections/all` mixes in teas, equipment and
  merch, so it is not used.
- The products.json `body_html` is thin (usually just flavour notes), while
  each product page carries a COFFEE DETAILS spec block (origin, altitude,
  body, acidity, roast, brewing, varietals, processing) plus narrative
  accordions — the scraper scrapes product pages pruned to
  `div.accordion-wrapper` to capture the extra detail cheaply.
- Product URLs are canonicalised to the no-collection `/products/<handle>`
  form the live site serves, and store currency is pinned to ZAR against
  Shopify Markets geo-conversion.

## Sources

- https://originroasting.co.za
- https://originroasting.co.za/pages/about-us
- https://originroasting.co.za/pages/contact
- https://originroasting.co.za/pages/shipping-policy
- https://originroasting.co.za/pages/awards
- https://originroasting.co.za/products/maghrib-ans-xv
- https://originroasting.co.za/collections/coffee-beans/products.json
