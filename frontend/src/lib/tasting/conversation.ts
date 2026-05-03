
export interface TastingConversationCategory {
	id: string;
	name: string;
	emoji: string;
	question: string;
	subTypeQuestion?: string; // Question to ask when selecting sub-categories
	subTypes?: {
		id: string;
		name: string;
		emoji: string;
		flavors: (string | { name: string; count: number })[];
	}[];
	flavors?: (string | { name: string; count: number })[]; // Support both simple and rich flavours
	isDefect?: boolean;
}

export interface TastingQuestion {
	id: string;
	name: string;
	description?: string;
	question: string;
	options: string[];
}


/**
 * Mapping for categories that have different names in API vs Skeleton
 */
export const CATEGORY_MAPPINGS: Record<string, string> = {
	"Spicy": "Spices",
	"Roasted": "Roasted", // Standard, but good to have for consistency
	"Defects": "Stale/Papery" // Example if we wanted to map defects
};

export interface TastingNoteCategoryData {
	primary_category: string;
	secondary_category: string;
	tertiary_category: string | null;
	note_count: number;
	bean_count: number;
	tasting_notes: string[];
	tasting_notes_with_counts: { note: string; bean_count: number }[];
}

/**
 * Merges dynamic flavor data from the API into the hardcoded conversation structure.
 */
export function mergeDynamicFlavours(
	skeleton: TastingConversationCategory[],
	apiData: Record<string, TastingNoteCategoryData[]> | null
): TastingConversationCategory[] {
	if (!apiData) return skeleton;

	return skeleton.map(category => {
		const newCategory = { ...category };

		// Use mapping or defaults
		const apiKey = CATEGORY_MAPPINGS[category.name] || category.name;
		const apiCategoryData = apiData[apiKey];

		console.log(`Matching skeleton category "${category.name}" (apiKey: "${apiKey}") -> data found: ${!!apiCategoryData}`);

		if (!apiCategoryData) return newCategory;

		if (newCategory.subTypes) {
			newCategory.subTypes = newCategory.subTypes.map(subType => {
				const newSubType = { ...subType };
				// Find all notes for this secondary category
				const notesWithCounts = apiCategoryData
					.filter(d => {
						if (!d.secondary_category) return false;
						const sec = d.secondary_category.toLowerCase();
						return sec === subType.name.toLowerCase() || sec === subType.id.toLowerCase();
					})
					.flatMap(d => d.tasting_notes_with_counts);

				if (notesWithCounts.length > 0) {
					// Group and aggregate counts (some notes might appear in multiple tertiary categories)
					const notesMap = new Map<string, number>();
					notesWithCounts.forEach(nc => {
						notesMap.set(nc.note, (notesMap.get(nc.note) || 0) + nc.bean_count);
					});

					newSubType.flavors = Array.from(notesMap.entries())
						.sort((a, b) => b[1] - a[1])
						.map(([name, count]) => ({ name, count }));

					if (newSubType.flavors.length < 3) {
						const originalFlavors = subType.flavors
							.filter(f => {
								const fName = typeof f === 'string' ? f : f.name;
								return !newSubType.flavors.some(nf => (typeof nf === 'string' ? nf : nf.name) === fName);
							})
							.map(f => typeof f === 'string' ? { name: f, count: 0 } : f);
						newSubType.flavors = [...newSubType.flavors, ...originalFlavors];
					}
				}
				return newSubType;
			});
		} else if (newCategory.flavors) {
			// Merge for categories without subtypes
			const notesMap = new Map<string, number>();
			apiCategoryData.forEach(d => {
				d.tasting_notes_with_counts.forEach(nc => {
					notesMap.set(nc.note, (notesMap.get(nc.note) || 0) + nc.bean_count);
				});
			});

			if (notesMap.size > 0) {
				const topNotes = Array.from(notesMap.entries())
					.sort((a, b) => b[1] - a[1])
					.map(([name, count]) => ({ name, count }));

				newCategory.flavors = topNotes;

				if (newCategory.flavors.length < 3) {
					const originalFlavors = category.flavors!
						.filter(f => {
							const fName = typeof f === 'string' ? f : f.name;
							return !newCategory.flavors!.some(nf => (typeof nf === 'string' ? nf : nf.name) === fName);
						})
						.map(f => typeof f === 'string' ? { name: f, count: 0 } : f);
					newCategory.flavors = [...newCategory.flavors as any[], ...originalFlavors];
				}
			}
		}

		return newCategory;
	});
}

