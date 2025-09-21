import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

/**
 * Get the display name for a country, preferring full name over code
 */
export function getCountryDisplayName(countryCode: string, countryFullName?: string | null): string {
	return countryFullName || countryCode || 'Unknown';
}
/**
 * Format price with currency symbol
 */
export function formatPrice(price: number | null, currency: string): string {
	if (price === null) return 'N/A';
	return new Intl.NumberFormat('en-US', {
		style: 'currency',
		currency: currency || 'EUR'
	}).format(price);
}

/**
 * Get country flag emoji based on ISO alpha-2 code
 */
export function getCountryFlag(countryCode: string): string {
	const flags: Record<string, string> = {
		'AF': '🇦🇫', 'AL': '🇦🇱', 'DZ': '🇩🇿', 'AD': '🇦🇩', 'AO': '🇦🇴', 'AG': '🇦🇬', 'AR': '🇦🇷', 'AM': '🇦🇲',
		'AU': '🇦🇺', 'AT': '🇦🇹', 'AZ': '🇦🇿', 'BS': '🇧🇸', 'BH': '🇧🇭', 'BD': '🇧🇩', 'BB': '🇧🇧', 'BY': '🇧🇾',
		'BE': '🇧🇪', 'BZ': '🇧🇿', 'BJ': '🇧🇯', 'BT': '🇧🇹', 'BO': '🇧🇴', 'BA': '🇧🇦', 'BW': '🇧🇼', 'BR': '🇧🇷',
		'BN': '🇧🇳', 'BG': '🇧🇬', 'BF': '🇧🇫', 'BI': '🇧🇮', 'CV': '🇨🇻', 'KH': '🇰🇭', 'CM': '🇨🇲', 'CA': '🇨🇦',
		'CF': '🇨🇫', 'TD': '🇹🇩', 'CL': '🇨🇱', 'CN': '🇨🇳', 'CO': '🇨🇴', 'KM': '🇰🇲', 'CG': '🇨🇬', 'CD': '🇨🇩',
		'CR': '🇨🇷', 'CI': '🇨🇮', 'HR': '🇭🇷', 'CU': '🇨🇺', 'CY': '🇨🇾', 'CZ': '🇨🇿', 'DK': '🇩🇰', 'DJ': '🇩🇯',
		'DM': '🇩🇲', 'DO': '🇩🇴', 'EC': '🇪🇨', 'EG': '🇪🇬', 'SV': '🇸🇻', 'GQ': '🇬🇶', 'ER': '🇪🇷', 'EE': '🇪🇪',
		'SZ': '🇸🇿', 'ET': '🇪🇹', 'FJ': '🇫🇯', 'FI': '🇫🇮', 'FR': '🇫🇷', 'GA': '🇬🇦', 'GM': '🇬🇲', 'GE': '🇬🇪',
		'DE': '🇩🇪', 'GH': '🇬🇭', 'GR': '🇬🇷', 'GD': '🇬🇩', 'GT': '🇬🇹', 'GN': '🇬🇳', 'GW': '🇬🇼', 'GY': '🇬🇾',
		'HT': '🇭🇹', 'HN': '🇭🇳', 'HU': '🇭🇺', 'IS': '🇮🇸', 'IN': '🇮🇳', 'ID': '🇮🇩', 'IR': '🇮🇷', 'IQ': '🇮🇶',
		'IE': '🇮🇪', 'IL': '🇮🇱', 'IT': '🇮🇹', 'JM': '🇯🇲', 'JP': '🇯🇵', 'JO': '🇯🇴', 'KZ': '🇰🇿', 'KE': '🇰🇪',
		'KI': '🇰🇮', 'KP': '🇰🇵', 'KR': '🇰🇷', 'KW': '🇰🇼', 'KG': '🇰🇬', 'LA': '🇱🇦', 'LV': '🇱🇻', 'LB': '🇱🇧',
		'LS': '🇱🇸', 'LR': '🇱🇷', 'LY': '🇱🇾', 'LI': '🇱🇮', 'LT': '🇱🇹', 'LU': '🇱🇺', 'MG': '🇲🇬', 'MW': '🇲🇼',
		'MY': '🇲🇾', 'MV': '🇲🇻', 'ML': '🇲🇱', 'MT': '🇲🇹', 'MH': '🇲🇭', 'MR': '🇲🇷', 'MU': '🇲🇺', 'MX': '🇲🇽',
		'FM': '🇫🇲', 'MD': '🇲🇩', 'MC': '🇲🇨', 'MN': '🇲🇳', 'ME': '🇲🇪', 'MA': '🇲🇦', 'MZ': '🇲🇿', 'MM': '🇲🇲',
		'NA': '🇳🇦', 'NR': '🇳🇷', 'NP': '🇳🇵', 'NL': '🇳🇱', 'NZ': '🇳🇿', 'NI': '🇳🇮', 'NE': '🇳🇪', 'NG': '🇳🇬',
		'MK': '🇲🇰', 'NO': '🇳🇴', 'OM': '🇴🇲', 'PK': '🇵🇰', 'PW': '🇵🇼', 'PS': '🇵🇸', 'PA': '🇵🇦', 'PG': '🇵🇬',
		'PY': '🇵🇾', 'PE': '🇵🇪', 'PH': '🇵🇭', 'PL': '🇵🇱', 'PT': '🇵🇹', 'QA': '🇶🇦', 'RO': '🇷🇴', 'RU': '🇷🇺',
		'RW': '🇷🇼', 'KN': '🇰🇳', 'LC': '🇱🇨', 'VC': '🇻🇨', 'WS': '🇼🇸', 'SM': '🇸🇲', 'ST': '🇸🇹', 'SA': '🇸🇦',
		'SN': '🇸🇳', 'RS': '🇷🇸', 'SC': '🇸🇨', 'SL': '🇸🇱', 'SG': '🇸🇬', 'SK': '🇸🇰', 'SI': '🇸🇮', 'SB': '🇸🇧',
		'SO': '🇸🇴', 'ZA': '🇿🇦', 'SS': '🇸🇸', 'ES': '🇪🇸', 'LK': '🇱🇰', 'SD': '🇸🇩', 'SR': '🇸🇷', 'SE': '🇸🇪',
		'CH': '🇨🇭', 'SY': '🇸🇾', 'TJ': '🇹🇯', 'TZ': '🇹🇿', 'TH': '🇹🇭', 'TL': '🇹🇱', 'TG': '🇹🇬', 'TO': '🇹🇴',
		'TT': '🇹🇹', 'TN': '🇹🇳', 'TR': '🇹🇷', 'TM': '🇹🇲', 'TV': '🇹🇻', 'UG': '🇺🇬', 'UA': '🇺🇦', 'AE': '🇦🇪',
		'GB': '🇬🇧', 'US': '🇺🇸', 'UY': '🇺🇾', 'UZ': '🇺🇿', 'VU': '🇻🇺', 'VE': '🇻🇪', 'VN': '🇻🇳', 'YE': '🇾🇪',
		'ZM': '🇿🇲', 'ZW': '🇿🇼'
	};
	return flags[countryCode] || '🌍';
}

