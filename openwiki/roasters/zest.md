---
type: "Reference"
title: "Zest — Roaster Profile"
description: "Australian specialty roaster with Melbourne, Sydney and Moe operations, Brambati and Diedrich roasting equipment, Cropster profiling, solar power and producer-focused origin projects."
---

# Zest — Roaster Profile

## Overview

Zest Specialty Coffee Roasters is an Australian roaster with operations in Melbourne, Sydney and Moe. Its Shopify storefront presents Espressist blends such as Blackbird, Corcovado, Libertango and African Mailman, alongside Foundation Series, Curated Collection and Special Reserve single origins. Zest also runs a Richmond sensory studio and education programme for baristas, café owners and coffee drinkers.

## Address

- 42 Buckley Street, Marrickville NSW 2204, Australia — Sydney Roastery.
- 12 Moore Street, Moe VIC 3825, Australia — Moe Roastery.

## Sustainability

- Zest says its roastery runs on solar-generated renewable electricity. It keeps hessian sacks and coffee husks out of landfill by donating them to farmers, landowners and community gardens for uses including weed matting, tree potting, composting and animal bedding.
- It separates cardboard and recyclable plastics for collection and donates hessian sacks to Hopeworks, where students use them in a sustainability module to make reusable shopping bags. It also promotes reusable drinkware and has run an artisan-cup project with a local artist.
- Zest is registered with the Rainforest Alliance (registration ID **RA37789**) and says it buys Rainforest Alliance coffees. It also says it pays a premium for Brazil coffee packed in 100% recyclable and renewable paper sacks rather than hessian.

## Sourcing & Transparency

- Zest describes direct relationships with farmers, intensive cupping and origin projects intended to help farming communities improve quality and earn higher remuneration. Its Project Raggiana pilot in Papua New Guinea used low-oxygen fermentation; Zest says the resulting microlots improved by four quality points and a later cooperative trial produced **100 bags** of higher-grade coffee intended to sell at a premium.
- The site explains that its micro-lots are traceable to the farm and farm owner and are usually coffees scoring **85+** on the SCA grading system. It does not publish FOB or farm-gate price figures on the pages checked.

## Roasting & Equipment

- Zest says it roasts on **Brambati** and **Diedrich** machines and tracks roast profiles with **Cropster**. It describes espresso and filter as different development approaches: espresso is generally roasted more slowly, while filter is developed faster to preserve delicate flavours.

## Schedules & Shipping

- Zest says it roasts micro-lots on **Mondays and Thursdays**, and Ninety Plus coffees **only on Thursdays**. Its studio page says retail coffees are roasted fresh each week.
- Within Australia, Standard Shipping is **$12.00 AUD** and Express Shipping is **$17.00 AUD**. Free standard shipping applies over **$70.00 AUD** and free express shipping over **$132.00 AUD**.

## Philosophy & Quirks

- Zest frames its purpose around flavour, balancing innovation with tradition and quality with accessibility. Its Richmond studio offers sensory flights, industry events and barista training intended to make coffee knowledge more accessible.

## Scraping Quirks

- The scraper reads the curated `/collections/coffee/products.json` feed, but the feed returns collection-form product URLs. It normalises `/collections/coffee/products/<handle>` to `/products/<handle>` before fetching the product page.
- The JSON body lacks much of Zest's producer and processing data, so the scraper keeps the `div.product-container` from the product page; that container holds producer, farm, region, varietal, process and altitude details for AI extraction.

## Sources

- https://www.zestcoffee.com.au/pages/our-brand
- https://www.zestcoffee.com.au/pages/our-sustainability
- https://www.zestcoffee.com.au/pages/our-coffee
- https://www.zestcoffee.com.au/pages/our-studios
- https://www.zestcoffee.com.au/pages/faqs
- https://www.zestcoffee.com.au/pages/contact-us