export const TASTING_CONVERSATION: TastingConversationCategory[] = [
	{
		id: "fruity",
		name: "Fruity",
		emoji: "🍓",
		question: "Any specific fruit vibes coming through?",
		subTypeQuestion: "Which fruit family do you notice first?",
		subTypes: [
			{
				id: "berry",
				name: "Berry",
				emoji: "🫐",
				flavors: ["Blackberry", "Blackcurrant", "Blueberry", "Cranberry", "Gooseberry", "Raspberry", "Red Berry", "Red Fruit", "Redcurrant", "Strawberry"]
			},
			{
				id: "citrus",
				name: "Citrus Fruit",
				emoji: "🍊",
				flavors: ["Bergamot", "Grapefruit", "Lemon", "Lime", "Orange", "Pomelo", "Yuzu"]
			},
			{
				id: "dried",
				name: "Dried Fruit",
				emoji: "🍇",
				flavors: ["Date", "Fig", "Prune", "Raisin"]
			},
			{
				id: "tropical",
				name: "Tropical Fruit",
				emoji: "🍍",
				flavors: ["Coconut", "Guava", "Kiwi", "Lychee", "Mango", "Passion Fruit", "Pineapple"]
			},
			{
				id: "stone",
				name: "Stone Fruit",
				emoji: "🍑",
				flavors: ["Apricot", "Cherry", "Peach", "Plum", "Nectarine"]
			},
			{
				id: "other_fruit",
				name: "Other Fruit",
				emoji: "🍎",
				flavors: ["Apple", "Banana", "Grape", "Honeydew Melon", "Melon", "Pear", "Persimmon", "Pomegranate", "Watermelon"]
			}
		]
	},
	{
		id: "floral",
		name: "Floral",
		emoji: "🌸",
		question: "What kind of floral notes can you catch?",
		flavors: ["Floral", "Rose", "Jasmine", "Chamomile", "Black Tea", "Hibiscus", "Lavender", "Orange Blossom"]
	},
	{
		id: "sweet",
		name: "Sweet",
		emoji: "🍯",
		question: "What does the sweetness remind you of?",
		flavors: ["Molasses", "Maple Syrup", "Brown Sugar", "Caramelized", "Honey", "Vanilla", "Vanillin", "Sweet Aromatics", "Overall Sweet", "Toffee", "Butterscotch"]
	},
	{
		id: "nutty",
		name: "Nutty",
		emoji: "🥜",
		question: "Getting any nutty characteristics?",
		flavors: ["Nutty", "Almond", "Hazelnut", "Peanuts", "Walnut", "Pecan", "Cashew", "Pistachio"]
	},
	{
		id: "cocoa",
		name: "Cocoa",
		emoji: "🍫",
		question: "Is there a chocolatey side to it?",
		flavors: ["Chocolate", "Cocoa", "Dark Chocolate", "Milk Chocolate", "Baker's Chocolate", "Nibs"]
	},
	{
		id: "spicy",
		name: "Spicy",
		emoji: "🌶️",
		question: "Notice any warm or spice notes?",
		flavors: ["Pungent", "Pepper", "Anise", "Nutmeg", "Brown Spice", "Cinnamon", "Clove", "Ginger", "Cardamom"]
	},
	{
		id: "roasted",
		name: "Roasted",
		emoji: "🔥",
		question: "How would you describe the roast character?",
		flavors: ["Tobacco", "Pipe Tobacco", "Smoky", "Roasted", "Brown, Roast", "Toasted", "Caramelized"]
	},
	{
		id: "earthy",
		name: "Earthy",
		emoji: "🌱",
		question: "What's the earthy quality like?",
		flavors: ["Woody", "Musty/Earthy", "Earthy", "Forest Floor", "Fresh Soil", "Damp Wood"]
	},
	{
		id: "green_vegetative",
		name: "Green/Vegetative",
		emoji: "🥬",
		question: "Does it have a fresh or green character?",
		flavors: ["Olive Oil", "Green", "Fresh", "Dark Green", "Vegetative", "Hay-like", "Herb-like", "Peapod", "Grassy"]
	},
	{
		id: "sour_acid",
		name: "Sour/Acid",
		emoji: "🧪",
		question: "How's the acidity showing up?",
		flavors: ["Sour Aromatics", "Citric Acid", "Malic Acid", "Tart", "Bright", "Crisp", "Phosphoric Acid"]
	},
	{
		id: "alcohol_fermented",
		name: "Alcohol/Fermented",
		emoji: "🍷",
		question: "Any boozy or fermented notes in there?",
		flavors: ["Alcohol", "Whiskey", "Winey", "Fermented", "Rum", "Cognac", "Overripe"]
	},
	{
		id: "cereal",
		name: "Cereal",
		emoji: "🌾",
		question: "Is it leaning towards grainy or malty?",
		flavors: ["Grain", "Malt", "Oatmeal", "Bread", "Toast"]
	}
];

