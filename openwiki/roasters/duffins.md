---
type: "Reference"
title: "Duffin's — Roaster Profile"
description: "Lake District (Cumbria) roaster in Staveley, Kendal on a WordPress WooCommerce + Elementor storefront — blends and single origins roasted on a 15kg Giesen, rebranded from Mr Duffins Coffee."
---

# Duffin's — Roaster Profile

## Overview

Duffin's (rebranded from "Mr Duffins Coffee") is a Lake District roaster based in Staveley, Kendal, Cumbria, on a WordPress WooCommerce + Elementor storefront at duffinscoffee.com. It sells blends (Shout Out, Chin Wag, Juicy Gossip, Chit Chat) and single origins (San Ignacio Peru, Rwanda Inzovu, Moche Peru, Decaf Cajamarca) at roughly £10.50–£45 (GBP).

## Address

- 49 Main Street, Staveley, Kendal LA8 9LN, Cumbria — United Kingdom

## Philosophy & Quirks

- Roasts in-house on a 15kg Giesen roaster with light-to-medium roasts.
- Same-day dispatch on Mondays and Thursdays; a community "gift" range.
- Rebranded from "Mr Duffins Coffee" (old site mrduffinscoffee.com is dead).

## Scraping Quirks

- WooCommerce + Elementor storefront (no products.json); coffee products live at `/shop/coffee/<slug>/`.
- A stale `/shop/page/2/` pagination duplicates the listing (excluded) — only `/shop/` is crawled and duplicate featured/related cards are deduplicated.
- Some products link via `/shop/type/<taxonomy>/<slug>/` taxonomy archive URLs, which normalize back to `/shop/coffee/<slug>/` (both resolve 200 to the same product).
- Sold-out items are detected by the `outofstock`/`sold-out`/`oos` CSS class on the `li.product` card.
- Elementor duplicates product cards (deduplicated); equipment, tea, hot-chocolate, gift cards/sets and hampers are excluded.

## Sources

- https://duffinscoffee.com
- https://duffinscoffee.com/shop/