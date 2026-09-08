---
type: "Reference"
title: "BeBerry Coffee — Roaster Profile"
description: "Pražská pražírna specializované kávy — the Prague speciality roastery founded by Slovak Cup Tasting Champion and Q Grader Tomáš Pavlov, selling Original/Limited/Competition-series coffees with cupping scores printed on the pack."
---

# BeBerry Coffee — Roaster Profile

## Overview

BeBerry Coffee ("Pražská pražírna specializované kávy" — Prague roastery of
speciality coffee) is a Czech specialty roaster founded by Tomáš Pavlov (1st
place Slovak Cup Tasting Champion 2018, Q Grader since 2019, 3rd place Czech
Roasting Championship 2023 and 2024) and Karin Pavlov (1st place Slovak Cup
Tasting Championship 2021). The WooCommerce storefront prices coffee in CZK
and divides its portfolio into Original (espresso 84–85+, filter 86+),
Limited (~88+) and Competition (top-0.01% auction lots) series. Per their
site, it is the only roastery in Czechia and Slovakia that prints current,
objective cupping scores on its packaging. A showroom sits at Přípotoční 35,
Praha 10 – Vršovice.

## Address

- Prague, Czechia — full roastery street address not published on site. The
  site lists a showroom ("Be Berry coffee showroom", Přípotoční 35, Praha 10 –
  Vršovice, 101 00, Czech Republic) and the company's registered office
  (BeBerry Coffee s.r.o., Korunní 108, 101 00 Praha).

## Sourcing & Transparency

- Direct trade plus "green buyer" partner sourcing, described on the /o-nas/
  page: direct purchases put the roastery in close contact with farmers,
  while larger partners let it pick top lots and better monetise farmers'
  full production.
- Sourcing partners support development projects in origin countries —
  schools, infrastructure and training for the communities growing the
  coffee.
- Cupping scores printed on packs are the average of the supplier's and
  BeBerry's own ratings of the delivered lot; lots failing the contracted
  quality are repriced or returned (per /o-nas/).
- Per their site, every coffee is graded at three stages: at the farm, after
  arrival in Europe, and in the roastery, with the Q Grader founder centrally
  involved.

## Schedules & Shipping

- Czech delivery via One by Allegro: 30 Kč to a pickup point or 49 Kč to an
  address, delivered by the 2nd day (per /doprava-a-platba/). No free-delivery
  minimum is published.

## Philosophy & Quirks

- "BE BOLD, BE BERRY." — the roastery's motto and the team's dog "Berry",
  described as its "quality controller", gave the company its name. Product
  tasting notes carry the same voice on the site (e.g. Uganda "sweet as
  banana in chocolate"), and the founders' wine-sensory background feeds the
  cupping-led curation.

## Scraping Quirks

- WooCommerce `li.product` cards carry the `instock`/`outofstock` status
  class; sold-out filtering uses the class, NOT text: every in-stock variable
  product card also renders a disabled "Dočasně vyprodáno" add-to-cart button,
  so substring detection would false-positive on the whole catalogue.
- The `kava` category's two coffee-cherry/blossom teas
  (`cascara-coffee-cherry-tea`, `kavovy-kvet`) are excluded — they are tea,
  not beans (consistent with the cascara convention elsewhere in the codebase).
- Product pages carry no `og:price:currency` meta, so `postprocess_extracted_bean`
  pins `currency = "CZK"`.

## Sources

- https://www.beberrycoffee.cz/
- https://www.beberrycoffee.cz/o-nas/
- https://www.beberrycoffee.cz/doprava-a-platba/
- https://www.beberrycoffee.cz/categories/kava/