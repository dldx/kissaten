---
type: "Reference"
title: "Mr Wush Wush Coffee — Roaster Profile"
description: "Ibagué, Tolima coffee producer and Q Arabica Grader presenting Colombian coffees in Traditional, Exotic, Elite and Culturing ranges."
---

# Mr Wush Wush Coffee — Roaster Profile

## Overview

Mr Wush Wush Coffee is a Colombian coffee producer and specialty-coffee business
based in Ibagué, Tolima. Its WordPress/WooCommerce site groups coffees into
Traditional, Exotic, Elite and Culturing ranges, including Colombian varietals,
co-fermented lots and coffees from named farms. The site identifies the founder
as a fifth-generation coffee grower, Q Arabica Grader and representative of the
Mr Wush Wush brand since 2019.

## Address

- Ibagué, Tolima, Colombia — the published Calle 45A address is presented as a physical store/contact address, not explicitly as the roastery; full roastery address not published on site.

## Schedules & Shipping

- The shipping-policy page says orders are processed in “[1-3]” business days,
  with estimated delivery of “[3-7]” business days nationally and “[7-21]”
  internationally. It gives an approximate standard rate of COP 13,000,
  location-dependent, and says international shipping is quoted by location.
  The square-bracket placeholders are retained on the page itself, so these
  figures should be treated cautiously; no free-delivery minimum is published.

## Philosophy & Quirks

- The site frames its purpose as sharing Colombian farmers’ stories and the
  country’s range of flavours, with a particular emphasis on Wush Wush and
  experimental processing.

## Scraping Quirks

- The scraper visits four category landing pages and extracts `/product/` links.
  AI extraction translates to English; post-processing forces every product to
  340g, rebuilds all price options at 340g, and treats prices above 1,000 as
  CLP. The code currently has no URL exclusions.

## Sources

- https://mrwushwush.com
- https://mrwushwush.com/contacto/
- https://mrwushwush.com/politica-de-envio/
