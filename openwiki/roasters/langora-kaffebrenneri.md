---
type: "Reference"
title: "Langøra Kaffebrenneri — Roaster Profile"
description: "Stjørdal (Norway) specialty roastery roasting fresh on order on a Shopify storefront, with free whole-country shipping and a 24-coffee Advent calendar."
---

# Langøra Kaffebrenneri — Roaster Profile

## Overview

Langøra Kaffebrenneri is a Norwegian specialty coffee roastery in Stjørdal,
Trøndelag, running on a Shopify storefront (`langorakaffe.no`, priced in NOK)
with the tagline "Langt reist, nært brent" ("far travelled, roasted close
by"). It buys green beans from traders and auctions worldwide, cups through a
broad range each year to pick its favourites, and roasts to order so beans
ship fresh from the roastery. Its seasonal 24-coffee Advent calendar is a
signature product.

## Address

- Hognesaunvegen 90B, 7513 Stjørdal, Norway — the roastery/contact address
  for Langøra's brenneri (per the contact page and shipping policy, which
  state the coffee is roasted in Stjørdal).

## Sourcing & Transparency

- The about page describes sourcing green beans "from the whole world, from
  both large and small traders and through auctions", cupping an unnumbered
  range of coffees each year to select what to roast (per their site). No
  FOB / farm-gate price figures are published.

## Schedules & Shipping

- Roasted fresh when ordered: beans are packed and shipped directly from the
  roastery shortly after roasting so they arrive as fresh as possible (per
  their site).
- Orders are normally dispatched within a few business days; Norway-wide
  **free shipping** with tracking emailed on dispatch and typical delivery
  3–5 business days.
- Subscriptions ("Langøra Kaffeklubb – Månedens kaffe") ship fresh-roasted on
  the chosen interval.
- Delivery outside Norway is by arrangement only — contact
  `post@langorakaffe.no`.

## Philosophy & Quirks

- Motto "Langt reist, nært brent" and "Fra oss til deg, med litt ekstra glede
  i hver kopp" ("From us to you, with a little extra joy in every cup").
- Roast profiles are tuned per origin, variety, process and bean character to
  let each coffee's own character come through in the cup.

## Scraping Quirks

- The scraper filters the full `produkter` shop by Shopify `product_type ==
  "Kaffe"`, because the collection also holds brewing equipment
  (`Kaffeutstyr`), merch, the coffee-subscription club (`Abonnement`) and the
  seasonal Advent calendar (`Adventskalender`) — genuine non-bean items that
  never belong in the catalogue.
- The shop also sells "Test roast 1,4kg" (product_type `Kaffe`), which is
  dropped upstream by the base class's global `test-roast` URL exclusion —
  deliberate framework policy, not a decision in this scraper (tests pin this
  as an expectation, so a change of heart is a deliberate act).
- Prices are pinned to NOK (store base currency) because a geo-localized
  presentment currency can otherwise be served to a datacenter IP.
- Product URLs are canonicalised to the `www.langorakaffe.no/products/<handle>`
  form the site actually serves.
- The single-origin Shopify JSON `body_html` is empty, so product pages are
  scraped (pruned to `<main>` for token efficiency) to recover tasting notes,
  process, variety, producer, region and elevation.
- "Hverdag + Fest | 4-pk" (3× Dagens Kaffe + 1× Ukens favoritt — two
  different coffees in one pack) carries no standard kit token in its URL or
  name, so `postprocess_review_flags` marks it `is_tasting_kit` and it flows
  through the admin review queue (`requires_review`) rather than public
  search. Dagens Kaffe 4-pk (same blend ×4) and Grut På Tur drip bags are not
  multi-coffee kits and stay unflagged.

## Sources

- https://www.langorakaffe.no/
- https://www.langorakaffe.no/pages/om-oss
- https://www.langorakaffe.no/pages/contact
- https://www.langorakaffe.no/policies/shipping-policy
- https://www.langorakaffe.no/pages/faq