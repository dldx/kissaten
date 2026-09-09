---
type: "Reference"
title: "Kesh Kesh Coffee Roastery — Roaster Profile"
description: "Calgary roastery rooted in the Eritrean coffee ceremony, roasting East African Arabica for delivery across Canada — and the online arm (evidenced but not confirmed on-site) of Nairobi's Kesh Kesh Coffee Roasters."
---

# Kesh Kesh Coffee Roastery — Roaster Profile

## Overview

Kesh Kesh Coffee Roastery is a small specialty roastery in Calgary, Alberta,
selling freshly roasted East African Arabica through a WooCommerce storefront
that ships across Canada only. The catalogue is deliberately tiny: two
signature roasts — **Jebena Medium Roast** and **Fernelo Dark Roast** — each
offered in 250 g / 340 g / 1000 g sizes with a choice of grind (whole bean
through moka-pot) and of origin (Kenya, Ethiopia, Uganda, Rwanda, Costa Rica)
selected per order. The brand name and story trace back to the Eritrean coffee
ceremony, and the site's about page describes a founder-led team guided by a
Certified Quality Arabica Grader with experience dating to 2007.

**A note on identity:** there is a better-known **Kesh Kesh Coffee Roasters &
Café** in Nairobi, Kenya (Timau Plaza, Kilimani), run by Fenkil Empire Ltd and
its founder Fenkil Asghedom Kahsay, who is described by a Nairobi coffee
directory as a CQI Certified Q Grader and SCA AST trainer. That business is
café-first and has **no online bean shop** — its website (keshkeshcafe.com) is
a static menu/reservation site. The Calgary roastery shares the distinctive
"kesh kesh" pan-roasting name story, the Q-Grader credential, the East African
sourcing focus, and even a product name ("Fernelo") closely echoing the
Nairobi founder's name "Fenkil", but the Calgary site itself never mentions
Nairobi — the connection is therefore **evidenced but not confirmed on-site**.

## Address

- 204 7A St NE, Calgary, Alberta T2E 4E8, Canada (roastery address per their
  site's contact and terms pages; returns are also mailed here)

## Schedules & Shipping

- Ships **within Canada only**; all prices in Canadian dollars, provincial
  sales taxes calculated at checkout (per their site's terms).
- Orders are typically processed within 1–2 business days; tracking details
  are emailed on dispatch (per their site's customer-help page).
- No free-delivery threshold or per-region shipping rates are published.

## Philosophy & Quirks

- "Kesh kesh" is the Eritrean word for the motion of coffee beans as they
  roast in a pan during the traditional Eritrean coffee ceremony — the name
  is shared by both the Calgary roastery and the Nairobi café (per their
  respective sites).
- The about page's motto is that "coffee deserves respect" — "not just
  brewed... honoured, prepared, and shared" — with an emphasis on
  "disciplined sourcing and controlled roasting" rather than variety; the
  two-roast line-up ("no shortcuts, no filler blends") reflects that.
- Both signature roasts are named for coffee-ceremony imagery: a *jebena* is
  the Eritrean/Ethiopian clay coffee pot; "Fernelo" appears to echo the
  Nairobi founder's name Fenkil (speculative — not stated on site).

## Scraping Quirks

- **Namesake risk:** two unrelated-looking businesses share the Kesh Kesh
  brand story — the Nairobi café/roaster (no online shop, cannot be scraped)
  and this Calgary WooCommerce roastery. This scraper targets the **Calgary
  shop** (keshkeshroastery.com), so Kissaten's geography data lists the
  roaster as Canada despite the brand's Kenyan association.
- The store is WooCommerce, not Shopify: there is no `products.json`; product
  URLs are root-level slugs (`/jebena-medium-roast/`) with no `/product/`
  segment, so URL-pattern filtering must not rely on the default product-path
  patterns.
- **Origin is a per-order variant, not a bean attribute**: each roast lets the
  customer choose Kenya / Ethiopia / Uganda / Rwanda / Costa Rica at
  add-to-cart time, so extracted beans may legitimately carry no single
  origin; do not hardcode one.
- Out-of-stock detection relies on WooCommerce's `outofstock` class on the
  `li.product` card of `/shop/`.

## Sources

- https://keshkeshroastery.com/ (home — tagline, catalogue, Google-review widget)
- https://keshkeshroastery.com/about/ (name story, founder, Q Grader)
- https://keshkeshroastery.com/shop/ (product line-up, prices, origins)
- https://keshkeshroastery.com/jebena-medium-roast/ (weights, grind and origin options, "18 years of industry experience")
- https://keshkeshroastery.com/customer-help/ (processing times, Canada-only shipping, returns, full mailing address)
- https://keshkeshroastery.com/contact/ (address, phone, support email)
- https://www.keshkeshcafe.com/ and https://www.keshkeshcafe.com/contact (Nairobi café — menu-only site, Timau Plaza, Kilimani)
- https://www.findmecoffee254.com/amazing-cafes/kesh-kesh-coffee-roasters-%26-cafe (Nairobi roaster profile: Q Grader, AST, East African sourcing)
- https://sca.coffee/sca-news/25/issue-24-an-evolving-landscape-9pwm2 (Fenkil Empire Ltd / Kesh Kesh Coffee Roasters, Nairobi)