/**
 * Get the appropriate icon for a processing method
 */
export function getProcessIcon(processName: string): string {
	const process = processName.toLowerCase();
	if (process.includes('washed') || process.includes('wet')) return 'mdi:water';
	if (process.includes('natural') || process.includes('dry')) return 'mdi:white-balance-sunny';
	if (process.includes('anaerobic')) return 'mdi:flask';
	if (process.includes('honey') || process.includes('pulped')) return 'mdi:hexagon';
	if (process.includes('ferment')) return 'mdi:bacteria';
	if (process.includes('experimental') || process.includes('carbonic')) return 'mdi:test-tube';
	if (process.includes('decaf')) return 'mdi:coffee-off';
	return 'mdi:cog';
}

/**
 * Get the processing method category for styling/theming
 */
export function getProcessCategory(processName: string): string {
	const process = processName.toLowerCase();
	if (process.includes('washed') || process.includes('wet')) return 'washed';
	if (process.includes('natural') || process.includes('dry')) return 'natural';
	if (process.includes('anaerobic')) return 'anaerobic';
	if (process.includes('honey') || process.includes('pulped')) return 'honey';
	if (process.includes('ferment')) return 'fermentation';
	if (process.includes('experimental') || process.includes('carbonic')) return 'experimental';
	if (process.includes('decaf')) return 'decaf';
	return 'other';
}

