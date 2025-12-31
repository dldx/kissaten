export const varietalConfig: Record<
    string,
    { icon: string; color: string; shortDescription: string; description: string }
> = {
    typica: {
        icon: "🌱",
        color: "green",
        shortDescription:
            "Classic heritage variety known for exceptional cup quality and complex flavours",
        description:
            "One of the oldest known varieties, Typica is prized for its exceptional cup quality and complex flavour profiles. It forms the genetic foundation for many modern varieties.",
    },
    bourbon: {
        icon: "🍇",
        color: "purple",
        shortDescription:
            "Sweet, balanced varieties with rich body and wine-like characteristics",
        description:
            "Known for their sweet, wine-like characteristics and full body. Bourbon varieties often produce complex cups with excellent balance and natural sweetness.",
    },
    heirloom: {
        icon: "🏛️",
        color: "amber",
        shortDescription:
            "Indigenous and wild varieties with unique regional characteristics",
        description:
            "Indigenous and wild varieties that have evolved naturally in their native regions, particularly Ethiopia, offering unique and unrepeatable flavour profiles.",
    },
    geisha: {
        icon: "🌸",
        color: "pink",
        shortDescription:
            "Prized variety known for exceptional floral and jasmine-like flavours",
        description:
            "A highly prized variety known for its exceptional floral aromatics, jasmine-like characteristics, and clean, tea-like body with extraordinary complexity.",
    },
    sl_varieties: {
        icon: "🔬",
        color: "blue",
        shortDescription:
            "Scott Labs selections bred for disease resistance and quality",
        description:
            "Scott Labs selections developed in Kenya, bred for resistance to coffee diseases while producing exceptional cup quality with bright acidity and wine-like characteristics.",
    },
    hybrid: {
        icon: "🧬",
        color: "indigo",
        shortDescription:
            "Modern cultivars bred for productivity and environmental resilience",
        description:
            "Modern cultivars bred for specific traits like disease resistance, productivity, and environmental adaptation while maintaining quality characteristics.",
    },
    large_bean: {
        icon: "🫘",
        color: "yellow",
        shortDescription:
            "Varieties producing notably large beans with unique characteristics",
        description:
            "Varieties producing notably large beans, such as Maragogipe and Pacamara, known for their distinct physical size and unique cup characteristics often featuring heavy body and complex notes.",
    },
    arabica_other: {
        icon: "☕",
        color: "orange",
        shortDescription:
            "Other distinct Arabica varieties with specialized characteristics",
        description:
            "Other distinct Arabica varieties with specialized characteristics that don't fit into the main families but offer unique and valuable flavour profiles.",
    },
    other: {
        icon: "❓",
        color: "gray",
        shortDescription: "Unique and specialty coffee varieties",
        description:
            "Unique and specialty coffee varieties including rare discoveries, experimental cross-breeds, and uncategorized local cultivars.",
    },
};
