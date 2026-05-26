export const categoryConfig: Record<
    string,
    { icon: string; color: string; shortDescription: string; description: string }
> = {
    infused_cofermented: {
        icon: "🍓",
        color: "rose",
        shortDescription:
            "Flavours enhanced by co-fermenting with fruits, flowers, or spices",
        description:
            "Co-fermented and infused processes involve adding external ingredients like fruits, flowers, or spices during fermentation. This creates distinctive flavours that come from the added ingredients rather than the coffee's terroir alone. Transparency about this method helps consumers understand the source of flavour notes.",
    },
    barrel_aged: {
        icon: "🛢️",
        color: "orange",
        shortDescription:
            "Post-processing aging in spirit or wine barrels",
        description:
            "Barrel aging involves storing green or parchment coffee in rum, whiskey, wine, or other spirit barrels. The coffee absorbs flavours from the barrel's previous contents, creating boozy, oaky, or vinous characteristics that overlay the original coffee profile.",
    },
    anaerobic_carbonic: {
        icon: "🫙",
        color: "purple",
        shortDescription:
            "Complex flavours from oxygen-free or CO₂-rich fermentation",
        description:
            "Anaerobic and carbonic maceration processes ferment coffee in sealed, oxygen-free environments or under CO₂ pressure. These controlled conditions allow specific microorganisms to develop intense, complex flavours often described as boozy, lactic, or wine-like.",
    },
    advanced_technical: {
        icon: "🧬",
        color: "teal",
        shortDescription:
            "Precise fermentation control using temperature, yeasts, or microbes",
        description:
            "Advanced technical processes use precise control over fermentation variables including thermal shock (rapid temperature changes), specific yeast or bacteria inoculation, koji mold, lactic acid bacteria, or nitrogen environments to develop targeted flavour profiles with high consistency.",
    },
    washed: {
        icon: "🌊",
        color: "blue",
        shortDescription:
            "Clean, bright, and acidic profiles with well-defined flavours",
        description:
            "The washed process involves removing the cherry's outer fruit before fermentation. Coffee cherries are pulped, fermented in water tanks, then washed and dried. This method produces clean, bright, and acidic flavour profiles with well-defined characteristics.",
    },
    natural: {
        icon: "☀️",
        color: "yellow",
        shortDescription:
            "Fruity, wine-like flavours with more body and sweetness",
        description:
            "In the natural process, whole coffee cherries are dried in the sun before removing the fruit. This extended contact between the bean and cherry creates fruity, wine-like flavours with more body and natural sweetness.",
    },
    honey: {
        icon: "🍯",
        color: "amber",
        shortDescription:
            "Balanced sweetness between washed and natural processes",
        description:
            "The honey process involves removing the cherry skin but leaving some mucilage (the sticky layer) attached during drying. This creates a balance between the cleanliness of washed coffees and the sweetness of naturals.",
    },
    wet_hulled: {
        icon: "🌴",
        color: "emerald",
        shortDescription:
            "Earthy, full-bodied Indonesian processing tradition",
        description:
            "Wet hulling (Giling Basah) is a traditional Indonesian method where parchment is removed while the coffee is still wet, then dried further. This produces distinctly earthy, herbal, and full-bodied flavour profiles characteristic of Sumatran and other Indonesian coffees.",
    },
    decaf: {
        icon: "🚫",
        color: "gray",
        shortDescription: "Caffeine removed while preserving original flavours",
        description:
            "Decaffeination processes remove caffeine while attempting to preserve the original flavour characteristics. Methods include Swiss Water Process, Ethyl Acetate (sugarcane), CO2 extraction, and Mountain Water Process.",
    },
    experimental: {
        icon: "🧪",
        color: "pink",
        shortDescription: "Innovative techniques pushing flavour boundaries",
        description:
            "Experimental processes push the boundaries of traditional coffee processing with novel or proprietary techniques that don't fit neatly into other categories.",
    },
    other: {
        icon: "❓",
        color: "gray",
        shortDescription: "Unique and specialty processing methods",
        description:
            "Unique processing methods that don't fit into traditional categories, often representing regional innovations or specialty techniques developed by individual producers.",
    },
};
