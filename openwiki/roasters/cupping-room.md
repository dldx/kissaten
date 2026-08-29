---
type: "Reference"
title: "Cupping Room — Roaster Profile"
description: "Hong Kong specialty coffee roastery founded in 2011, small-batch roasting on a Loring S35 Kestrel, with barista-champion pedigree — 'Brew like a champ!'"
---

# Cupping Room — Roaster Profile

## Overview

Cupping Room is a Hong Kong specialty coffee roasting company, founded in 2011
in Stanley Plaza, Stanley (per its site). Official collateral describes it as an
award-winning specialty coffee roastery and a pioneer of Hong Kong's
specialty-coffee scene. It sources green beans around the globe, roasts them in
Hong Kong, and serves through cafés in Hong Kong and (per official material)
Singapore, plus an online shop. The web shop is a client-rendered React
storefront backed by the GOLS e-commerce service; its `Beans` category
(`/shop/115`) holds the Blend and Single Origin coffees.

## Address

- Hong Kong — roastery and coffee bar on Po Hing Fong, Sheung Wan (per their
  site's story page); full street address not published.

## Sustainability

- Follows "relationship coffee": direct links to the families and communities
  who grow and produce its coffee, forging links in person whenever possible and
  securing top-quality lots in return.
- Its roasting equipment is cited for energy efficiency (see Roasting &
  Equipment), and packaging choices — e.g. the NESPRESSO®-system capsule — were
  weighed for environmental impact.

## Sourcing & Transparency

- Buys directly from producers and trusted partners, season after season, and
  visits them in person; named relationships include Gesha Village (Ethiopia)
  and Granja La Esperanza (Colombia).
- Every package and product page shows the producer, region, altitude, process,
  harvest time and variety of the coffee.

## Roasting & Equipment

- Small-batch roasting on a **Loring S35 Kestrel** — called the first of its
  kind in Hong Kong and "the gold standard of coffee roasters" — whose patented
  integrated afterburner recycles heat. The roastery previously roasted on a
  Probat UG15 Retro, upgraded to the Loring to cater for larger production.
  Machine capacity is not published.

## Schedules & Shipping

- The roastery operates weekly: orders cut off Tuesdays 9:00 a.m., with coffee
  roasted fresh Wednesday–Friday.
- Local orders dispatch the following Monday via SF Express and arrive 2–3
  working days later; international orders go via HK EMS Speedpost / FedEx /
  Aramex and arrive 4–10 working days after dispatch.
- Free local delivery on orders over HK$300; a HK$30 delivery fee applies below
  (an extra HK$15 per kg over 1 kg).
- Coffee subscription: cut-off on the 22nd of each month, roasted the last week
  of the month.

## Philosophy & Quirks

- Tagline: **"Brew like a champ!"** — and the brand name references the "cupping
  room" where coffee professionals taste, evaluate and discover great coffees.
- Champion results associated with the brand include Kapo Chiu (Hong Kong
  Barista Champion 2012, 2013, 2016), Taka Ishitani (Japan Barista Champion
  2017, 2019), Slawek Saran (Poland Brewers Cup Champion 2020) and Penny Pang
  (Hong Kong Barista Champion 2023).
- The subscription ships a Roaster's Choice each month: selected coffees are not
  taken from current web-shop offerings and may appear in the shop around a
  month after shipping. Subscriptions are managed through ReCharge.

## Scraping Quirks

- The storefront is a fully client-rendered React SPA backed by the GOLS
  e-commerce API, so every listing and product page must be rendered with
  Playwright — a plain HTTP fetch returns only the empty app shell — and the
  listing is scrolled to trigger lazy-loaded products.
- The scraper removes the generic `cupping` URL exclusion because the roaster's
  own domain contains that word.
- Currency is pinned to HKD because product pages expose no
  `og:price:currency` tag on this mono-currency storefront.

## Sources

- https://cuppingroom.hk/
- https://cuppingroom.hk/shop/115
- https://cuppingroom.hk/delivery
- https://cuppingroom.hk/subscription
- https://cuppingroom.hk/locations
- https://cuppingroom.hk/about
- https://cuppingroom.hk/our-story
- https://cuppingroom.hk/our-coffee
- https://cuppingroom.hk/our-achievements
- https://cuppingroom.hk/our-sustainability-practises
