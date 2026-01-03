export const categoryConfig: Record<
    string,
    { icon: string; color: string; shortDescription: string; description: string }
> = {
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
    anaerobic: {
        icon: "🫙",
        color: "purple",
        shortDescription:
            "Unique, complex flavours from oxygen-free fermentation",
        description:
            "Anaerobic fermentation occurs in sealed, oxygen-free environments, allowing unique microorganisms to develop distinct flavours. This process produces complex, often funky or wine-like characteristics that can be quite experimental.",
    },
    honey: {
        icon: "🍯",
        color: "amber",
        shortDescription:
            "Balanced sweetness between washed and natural processes",
        description:
            "The honey process involves removing the cherry skin but leaving some mucilage (the sticky layer) attached during drying. This creates a balance between the cleanliness of washed coffees and the sweetness of naturals.",
    },
    fermentation: {
        icon: "🦠",
        color: "green",
        shortDescription:
            "Enhanced flavours through controlled fermentation techniques",
        description:
            "Advanced fermentation techniques use controlled environments, specific yeasts, or extended fermentation times to develop unique flavour profiles. These methods often enhance fruity, floral, or complex characteristics.",
    },
    decaf: {
        icon: "🚫",
        color: "gray",
        shortDescription: "Caffeine removed while preserving original flavours",
        description:
            "Decaffeination processes remove caffeine while attempting to preserve the original flavour characteristics. Methods include Swiss Water Process, Ethyl Acetate (sugarcane), and CO2 extraction.",
    },
    experimental: {
        icon: "🧪",
        color: "pink",
        shortDescription: "Innovative techniques pushing flavour boundaries",
        description:
            "Experimental processes push the boundaries of traditional coffee processing. These include carbonic maceration, thermal shock, yeast inoculation, and other innovative techniques that create unique and often surprising flavour profiles.",
    },
    other: {
        icon: "❓",
        color: "gray",
        shortDescription: "Unique and specialty processing methods",
        description:
            "Unique processing methods that don't fit into traditional categories, often representing regional innovations or specialty techniques developed by individual producers.",
    },
};