/**
 * Get processing method category configuration for theming
 */
export function getProcessCategoryConfig(category: string): { gradient: string; icon: string } {
	const configs: Record<string, { gradient: string; icon: string }> = {
		washed: {
			gradient: 'from-blue-500 to-blue-600',
			icon: 'mdi:water'
		},
		natural: {
			gradient: 'from-orange-500 to-orange-600',
			icon: 'mdi:white-balance-sunny'
		},
		anaerobic: {
			gradient: 'from-purple-500 to-purple-600',
			icon: 'mdi:flask'
		},
		honey: {
			gradient: 'from-yellow-500 to-yellow-600',
			icon: 'mdi:hexagon'
		},
		fermentation: {
			gradient: 'from-indigo-500 to-indigo-600',
			icon: 'mdi:bacteria'
		},
		experimental: {
			gradient: 'from-pink-500 to-pink-600',
			icon: 'mdi:test-tube'
		},
		decaf: {
			gradient: 'from-red-500 to-red-600',
			icon: 'mdi:coffee-off'
		},
		other: {
			gradient: 'from-gray-500 to-gray-600',
			icon: 'mdi:cog'
		}
	};
	return configs[category] || configs.other;
}

// Get category emoji
export const getCategoryEmoji = (category: string) => {
	const emojiMap: Record<string, string> = {
		'Fruity': '🍓',
		'Cocoa': '🍫',
		'Nutty': '🥜',
		'Floral': '🌸',
		'Sweet': '🍯',
		'Spicy': '🌶️',
		'Earthy': '🌱',
		'Roasted': '🔥',
		'Green/Vegetative': '🥬',
		'Sour/Fermented': '🍋',
		'Alcohol/Fermented': '🍷',
		'Chemical': '⚗️',
		'Papery/Musty': '📰',
		'Other': '☕'
	};
	return emojiMap[category] || '☕';
};

