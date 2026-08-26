---
type: "Reference"
title: "MobyDick Coffee Roasters — Roaster Profile"
description: "Shanghai roaster founded in 2015 whose Notion-based coffee catalogue is organised around respect for time and nature."
---

# MobyDick Coffee Roasters — Roaster Profile

## Overview

MOBYDICK COFFEE ROASTERS says it was founded in Shanghai in 2015. Its official site is a compact English/Chinese site with a “Delicious” coffee list and wholesale information; the company says it focuses on the beans themselves and on professional roasting. The published story frames its work around respect for time, reverence for nature, and giving back to coffee origins.

## Address

- Shanghai, China — full roastery address not published on the official pages reviewed.

## Philosophy & Quirks

- The company’s own description says it seeks innovation and practice that benefit the coffee industry, and uses products and design to express a “let go of the time” lifestyle. No public product prices were visible to the scraper.

## Scraping Quirks

- The registry key is `mobydick-coffee-roasters`. The scraper targets `/delicious`; its Playwright helper clicks every `div.notion-toggle` before reading the page so folded products become visible. Product extraction translates to English, and post-processing deliberately sets price and price options empty because the site does not display prices.

## Sources

- https://mobydickcoffeeroasters.guide
- https://mobydickcoffeeroasters.guide/delicious
