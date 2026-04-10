
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
		flavors: string[];
	}[];
	flavors?: string[]; // For categories without subtypes
	isDefect?: boolean;
}

export const TASTING_CONVERSATION: TastingConversationCategory[] = [
	{
		id: "fruity",
		name: "Fruity",
		emoji: "🍓",
		question: "What kind of fruit does it remind you of?",
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
		question: "Which floral character stands out?",
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
		question: "Which nut does it remind you of?",
		flavors: ["Nutty", "Almond", "Hazelnut", "Peanuts", "Walnut", "Pecan", "Cashew", "Pistachio"]
	},
	{
		id: "cocoa",
		name: "Cocoa",
		emoji: "🍫",
		question: "What kind of chocolate comes to mind?",
		flavors: ["Chocolate", "Cocoa", "Dark Chocolate", "Milk Chocolate", "Baker's Chocolate", "Nibs"]
	},
	{
		id: "spicy",
		name: "Spicy",
		emoji: "🌶️",
		question: "What kind of spice do you notice?",
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
		question: "What is the earthy quality like?",
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
		question: "What kind of acidity or sourness do you perceive?",
		flavors: ["Sour Aromatics", "Citric Acid", "Malic Acid", "Tart", "Bright", "Crisp", "Phosphoric Acid"]
	},
	{
		id: "alcohol_fermented",
		name: "Alcohol/Fermented",
		emoji: "🍷",
		question: "Is there a fermented or boozy note?",
		flavors: ["Alcohol", "Whiskey", "Winey", "Fermented", "Rum", "Cognac", "Overripe"]
	},
	{
		id: "cereal",
		name: "Cereal",
		emoji: "🌾",
		question: "Is it more grainy or malty?",
		flavors: ["Grain", "Malt", "Oatmeal", "Bread", "Toast"]
	}
];

export const DEFECT_CONVERSATION: TastingConversationCategory[] = [
	{
		id: "stale_papery",
		name: "Stale/Papery",
		emoji: "📰",
		question: "Does it taste old or like paper?",
		flavors: ["Stale", "Papery", "Cardboard", "Dusty"],
		isDefect: true
	},
	{
		id: "chemical",
		name: "Chemical",
		emoji: "⚗️",
		question: "Are there any artificial or chemical notes?",
		flavors: ["Medicinal", "Rubber", "Petroleum", "Skunky", "Plastic"],
		isDefect: true
	},
	{
		id: "earthy_defects",
		name: "Musty/Off-earth",
		emoji: "🍄",
		question: "Is there an unpleasant earthy or moldy note?",
		flavors: ["Musty/Dusty", "Moldy/Damp", "Phenolic", "Animalic", "Meaty/Brothy"],
		isDefect: true
	},
	{
		id: "sour_defects",
		name: "Off-acids",
		emoji: "🤮",
		question: "Does it have a rancid or vinegary sourness?",
		flavors: ["Acetic Acid", "Butyric Acid", "Isovaleric Acid"],
		isDefect: true
	},
	{
		id: "roasted_defects",
		name: "Over-roasted",
		emoji: "💨",
		question: "Is it burnt or acrid?",
		flavors: ["Acrid", "Ashy", "Burnt"],
		isDefect: true
	},
	{
		id: "green_defects",
		name: "Under-developed",
		emoji: "🫛",
		question: "Does it taste raw or like dry hay?",
		flavors: ["Raw", "Under-ripe", "Beany"],
		isDefect: true
	}
];

export const MOUTHFEEL_QUESTIONS = [
	{
		id: "body",
		name: "Body",
		question: "How heavy or thick does the coffee feel?",
		options: ["Light/Thin", "Medium/Silky", "Heavy/Syrupy"]
	},
	{
		id: "texture",
		name: "Texture",
		question: "How would you describe the tactile sensation?",
		options: ["Crisp/Clean", "Round/Smooth", "Oily/Creamy", "Rough/Astringent"]
	},
	{
		id: "finish",
		name: "Finish",
		question: "How long does the aftertaste linger?",
		options: ["Short/Clean", "Medium", "Long/Lingering"]
	}
];

export const TASTE_BASICS_QUESTIONS = [
	{
		id: "sweetness",
		name: "Sweetness",
		question: "How sweet is the foundation of this coffee?",
		options: ["Low", "Medium", "High"]
	},
	{
		id: "acidity",
		name: "Acidity",
		question: "How intense is the acidity?",
		options: ["Mellow", "Balanced", "Vibrant", "Sharp"]
	},
	{
		id: "bitterness",
		name: "Bitterness",
		question: "Is there a noticeable bitterness?",
		options: ["None", "Pleasant", "Dominant"]
	}
];
