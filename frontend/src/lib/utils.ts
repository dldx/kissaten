import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import WaterIcon from 'virtual:icons/mdi/water';
import SunIcon from 'virtual:icons/mdi/white-balance-sunny';
import FlaskIcon from 'virtual:icons/mdi/flask';
import HexagonIcon from 'virtual:icons/mdi/hexagon';
import BacteriaIcon from 'virtual:icons/mdi/bacteria';
import TestTubeIcon from 'virtual:icons/mdi/test-tube';
import CoffeeOffIcon from 'virtual:icons/mdi/coffee-off';
import CogIcon from 'virtual:icons/mdi/cog';
import BarrelIcon from 'virtual:icons/mdi/barrel';
import FruitCherries from 'virtual:icons/mdi/fruit-cherries';
import ThermometerIcon from 'virtual:icons/mdi/thermometer';
import TreePalmIcon from 'virtual:icons/mdi/palm-tree';


export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

/**
 * Resize an image File to fit within maxWidth × maxHeight, returning a JPEG File.
 * If the image is already smaller than the limits it is returned unchanged (in JPEG format).
 */
export function resizeImage(
	file: File,
	maxWidth: number,
	maxHeight: number,
): Promise<File> {
	return new Promise((resolve, reject) => {
		const img = document.createElement("img");
		img.src = URL.createObjectURL(file);
		img.onload = () => {
			const canvas = document.createElement("canvas");
			const ctx = canvas.getContext("2d");
			if (!ctx) {
				return reject(new Error("Could not get canvas context"));
			}

			let { width, height } = img;
			const ratio = Math.min(maxWidth / width, maxHeight / height);

			if (ratio < 1) {
				width *= ratio;
				height *= ratio;
			}

			canvas.width = width;
			canvas.height = height;

			ctx.drawImage(img, 0, 0, width, height);

			canvas.toBlob(
				(blob) => {
					if (!blob) {
						return reject(new Error("Canvas to Blob conversion failed"));
					}
					resolve(new File([blob], file.name, {
						type: "image/jpeg",
						lastModified: Date.now(),
					}));
				},
				"image/jpeg",
				0.9,
			);
		};
		img.onerror = () => reject(new Error("Image load error"));
	});
}

/**
 * Normalize a region name for use in URLs.
 */
