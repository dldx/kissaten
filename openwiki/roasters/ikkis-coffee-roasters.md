---
type: "Reference"
title: "Ikkis Coffee Roasters — Roaster Profile"
description: "Indian specialty roaster with estate-led filter and espresso coffees, an in-house coffee collection and a strong ritual-focused presentation."
---

# Ikkis Coffee Roasters — Roaster Profile

## Overview

Ikkis Coffee Roasters is an Indian specialty coffee roaster whose official “Our Coffee” page presents filter coffees, espresso coffees and an Ikkis Blend. Products are identified with estate names such as Ratnagiri, Karadykan, Mooleh Manay and Stanmore, and are sold in INR through a Shopify storefront. The site also links to its own farms, barista training and wholesale programmes.

## Address

- India — full roastery address not published on the consulted site page.

## Philosophy & Quirks

- The storefront’s closing line is “Never settle for good enough.” The product presentation calls the buying experience a “ritual” and separates filter, espresso and blend coffees.

## Scraping Quirks

- The scraper fetches the `/pages/our-coffee` listing with Playwright, then takes product links only from the first `div.ikkis-products-container`. It currently applies no custom URL exclusions after the base coffee-product check, so the first-grid assumption is the important maintenance hazard.

## Sources

- https://www.ikkis.coffee/pages/our-coffee
- https://www.ikkis.coffee
