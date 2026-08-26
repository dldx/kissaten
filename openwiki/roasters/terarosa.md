---
type: "Reference"
title: "Terarosa — Roaster Profile"
description: "South Korean specialty coffee company with an English/Korean online shop, rotating origin coffees, subscriptions and a long-running coffee brand."
---

# Terarosa — Roaster Profile

## Overview

Terarosa is a South Korean coffee company whose online shop sells single origins, blends, decaffeinated coffees, drip bags and subscriptions. The site presents products in Korean and English and publishes roast dates on product listings. Its public site also links the shop to Terarosa cafés and a library/newsletter programme.

## Address

- 25 Hyeoncheon-gil, Gujeong-myeon, Gangneung-si, Gangwon-do, South Korea (the address published in the site footer for the company/roastery)

## Philosophy & Quirks

- The storefront uses Korean category and product pages, with English names and translated product facts alongside them. Product origin specifications may be supplied as images on detail pages rather than as ordinary page text.

## Scraping Quirks

- The scraper discovers coffee sub-categories from the live listing page instead of hard-coding Korean category names, skips the “View All” parent link, and uses Playwright plus English translation for AI extraction.
- Terarosa’s origin spec sheets are image-based. The scraper narrows the product HTML to the product card but scrolls the full page before taking a screenshot so lazy-loaded origin images are captured. It conservatively drops accessory-only grid items such as shopping bags and collectible blocks, while retaining names that also contain coffee/drip-bag terms.

## Sources

- https://www.terarosa.com
- https://www.terarosa.com/contents/story/
