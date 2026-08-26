---
type: "Reference"
title: "Botz Coffee — Roaster Profile"
description: "Danny Falloon's Munster, Indiana micro-roastery, named for a childhood nickname and a robot roasting machine, with playful single-origin coffees and explicit roasting standards."
---

# Botz Coffee — Roaster Profile

## Overview

Botz Coffee is a US micro-roastery created by Danny Falloon. Falloon says he returned to his hometown of Munster, Indiana after honing his skills around the United States, and built Botz around small-quantity green buying and a fresh, thoughtful menu. The shop focuses on playful single-origin coffees and micro-lots, with roast data published as a dedicated part of the storefront.

## Address

- Munster, Indiana - United States (full street address not published on the site)

## Sourcing & Transparency

- Botz says it buys ethically sourced green coffee in small quantities. Falloon states that, while he is not yet able to travel to producers, he buys through importers invested in a transparent and sustainable coffee community. The site publishes no FOB or price-paid-to-producer figures.

## Schedules & Shipping

- The storefront advertises a USD 5 flat shipping rate and free shipping on orders of USD 55 or more. No roast or dispatch cadence is published on the pages checked.

## Philosophy & Quirks

- The name comes from a childhood nickname and Falloon's "wicked cute" roasting machine, alongside his love of coffee roasting and video games. Botz's published standards include sharing the chosen roast profile, cupping every batch before sale, acknowledging uncertainty, and continuing to support racial and social equality initiatives.

## Scraping Quirks

- The scraper uses Shopify's `all` collection because coffee and merch share that endpoint, then removes gift cards, clothing, subscriptions, and other non-coffee slugs. It rewrites collection product URLs to the canonical `/products/<handle>` path; the dedicated Roast Data page is not itself a product source.

## Sources

- https://botz-coffee.com/pages/about
- https://botz-coffee.com/pages/contact
- https://botz-coffee.com/policies/shipping-policy
