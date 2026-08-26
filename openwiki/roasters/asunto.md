---
type: "Reference"
title: "Asunto Coffee Roasters — Roaster Profile"
description: "Santiago, Chile roaster on Jumpseller offering origin coffees in 250 g and 1 kg formats alongside training and business services."
---

# Asunto Coffee Roasters — Roaster Profile

## Overview

Asunto Coffee Roasters is a specialty coffee business based in Santiago, Chile,
with a Jumpseller storefront. Its coffee navigation separates 250 g, 1 kg and
“super special” formats; the shop also offers accessories, training and
business services. The accessible catalogue includes coffees from Peru, Brazil,
Bolivia and Colombia.

## Address

- Santiago — Chile; the site publishes a contact address at Compañía de Jesús 2820, but does not identify that address specifically as the roastery.

## Scraping Quirks

- The scraper targets the 250 g category at
  `/cafe-en-grano/formato-250gr`, reads `a.product-image` links, skips links
  marked `not-available`, and excludes the `desgustacion` path.
- Product pages are extracted with AI and translated to English. The
  registry's scraper is deliberately limited to the 250 g category, not the
  site's 1 kg category or equipment catalogue.

## Sources

- https://www.asunto.cl
- https://www.asunto.cl/contact
- https://www.asunto.cl/cafe-en-grano/formato-250gr