// Get category colors for styling
export const getFlavourCategoryColors = (category: string) => {
	const colorMap: Record<
		string,
		{
			bg: string;
			text: string;
			border: string;
			darkBg: string;
			darkText: string;
			darkBorder: string;
		}
	> = {
		Fruity: {
			// Brighter, more vibrant red or even a berry-like magenta
			bg: "bg-rose-100", // Soft, inviting fruit
			text: "text-rose-800",
			border: "border-rose-200",
			darkBg: "dark:bg-rose-900/30",
			darkText: "dark:text-rose-300",
			darkBorder: "dark:border-rose-700/50",
		},
		Cocoa: {
			// Richer, darker brown for chocolate
			bg: "bg-amber-50", // Lighter base to represent milk chocolate or cacao
			text: "text-amber-900", // Darker brown for text
			border: "border-amber-100",
			darkBg: "dark:bg-amber-950/30", // Even darker in dark mode
			darkText: "dark:text-amber-200",
			darkBorder: "dark:border-amber-800/50",
		},
		Nutty: {
			// Warmer, earthy brown for nuts
			bg: "bg-stone-100", // Softer, light brown like roasted nuts
			text: "text-stone-800",
			border: "border-stone-200",
			darkBg: "dark:bg-stone-900/30",
			darkText: "dark:text-stone-300",
			darkBorder: "dark:border-stone-700/50",
		},
		Floral: {
			// Delicate and soft, perhaps a lavender or light pink
			bg: "bg-fuchsia-50", // Softer, more delicate floral pink/purple
			text: "text-fuchsia-800",
			border: "border-fuchsia-100",
			darkBg: "dark:bg-fuchsia-900/30",
			darkText: "dark:text-fuchsia-300",
			darkBorder: "dark:border-fuchsia-700/50",
		},
		Sweet: {
			// A warmer, inviting tone like caramel or honey
			bg: "bg-yellow-50", // Light, warm yellow for caramel, honey, vanilla
			text: "text-yellow-800",
			border: "border-yellow-100",
			darkBg: "dark:bg-yellow-900/30",
			darkText: "dark:text-yellow-300",
			darkBorder: "dark:border-yellow-700/50",
		},
		Spicy: {
			// A rich, warm orange or red-orange for spice
			bg: "bg-orange-100", // Classic warm spice color
			text: "text-orange-800",
			border: "border-orange-200",
			darkBg: "dark:bg-orange-900/30",
			darkText: "dark:text-orange-300",
			darkBorder: "dark:border-orange-700/50",
		},
		Earthy: {
			// Deeper, richer green or brown-green
			bg: "bg-lime-50", // Muted, earthy green, like moss or damp soil
			text: "text-lime-800",
			border: "border-lime-100",
			darkBg: "dark:bg-lime-900/30",
			darkText: "dark:text-lime-300",
			darkBorder: "dark:border-lime-700/50",
		},
		Roasted: {
			// Darker, robust brown, like a dark roast coffee bean
			bg: "bg-brown-100", // *Custom brown, see note below* - Or use neutral/stone if custom is not an option
			text: "text-brown-900",
			border: "border-brown-200",
			darkBg: "dark:bg-brown-950/30",
			darkText: "dark:text-brown-200",
			darkBorder: "dark:border-brown-800/50",
		},
		"Green/Vegetative": {
			// Fresh, vibrant green
			bg: "bg-emerald-50", // Bright, fresh green like leafy vegetables or grass
			text: "text-emerald-800",
			border: "border-emerald-100",
			darkBg: "dark:bg-emerald-900/30",
			darkText: "dark:text-emerald-300",
			darkBorder: "dark:border-emerald-700/50",
		},
		"Sour/Fermented": {
			// A sharp, slightly acidic yellow or light green
			bg: "bg-lime-50", // A slightly tart, acidic lime-green or a very light yellow
			text: "text-lime-800",
			border: "border-lime-100",
			darkBg: "dark:bg-lime-900/30",
			darkText: "dark:text-lime-300",
			darkBorder: "dark:border-lime-700/50",
		},
		"Alcohol/Fermented": {
			// Rich, deep purple or burgundy
			bg: "bg-violet-100", // A deeper, more mature purple for wine/spirit notes
			text: "text-violet-800",
			border: "border-violet-200",
			darkBg: "dark:bg-violet-900/30",
			darkText: "dark:text-violet-300",
			darkBorder: "dark:border-violet-700/50",
		},
		Chemical: {
			// Stark, cool, almost sterile blue or gray
			bg: "bg-slate-100", // Good choice already - neutral, somewhat unappealing
			text: "text-slate-800",
			border: "border-slate-200",
			darkBg: "dark:bg-slate-900/30",
			darkText: "dark:text-slate-300",
			darkBorder: "dark:border-slate-700/50",
		},
		"Papery/Musty": {
			// Desaturated, dull brown or gray
			bg: "bg-stone-50", // Light, slightly faded brown/beige like old paper
			text: "text-stone-800",
			border: "border-stone-100",
			darkBg: "dark:bg-stone-900/30",
			darkText: "dark:text-stone-300",
			darkBorder: "dark:border-stone-700/50",
		},
		Other: {
			// Neutral default
			bg: "bg-gray-100",
			text: "text-gray-800",
			border: "border-gray-200",
			darkBg: "dark:bg-gray-900/30",
			darkText: "dark:text-gray-300",
			darkBorder: "dark:border-gray-700/50",
		},
	};
	return (
		colorMap[category] || {
			bg: "bg-gray-100",
			text: "text-gray-800",
			border: "border-gray-200",
			darkBg: "dark:bg-gray-900/30",
			darkText: "dark:text-gray-300",
			darkBorder: "dark:border-gray-700/50",
		}
	);
};