export function normalizeRegionName(region: string): string {
	return region
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '') // Remove accents
		.toLowerCase()
		.replace(/[^\w\s-]/g, '')
		.replace(/[\s_]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

/**
 * Normalize a farm name for use in URLs.
 */
export function normalizeFarmName(farm: string): string {
	return farm
		.normalize('NFD')
		.replace(/[\u0300-\u036f]/g, '') // Remove accents
		.toLowerCase()
		.replace(/[^\w\s-]/g, '')
		.replace(/[\s_]+/g, '-')
		.replace(/^-+|-+$/g, '');
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
export function getProcessIcon(processName: string): any {
	const process = processName.toLowerCase();
	if (process.includes('co-ferment') || process.includes('infuse') || process.includes('infusion')) return getProcessCategoryConfig('infused_cofermented').icon;
	if (process.includes('barrel')) return getProcessCategoryConfig('barrel_aged').icon;
	if (process.includes('anaerobic') || process.includes('carbonic') || process.includes('anoxic')) return getProcessCategoryConfig('anaerobic_carbonic').icon;
	if (process.includes('thermal shock') || process.includes('koji') || process.includes('lactic') || process.includes('yeast') || process.includes('nitrogen')) return getProcessCategoryConfig('advanced_technical').icon;
	if (process.includes('honey') || process.includes('pulped')) return getProcessCategoryConfig('honey').icon;
	if (process.includes('washed') || process.includes('lavado')) return getProcessCategoryConfig('washed').icon;
	if (process.includes('natural') || process.includes('dry') || process.includes('sun-dried')) return getProcessCategoryConfig('natural').icon;
	if (process.includes('giling basah') || process.includes('wet hulled')) return getProcessCategoryConfig('wet_hulled').icon;
	if (process.includes('decaf') || process.includes('sugarcane') || process.includes('swiss water')) return getProcessCategoryConfig('decaf').icon;
	if (process.includes('experimental')) return getProcessCategoryConfig('experimental').icon;
	return getProcessCategoryConfig('other').icon;
}

/**
 * Get the processing method category for styling/theming
 */
export function getProcessCategory(processName: string): string {
	const process = processName.toLowerCase();
	if (process.includes('co-ferment') || process.includes('infuse') || process.includes('infusion')) return 'infused_cofermented';
	if (process.includes('barrel')) return 'barrel_aged';
	if (process.includes('anaerobic') || process.includes('carbonic') || process.includes('anoxic')) return 'anaerobic_carbonic';
	if (process.includes('thermal shock') || process.includes('koji') || process.includes('lactic') || process.includes('yeast') || process.includes('nitrogen')) return 'advanced_technical';
	if (process.includes('honey') || process.includes('pulped')) return 'honey';
	if (process.includes('washed') || process.includes('lavado')) return 'washed';
	if (process.includes('natural') || process.includes('dry') || process.includes('sun-dried')) return 'natural';
	if (process.includes('giling basah') || process.includes('wet hulled')) return 'wet_hulled';
	if (process.includes('decaf') || process.includes('sugarcane') || process.includes('swiss water')) return 'decaf';
	if (process.includes('experimental')) return 'experimental';
	return 'other';
}

/**
 * Get processing method category configuration for theming
 */
export function getProcessCategoryConfig(category: string): { gradient: string; icon: any } {
	const configs: Record<string, { gradient: string; icon: any }> = {
		infused_cofermented: {
			gradient: 'from-rose-500 to-rose-600',
			icon: FruitCherries
		},
		barrel_aged: {
			gradient: 'from-amber-700 to-amber-800',
			icon: BarrelIcon
		},
		anaerobic_carbonic: {
			gradient: 'from-purple-500 to-purple-600',
			icon: FlaskIcon
		},
		advanced_technical: {
			gradient: 'from-teal-500 to-teal-600',
			icon: ThermometerIcon
		},
		washed: {
			gradient: 'from-blue-500 to-blue-600',
			icon: WaterIcon
		},
		natural: {
			gradient: 'from-orange-500 to-orange-600',
			icon: SunIcon
		},
		honey: {
			gradient: 'from-yellow-500 to-yellow-600',
			icon: HexagonIcon
		},
		wet_hulled: {
			gradient: 'from-emerald-500 to-emerald-600',
			icon: TreePalmIcon
		},
		decaf: {
			gradient: 'from-red-500 to-red-600',
			icon: CoffeeOffIcon
		},
		experimental: {
			gradient: 'from-pink-500 to-pink-600',
			icon: TestTubeIcon
		},
		other: {
			gradient: 'from-gray-500 to-gray-600',
			icon: CogIcon
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
		'Amplitude': '📈',
		'Cereal': '🌾',
		'Mouthfeel': '👅',
		'Sour/Acid': '🧪',
		'Spices': '🫚',
		'Taste Basics': '👅',
		'Chemical': '⚗️',
		'Papery/Musty': '📰',
		'Other': '☕'
	};
	return emojiMap[category] || '☕';
};

// Canonical category order for consistent display and coloring
export const FLAVOUR_CATEGORY_ORDER = [
	'Fruity',
	'Floral',
	'Sweet',
	'Nutty',
	'Cocoa',
	'Spicy',
	'Roasted',
	'Earthy',
	'Green/Vegetative',
	'Sour/Fermented',
	'Sour/Acid',
	'Alcohol/Fermented',
	'Chemical',
	'Papery/Musty',
	'Cereal',
	'Mouthfeel',
	'Amplitude',
	'Spices',
	'Taste Basics',
	'Other'
] as const;

// Get category hex color for chart
export const getFlavourCategoryHexColor = (category: string): string => {
	const colorMap: Record<string, string> = {
		Fruity: '#f43f5e', // rose-500
		Cocoa: '#92400e', // amber-800
		Nutty: '#78716c', // stone-500
		Floral: '#d946ef', // fuchsia-500
		Sweet: '#eab308', // yellow-500
		Spicy: '#f97316', // orange-500
		Earthy: '#65a30d', // lime-600
		Roasted: '#292524', // stone-800
		'Green/Vegetative': '#10b981', // emerald-500
		'Sour/Fermented': '#84cc16', // lime-500
		'Alcohol/Fermented': '#8b5cf6', // violet-500
		Chemical: '#64748b', // slate-500
		'Papery/Musty': '#a8a29e', // stone-400
		Other: '#6b7280', // gray-500
		Amplitude: '#3b82f6', // blue-500
		Cereal: '#ca8a04', // yellow-600
		Mouthfeel: '#ec4899', // pink-500
		'Sour/Acid': '#84cc16', // lime-500
		Spices: '#f97316', // orange-500
		'Taste Basics': '#9ca3af' // gray-400
	};
	return colorMap[category] || '#6b7280'; // gray-500 default
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

// Function to construct final image URL from Wikidata image name
export async function constructWikiImageUrl(imageName: string): Promise<string> {
	const { createHash } = await import('node:crypto');
	// Replace spaces with underscores
	const normalizedName = imageName.replace(/ /g, '_');

	// Calculate MD5 hash of the normalized name
	const hash = await createHash('md5').update(normalizedName).digest('hex');

	// Get first two characters of MD5 hash
	const a = hash[0];
	const b = hash[1];

	// Construct final URL
	// return `https://upload.wikimedia.org/wikipedia/commons/${a}/${a}${b}/${normalizedName}`;
	return `https://upload.wikimedia.org/wikipedia/commons/thumb/${a}/${a}${b}/${normalizedName}/1000px-${normalizedName}.png`
}

// Function to get images from Wikidata for any item using wbgetclaims
export async function searchItemsWithImages(searchTerms: string[], fetchFn: typeof fetch = fetch) {
	let limit = 5; // Limit number of search results to process
	let searchTerm = searchTerms[0]; // Use the first term for searching
	try {
		let searchResults: { id: string }[] = [];
		// If searchTerm is an ID, eg Q123456, use it directly instead of searching
		if (searchTerm.match(/^Q\d+$/)) {
			searchResults = [{
				id: searchTerm,
			}];
		}
		else {
			// Get search results
			const searchUrl = `https://www.wikidata.org/w/api.php?action=wbsearchentities&search=${encodeURIComponent(searchTerm)}&language=en&format=json&limit=${limit}&origin=*`;

			const searchResponse = await fetchFn(searchUrl);
			const searchData = await searchResponse.json();

			if (searchData.search.length === 0) {
				if (searchTerms.length === 1) return [] // No results and no more terms to try
				// Try next search term
				return await searchItemsWithImages(searchTerms.slice(1), fetchFn);
			}
			searchResults = searchData.search;
		}

		// Get detailed info for each item
		const results = [];
		for (const item of searchResults) {
			// Use wbgetclaims to get image claims (P18)
			const claimsUrl = `https://www.wikidata.org/w/api.php?action=wbgetclaims&property=P18&entity=${item.id}&format=json&origin=*`;

			try {
				const claimsResponse = await fetchFn(claimsUrl);
				const claimsData = await claimsResponse.json();

				// Check if item has images (P18)
				if (claimsData.claims && claimsData.claims.P18) {
					// Process first image claim
					const imagePromises = claimsData.claims.P18.slice(0, 1).map(async (claim: any) => {
						const imageName = claim.mainsnak.datavalue.value;
						return await constructWikiImageUrl(imageName);
					});

					const images = await Promise.all(imagePromises);

					// // Get basic info for the item
					// const entityUrl = `https://www.wikidata.org/w/api.php?action=wbgetentities&ids=${item.id}&props=labels|descriptions&languages=en&format=json&origin=*`;
					// const entityResponse = await fetchFn(entityUrl);
					// const entityData = await entityResponse.json();
					// const entity = entityData.entities[item.id];

					results.push({
						id: item.id,
						// label: entity.labels?.en?.value || item.label,
						// description: entity.descriptions?.en?.value || item.description || 'No description',
						images: images
					});
					break;
				}
			} catch (error) {
				console.error(`Error fetching claims for entity ${item.id}:`, error);
			}
		}
		return results;

	} catch (error) {
		console.error('Error searching items with images:', error);
		if (searchTerms.length === 1) return [];
		// Try next search term
		return await searchItemsWithImages(searchTerms.slice(1), fetchFn);
	}
}



// API endpoint for available flavour images
export const getAvailableFlavourImages = async (fetchFn: typeof fetch): Promise<Array<{ note: string; filename: string; url: string; image_author?: string; image_license?: string; image_license_url?: string }>> => {
	const res = await fetchFn('/api/v1/flavour-images');
	if (!res.ok) return [];
	const data = await res.json();
	return data?.data ?? [];
};

// Helper to normalize flavour note for matching
export function normalizeNote(note: string): string {
	return note
		.toLowerCase()
		.replace(/_/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
}

// Given an array of flavour notes, return the first matching image URL (or null)
export async function getFlavourImageFromAvailable(flavours: string[], availableImages: Array<{ note: string; filename: string; url: string; image_author?: string; image_license?: string; image_license_url?: string }>): Promise<{ url: string; attribution: { image_author?: string; image_license?: string; image_license_url?: string } } | null> {
	try {
		for (const note of flavours) {
			const normalized = normalizeNote(note);
			const match = availableImages.find(img => normalizeNote(img.note) === normalized);
			if (match) {
				return {
					url: match.url,
					attribution: {
						image_author: match.image_author,
						image_license: match.image_license,
						image_license_url: match.image_license_url
					}
				};
			}
		}
	} catch (error) {
		console.error('Error fetching available flavour images:', error);
	}
	return null;
}

/**
 * Add UTM parameters to a URL
 * Preserves existing query parameters and hash fragments
 */
export function addUtmParams(url: string, params: { source: string; medium: string; campaign?: string }): string {
	try {
		const urlObj = new URL(url);
		urlObj.searchParams.set('utm_source', params.source);
		urlObj.searchParams.set('utm_medium', params.medium);
		if (params.campaign) {
			urlObj.searchParams.set('utm_campaign', params.campaign);
		}
		return urlObj.toString();
	} catch (e) {
		// If URL parsing fails, return original URL
		console.warn('Failed to add UTM params to URL:', url, e);
		return url;
	}
}