export const DEFECT_CONVERSATION: TastingConversationCategory[] = [
	{
		id: "stale_papery",
		name: "Stale/Papery",
		emoji: "📰",
		question: "Any hints of it tasting a bit old or like paper?",
		flavors: ["Stale", "Papery", "Cardboard", "Dusty"],
		isDefect: true
	},
	{
		id: "chemical",
		name: "Chemical",
		emoji: "⚗️",
		question: "Does it have any artificial or 'off' medicinal vibes?",
		flavors: ["Medicinal", "Rubber", "Petroleum", "Skunky", "Plastic"],
		isDefect: true
	},
	{
		id: "earthy_defects",
		name: "Musty/Off-earth",
		emoji: "🍄",
		question: "Is there an unpleasant damp or moldy note?",
		flavors: ["Musty/Dusty", "Moldy/Damp", "Phenolic", "Animalic", "Meaty/Brothy"],
		isDefect: true
	},
	{
		id: "sour_defects",
		name: "Off-acids",
		emoji: "🤮",
		question: "Is the sourness crossing into rancid or vinegary territory?",
		flavors: ["Acetic Acid", "Butyric Acid", "Isovaleric Acid"],
		isDefect: true
	},
	{
		id: "roasted_defects",
		name: "Over-roasted",
		emoji: "💨",
		question: "Does it taste unpleasantly burnt or acrid?",
		flavors: ["Acrid", "Ashy", "Burnt"],
		isDefect: true
	},
	{
		id: "green_defects",
		name: "Under-developed",
		emoji: "🫛",
		question: "Notice any raw, beany, or 'underflow' tastes?",
		flavors: ["Raw", "Under-ripe", "Beany"],
		isDefect: true
	}
];

export const MOUTHFEEL_QUESTIONS: TastingQuestion[] = [
	{
		id: "body",
		name: "Body",
		description: "Think of the weight on your tongue—like the difference between water and full cream.",
		question: "How heavy or thick does the coffee feel?",
		options: ["Light/Thin", "Medium/Silky", "Heavy/Syrupy"]
	},
	{
		id: "texture",
		name: "Texture",
		description: "How does it feel physically? Is it smooth, or does it leave your mouth feeling dry?",
		question: "How would you describe the tactile sensation?",
		options: ["Crisp/Clean", "Round/Smooth", "Oily/Creamy", "Rough/Astringent"]
	},
	{
		id: "finish",
		name: "Finish",
		description: "The flavors that linger after you've taken a sip. Does it stay with you?",
		question: "How long does that aftertaste stick around?",
		options: ["Short/Clean", "Medium", "Long/Lingering"]
	}
];

export const TASTE_BASICS_QUESTIONS: TastingQuestion[] = [
	{
		id: "sweetness",
		name: "Sweetness",
		description: "The underlying sugar-like quality that brings everything into balance.",
		question: "How sweet is the foundation of this cup?",
		options: ["Low", "Medium", "High"]
	},
	{
		id: "acidity",
		name: "Acidity",
		description: "The 'sparkle' or 'brightness'—think of that refreshingly crisp fruit sensation.",
		question: "How vibrant is the acidity?",
		options: ["Mellow", "Balanced", "Vibrant", "Sharp"]
	},
	{
		id: "bitterness",
		name: "Bitterness",
		description: "The sharp, cocoa-like or tea-like edge. In good coffee, it's pleasant and adds structure.",
		question: "Is there a noticeable bitterness?",
		options: ["None", "Pleasant", "Dominant"]
	}
];

