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