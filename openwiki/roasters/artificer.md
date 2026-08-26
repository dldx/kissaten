---
type: "Reference"
title: "Artificer — Roaster Profile"
description: "Surry Hills, Sydney coffee bar and roastery focused on the relationship between coffee selection, roasting, and brewing, with seasonal single-origin and blend offerings."
---

# Artificer — Roaster Profile

## Overview

Artificer is a specialty coffee bar and roastery in Surry Hills, Sydney. Its public site says the business specialises in procuring delicious coffee and focuses on the relationship between selection, roasting, and brewing that best represents each coffee's qualities. The online menu currently includes seasonal blends and single origins from Colombia, Ethiopia, Kenya, Peru, and elsewhere.

## Address

- 547 Bourke Street, Surry Hills, Sydney - Australia

## Scraping Quirks

- The store is Square Online rather than a conventional linked product catalogue. Product cards are rendered as buttons without discoverable product links, so the scraper discovers product URLs from `https://artificercoffee.square.site/sitemap.xml`, uses Playwright for JavaScript-rendered product pages, and narrows extraction to the Square product-detail container. It excludes equipment, drip bags, and merchandise by specific URL slugs.

## Sources

- https://artificercoffee.com
- https://artificercoffee.square.site/sitemap.xml
- https://artificercoffee.square.site/product/250g-seasonal-blend/44
