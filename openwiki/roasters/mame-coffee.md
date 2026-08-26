---
type: "Reference"
title: "Mame Coffee — Roaster Profile"
description: "Zurich roastery founded by competition baristas Emi Fukahori and Mathieu Theis, with daily and competition coffees and a long championship record."
---

# Mame Coffee — Roaster Profile

## Overview

MAME Roastery is a Swiss specialty coffee company founded in 2016 by Emi Fukahori and Mathieu Theis. The WooCommerce storefront separates daily coffees from competition coffees, and says MAME began sourcing and roasting its own coffee in 2020. Its site lists cafés and the roastery across Switzerland, with an additional KURO MAME location in Tokyo.

## Address

- MAME Roastery GmbH, Uetlibergstrasse 65/67, 8045 Zürich, Switzerland.

## Sourcing & Transparency

- MAME says it selects coffees carefully, maps them onto its flavour wheel, and roasts separate espresso and filter expressions. The site provides sourcing and roasting context but does not publish FOB, farm-gate, or price-paid-to-producer figures on the reviewed pages.

## Philosophy & Quirks

- The name “MAME” means “beans” in Japanese. Competition is central to the company’s story: the founders met through coffee championships, and the site records Emi Fukahori’s 2018 World Brewers Cup win and Mathieu Theis’s 2018 World Barista Championship third place, among many later results.

## Scraping Quirks

- The registry key is `mame-coffee`. The scraper visits two separate WooCommerce category archives (daily coffee and competition coffees), uses AI extraction without Playwright, and excludes URLs containing `subscription`, `equipment`, `box-set`, `gift`, or `monthly-mame`. The `box-set` exclusion is worth checking if the catalogue introduces a coffee sampler that should go through review rather than disappear.

## Sources

- https://mame.coffee/about-us/
- https://mame.coffee/imprint/
- https://mame.coffee/
