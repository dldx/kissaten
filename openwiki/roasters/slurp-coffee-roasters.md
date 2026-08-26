---
type: "Reference"
title: "Slurp Coffee Roasters — Roaster Profile"
description: "Ukrainian specialty roaster serving a UAH coffee catalogue through a protected, Ukrainian-language online shop."
---

# Slurp Coffee Roasters — Roaster Profile

## Overview

Slurp Coffee Roasters is a Ukrainian specialty coffee roaster. The registered
shop is the Ukrainian-language `slurpcoffeeroasters.com.ua` storefront, whose
coffee catalogue is organised under `/kava/` and filter pages. The reviewed
official pages did not expose reliable founding, equipment or producer-price
details.

## Address

- Ukraine — full roastery address not published on site.

## Scraping Quirks

- The scraper crawls the coffee catalogue and its second filter page, using
  Playwright because the site presents a JavaScript proof-of-work challenge.
  It waits for the `challenge_passed` cookie and page reload before reading
  the full HTML.
- URL extraction uses `catalogCard-image` links and a root path pattern rather
  than a `/products/` pattern, and the scraper translates extracted content to
  English.
- Subscription, gift, wholesale, equipment, merchandise and several named
  non-coffee products are filtered out.

## Sources

- https://slurpcoffeeroasters.com.ua/
- https://slurpcoffeeroasters.com.ua/kava/
