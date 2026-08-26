---
type: "Reference"
title: "MachHörndl Kaffee — Roaster Profile"
description: "Nuremberg roastery founded in 2008, operating a 25 kg Probat drum roaster and publishing detailed German and neighbouring-country shipping bands."
---

# MachHörndl Kaffee — Roaster Profile

## Overview

MachHörndl Kaffee is a specialty roastery in Nuremberg, Germany, with espresso and brew bars. The company says it was founded as a roastery in 2008 and focuses on seasonal, traceable coffees and light roasts. Its shop separates espresso and filter coffees and also offers equipment, tea, cocoa, bundles and an unpackaged section.

## Address

- Obere Kieselbergstr. 13, 90429 Nürnberg, Germany.

## Sourcing & Transparency

- MachHörndl says its green coffee is **100% traceable** and that it usually seeks coffees from small farmers. It says growing conditions, varieties and processing methods guide selection. The pages checked do not publish per-lot FOB or producer-payment figures.

## Roasting & Equipment

- The Goho roastery page identifies a **25 kg Probat drum roaster** and says visitors can watch the team roast there. The company describes gentle, light roasting intended to preserve each coffee’s distinctive aromas.
- The roastery page also describes a rotating espresso/filter selection and brew-bar service; no roasting software is named.

## Schedules & Shipping

- The published shipping page says orders are processed Monday–Friday within 24 hours and made ready for dispatch after payment. Delivery is generally stated as a maximum of 10 days, depending on parcel-service workload.
- Germany: €3.20 up to 750 g, €4.50 up to 2.5 kg, €7.50 up to 16 kg, €15.00 up to 32 kg and €20.00 above 32 kg.
- Austria: €15 up to 16 kg, €30 up to 32 kg and €40 above 32 kg. Switzerland: €15.90 up to 1.5 kg, €30 up to 4.5 kg, €35 up to 9 kg, €50 up to 19 kg and €55 up to 30 kg. Austria and Switzerland are given a delivery time of 15 working days after payment. The page publishes no free-shipping threshold.

## Philosophy & Quirks

- MachHörndl’s philosophy page traces the business to Armin Machhörndl’s 2005 “green & bean” barista shop and its 2008 roastery launch. It highlights variety and complexity over uniformity, and describes Armin as a two-time German Brewers Cup champion.
- The shop’s **Unverpackt** section offers selected products without packaging and says beans can be bought in reusable containers for refilling on a later visit.

## Scraping Quirks

- The scraper visits separate `/Shop/Espresso/` and `/Shop/Filter/` pages and uses the site’s `a.product-image-link` selector with a root URL pattern of `/`. It currently has no additional exclusion patterns, so the catalogue boundary depends on those two category pages and the base scraper’s product test.

## Sources

- https://www.machhoerndl-kaffee.de
- https://www.machhoerndl-kaffee.de/Locations/
- https://www.machhoerndl-kaffee.de/Philosophy/
- https://www.machhoerndl-kaffee.de/Footernavigation/Versandkosten/
