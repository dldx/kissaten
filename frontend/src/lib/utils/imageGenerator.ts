import { getFlavourCategoryHexColor, getCategoryEmoji } from '../utils';
import { TASTING_CONVERSATION, DEFECT_CONVERSATION } from '../tasting/conversation';
import type { CoffeeBean } from '../api';

export interface TastingImageOptions {
	sessionName?: string;
	dateOrNotes?: string;
	basics: Record<string, string>;
	mouthfeel: Record<string, string>;
	allSelectedNotesList: string[];
	beanData?: CoffeeBean | null;
	isDarkMode?: boolean;
}

/** Mirrors TastingSummaryCard's logic: find the parent category name for a given note string */
function findCategoryForNote(noteName: string): string | null {
	const categories = [...TASTING_CONVERSATION, ...DEFECT_CONVERSATION];
	const cat = categories.find(
		(c) =>
			c.name === noteName ||
			c.flavors?.some((f) => (typeof f === 'string' ? f : f.name) === noteName) ||
			c.subTypes?.some(
				(s) =>
					s.name === noteName ||
					s.flavors.some((f) => (typeof f === 'string' ? f : f.name) === noteName),
			),
	);
	return cat ? cat.name : null;
}

/** Returns canvas-compatible hex/rgba chip colours matching the app's getFlavourCategoryColors palette */
function getChipColors(categoryName: string, isDarkMode: boolean): { bg: string; text: string } {
	const light: Record<string, { bg: string; text: string }> = {
		Fruity:               { bg: '#ffe4e6', text: '#9f1239' }, // rose-100 / rose-800
		Cocoa:                { bg: '#fffbeb', text: '#78350f' }, // amber-50 / amber-900
		Nutty:                { bg: '#f5f5f4', text: '#292524' }, // stone-100 / stone-800
		Floral:               { bg: '#fdf4ff', text: '#86198f' }, // fuchsia-50 / fuchsia-800
		Sweet:                { bg: '#fefce8', text: '#854d0e' }, // yellow-50 / yellow-800
		Spicy:                { bg: '#ffedd5', text: '#9a3412' }, // orange-100 / orange-800
		Earthy:               { bg: '#f7fee7', text: '#3f6212' }, // lime-50 / lime-800
		Roasted:              { bg: '#f5f5f4', text: '#292524' }, // stone-100 / stone-800
		'Green/Vegetative':   { bg: '#ecfdf5', text: '#065f46' }, // emerald-50 / emerald-800
		'Sour/Fermented':     { bg: '#f7fee7', text: '#3f6212' }, // lime-50 / lime-800
		'Alcohol/Fermented':  { bg: '#ede9fe', text: '#5b21b6' }, // violet-100 / violet-800
		Chemical:             { bg: '#f1f5f9', text: '#1e293b' }, // slate-100 / slate-800
		'Papery/Musty':       { bg: '#fafaf9', text: '#292524' }, // stone-50 / stone-800
		Other:                { bg: '#f3f4f6', text: '#1f2937' }, // gray-100 / gray-800
	};
	const dark: Record<string, { bg: string; text: string }> = {
		Fruity:               { bg: 'rgba(136,19,55,0.3)',   text: '#fda4af' }, // rose-900/30 / rose-300
		Cocoa:                { bg: 'rgba(69,26,3,0.3)',     text: '#fde68a' }, // amber-950/30 / amber-200
		Nutty:                { bg: 'rgba(28,25,23,0.3)',    text: '#d6d3d1' }, // stone-900/30 / stone-300
		Floral:               { bg: 'rgba(112,26,117,0.3)',  text: '#f0abfc' }, // fuchsia-900/30 / fuchsia-300
		Sweet:                { bg: 'rgba(113,63,18,0.3)',   text: '#fde047' }, // yellow-900/30 / yellow-300
		Spicy:                { bg: 'rgba(124,45,18,0.3)',   text: '#fdba74' }, // orange-900/30 / orange-300
		Earthy:               { bg: 'rgba(54,83,20,0.3)',    text: '#bef264' }, // lime-900/30 / lime-300
		Roasted:              { bg: 'rgba(28,25,23,0.3)',    text: '#d6d3d1' }, // stone-900/30 / stone-300
		'Green/Vegetative':   { bg: 'rgba(6,78,59,0.3)',     text: '#6ee7b7' }, // emerald-900/30 / emerald-300
		'Sour/Fermented':     { bg: 'rgba(54,83,20,0.3)',    text: '#bef264' }, // lime-900/30 / lime-300
		'Alcohol/Fermented':  { bg: 'rgba(76,29,149,0.3)',   text: '#c4b5fd' }, // violet-900/30 / violet-300
		Chemical:             { bg: 'rgba(15,23,42,0.3)',    text: '#cbd5e1' }, // slate-900/30 / slate-300
		'Papery/Musty':       { bg: 'rgba(28,25,23,0.3)',    text: '#d6d3d1' }, // stone-900/30 / stone-300
		Other:                { bg: 'rgba(17,24,39,0.3)',    text: '#d1d5db' }, // gray-900/30 / gray-300
	};
	const map = isDarkMode ? dark : light;
	return map[categoryName] ?? (isDarkMode
		? { bg: 'rgba(17,24,39,0.3)', text: '#d1d5db' }
		: { bg: '#f3f4f6',           text: '#1f2937' });
}

export async function generateTastingImage(options: TastingImageOptions): Promise<Blob> {
	const { sessionName, dateOrNotes, basics, mouthfeel, allSelectedNotesList, beanData, isDarkMode = false } = options;

	// Use a scale factor for HiDPI/Retina output (e.g., 2x or 3x)
	const scale = 4;
	const baseWidth = 1000;
	const width = baseWidth * scale;
	const padding = 60 * scale;
	const logoSize = 120 * scale;

	// Font families from app.css
	const fonts = {
		fun: '"Knewave", sans-serif',
		heading: '"Cabin", sans-serif',
		sans: '"Quicksand", sans-serif'
	};

	// Theme colors
	const colors = {
		bg: isDarkMode ? '#09090b' : '#ffffff', // zinc-950 or white
		border: isDarkMode ? '#171717' : '#f1f1f1',
		title: isDarkMode ? '#fafafa' : '#171717',
		text: isDarkMode ? '#e5e5e5' : '#404040',
		muted: isDarkMode ? '#a1a1aa' : '#737373', // zinc-400 or neutral-500
		separator: isDarkMode ? '#27272a' : '#e5e5e5', // zinc-800 or neutral-200
		chipBg: isDarkMode ? '#18181b' : '#f5f5f5', // zinc-900 or neutral-100
		chipText: isDarkMode ? '#d4d4d8' : '#404040', // zinc-300 or neutral-600
		footer: isDarkMode ? '#3f3f46' : '#a3a3a3', // zinc-600 or neutral-400
		success: isDarkMode ? '#10b981' : '#059669', // emerald-500 or emerald-600
		beanBg: isDarkMode ? 'rgba(15, 23, 42, 0.8)' : 'rgba(16, 185, 129, 0.05)', // slate-900 or emerald-500/5
		beanBorder: isDarkMode ? 'rgba(6, 182, 212, 0.3)' : 'rgba(16, 185, 129, 0.2)', // cyan-500 or emerald-500/20
		tagProcessBg: isDarkMode ? 'rgba(8, 145, 178, 0.4)' : '#dbeafe', // cyan-900/40 or blue-100
		tagProcessText: isDarkMode ? '#c4f1f9' : '#1e40af', // cyan-200 or blue-800
		tagVarietyBg: isDarkMode ? 'rgba(6, 95, 70, 0.4)' : '#dcfce7', // emerald-900/40 or green-100
		tagVarietyText: isDarkMode ? '#a7f3d0' : '#166534' // emerald-200 or green-800
	};

	// Create temporary canvas to measure height
	const canvas = document.createElement('canvas');
	const tempCtx = canvas.getContext('2d')!;

	// Estimate height based on segments
	// Base height + extra for bean data if present
	let estimatedHeight = 1600;
	if (beanData) {
		estimatedHeight += 200;
		if (beanData.image_url) estimatedHeight += 350;
	}
	const canvasHeight = estimatedHeight * scale;

	canvas.width = width;
	canvas.height = canvasHeight;

	// Background
	tempCtx.fillStyle = colors.bg;
	tempCtx.fillRect(0, 0, width, canvasHeight);

	// Subtly styled background with a border/frame
	tempCtx.strokeStyle = colors.border;
	tempCtx.lineWidth = 20 * scale;
	tempCtx.strokeRect(0, 0, width, canvasHeight);

	// Load Logo
	try {
		const logo = new Image();
		// Use dark mode logo if applicable
		logo.src = isDarkMode ? '/logo_dark_full.svg' : '/logo_full.svg';
		await new Promise((resolve, reject) => {
			logo.onload = resolve;
			logo.onerror = reject;
		});
		const aspect = logo.width / logo.height;
		const drawWidth = logoSize * aspect;
		tempCtx.drawImage(logo, (width - drawWidth) / 2, padding, drawWidth, logoSize);
	} catch (e) {
		console.warn('Could not load logo for tasting image', e);
	}

	let currentY = padding + logoSize + 120 * scale;

	// Session Title
	tempCtx.textAlign = 'center';
	tempCtx.fillStyle = colors.title;
	tempCtx.font = `${56 * scale}px ${fonts.heading}`;
	tempCtx.fillText(sessionName || 'Coffee Tasting Session', width / 2, currentY);
	currentY += 60 * scale;

	// Date/Notes
	tempCtx.font = `${32 * scale}px ${fonts.sans}`;
	tempCtx.fillStyle = colors.muted;
	const dateStr = dateOrNotes || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
	tempCtx.fillText(dateStr, width / 2, currentY);
	currentY += 100 * scale;

	// --- Coffee Bean Section ---
	if (beanData) {
		currentY += 20 * scale;
		const beanSectionX = padding;
		const beanSectionWidth = width - (padding * 2);
		const beanPadding = 32 * scale;
		const innerContentX = beanSectionX + beanPadding;
		const imgSize = 200 * scale;

		// 1. Draw Container Background
		tempCtx.fillStyle = colors.beanBg;
		tempCtx.strokeStyle = colors.beanBorder;
		tempCtx.lineWidth = 2 * scale;
		tempCtx.beginPath();
		tempCtx.roundRect(beanSectionX, currentY, beanSectionWidth, imgSize + (beanPadding * 2), 24 * scale);
		tempCtx.fill();
		tempCtx.stroke();

		const contentStartY = currentY + beanPadding;

		// 2. Bean Image (Left aligned like the tile)
		let imageOffset = 0;
		if (beanData.image_url) {
			try {
				const beanImg = new Image();
				beanImg.crossOrigin = 'anonymous';
				beanImg.src = beanData.image_url;
				await new Promise((resolve, reject) => {
					beanImg.onload = resolve;
					beanImg.onerror = reject;
				});

				tempCtx.save();
				tempCtx.beginPath();
				tempCtx.roundRect(innerContentX, contentStartY, imgSize, imgSize, 20 * scale);
				tempCtx.clip();
				tempCtx.drawImage(beanImg, innerContentX, contentStartY, imgSize, imgSize);
				tempCtx.restore();

				imageOffset = imgSize + 32 * scale;
			} catch (e) {
				console.warn('Could not load bean image', e);
			}
		} else {
			// Placeholder like the tile
			tempCtx.fillStyle = isDarkMode ? 'rgba(8, 145, 178, 0.1)' : 'rgba(16, 185, 129, 0.05)';
			tempCtx.beginPath();
			tempCtx.roundRect(innerContentX, contentStartY, imgSize, imgSize, 20 * scale);
			tempCtx.fill();
			imageOffset = imgSize + 32 * scale;
		}

		// 3. Bean Content (Right of image)
		const textX = innerContentX + imageOffset;
		let textY = contentStartY + 30 * scale;

		// Roaster (Emerald small caps)
		tempCtx.textAlign = 'left';
		tempCtx.font = `bold ${24 * scale}px ${fonts.sans}`;
		tempCtx.fillStyle = isDarkMode ? '#67e8f9' : '#059669'; // cyan-300 or emerald-600
		tempCtx.fillText(beanData.roaster.toUpperCase(), textX, textY);
		textY += 45 * scale;

		// Bean Name
		tempCtx.font = `extrabold ${42 * scale}px ${fonts.heading}`;
		tempCtx.fillStyle = colors.title;
		tempCtx.fillText(beanData.name, textX, textY);
		textY += 50 * scale;

		// Origin line
		if (beanData.origins && beanData.origins.length > 0) {
			const first = beanData.origins[0];
			const originStr = [first.country_full_name || first.country, first.region].filter(Boolean).join(', ');
			if (originStr) {
				tempCtx.font = `bold ${28 * scale}px ${fonts.sans}`;
				tempCtx.fillStyle = isDarkMode ? '#6ee7b7' : '#374151'; // emerald-300 or gray-700
				tempCtx.fillText(originStr, textX, textY);
				textY += 50 * scale;
			}
		}

		// Tags (Process & Variety)
		const firstOrigin = beanData.origins?.[0];
		let tagX = textX;
		const drawTag = (text: string, bgColor: string, textColor: string) => {
			tempCtx.font = `${24 * scale}px ${fonts.sans}`;
			const metrics = tempCtx.measureText(text);
			const tagPadding = 16 * scale;
			const tagW = metrics.width + (tagPadding * 2);
			const tagH = 44 * scale;

			tempCtx.fillStyle = bgColor;
			tempCtx.beginPath();
			tempCtx.roundRect(tagX, textY - 32 * scale, tagW, tagH, 8 * scale);
			tempCtx.fill();

			tempCtx.fillStyle = textColor;
			tempCtx.fillText(text, tagX + tagPadding, textY);
			tagX += tagW + 12 * scale;
		};

		if (firstOrigin?.process) {
			drawTag(firstOrigin.process, colors.tagProcessBg, colors.tagProcessText);
		}

		// Use variety_canonical if available (like the tile does via api.getVarieties)
		const varieties = beanData.origins?.flatMap(o => o.variety_canonical || []) || [];
		const uniqueVarieties = [...new Set(varieties)];

		if (uniqueVarieties.length > 0) {
			drawTag(uniqueVarieties.join('/'), colors.tagVarietyBg, colors.tagVarietyText);
		} else if (firstOrigin?.variety) {
			// Fallback to raw variety string if no canonical ones found
			drawTag(firstOrigin.variety, colors.tagVarietyBg, colors.tagVarietyText);
		}

		currentY += imgSize + (beanPadding * 2) + 60 * scale;
	}

	// Separator
	tempCtx.strokeStyle = colors.separator;
	tempCtx.lineWidth = 2 * scale;
	tempCtx.beginPath();
	tempCtx.moveTo(padding, currentY);
	tempCtx.lineTo(width - padding, currentY);
	tempCtx.stroke();
	currentY += 80 * scale;

	// --- Flavours Section ---
	tempCtx.textAlign = 'left';
	tempCtx.font = `bold ${36 * scale}px ${fonts.heading}`;
	tempCtx.fillStyle = colors.title;
	tempCtx.fillText('Flavour Profile', padding, currentY);
	currentY += 60 * scale;

	// Render chips
	let cursorX = padding;
	const chipHeight = 56 * scale;
	const chipPaddingX = 24 * scale;
	const chipGap = 16 * scale;
	const lineGap = 40 * scale;

	tempCtx.font = `${28 * scale}px ${fonts.sans}`;

	for (const note of allSelectedNotesList) {
		const textWidth = tempCtx.measureText(note).width;
		const chipWidth = textWidth + chipPaddingX * 2;

		if (cursorX + chipWidth > width - padding) {
			cursorX = padding;
			currentY += chipHeight + lineGap;
		}

		// Resolve per-category chip colours using the same lookup as TastingSummaryCard
		const categoryName = findCategoryForNote(note);
		const chipColors = categoryName
			? getChipColors(categoryName, isDarkMode)
			: { bg: colors.chipBg, text: colors.chipText };

		// Draw chip background
		tempCtx.fillStyle = chipColors.bg;
		tempCtx.beginPath();
		tempCtx.roundRect(cursorX, currentY - (40 * scale), chipWidth, chipHeight, 28 * scale);
		tempCtx.fill();

		// Draw text
		tempCtx.fillStyle = chipColors.text;
		tempCtx.fillText(note, cursorX + chipPaddingX, currentY);

		cursorX += chipWidth + chipGap;
	}

	currentY += 120 * scale;

	// --- Basics & Mouthfeel ---
	const renderGridItems = (title: string, items: Record<string, string>, startY: number) => {
		tempCtx.textAlign = 'left';
		tempCtx.font = `bold ${36 * scale}px ${fonts.heading}`;
		tempCtx.fillStyle = colors.title;
		tempCtx.fillText(title, padding, startY);
		let y = startY + 60 * scale;

		tempCtx.font = `${28 * scale}px ${fonts.sans}`;
		const keys = Object.keys(items);
		for (let i = 0; i < keys.length; i++) {
			const key = keys[i];
			const val = items[key];

			// Label
			tempCtx.fillStyle = colors.muted;
			tempCtx.fillText(`${key}:`, padding, y);

			// Value
			tempCtx.fillStyle = colors.title;
			tempCtx.font = `bold ${28 * scale}px ${fonts.sans}`;
			tempCtx.fillText(val, padding + 220 * scale, y);
			tempCtx.font = `${28 * scale}px ${fonts.sans}`; // reset for next label

			y += 50 * scale;
		}
		return y;
	};

	let basicsY = renderGridItems('Basics', basics, currentY);
	renderGridItems('Body & Finish', mouthfeel, basicsY + (40 * scale));

	// Final Footer
	tempCtx.textAlign = 'center';
	tempCtx.font = `italic ${24 * scale}px ${fonts.sans}`;
	tempCtx.fillStyle = colors.footer;
	tempCtx.fillText('kissaten.app', width / 2, canvasHeight - padding);

	return new Promise((resolve) => {
		canvas.toBlob((blob) => {
			resolve(blob!);
		}, 'image/png');
	});
}

/**
 * Generate a consistent text summary for a tasting session.
 */
export function generateTastingText(options: TastingImageOptions): string {
	const { sessionName, dateOrNotes, allSelectedNotesList, beanData } = options;
	const title = sessionName || 'Coffee Tasting';
	const dateStr = dateOrNotes || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });

	let text = `☕ ${title}\n📅 ${dateStr}\n\n`;

	if (beanData) {
		text += `🟢 Bean: ${beanData.name}\n`;
		text += `🏭 Roaster: ${beanData.roaster}\n`;
		if (beanData.origins && beanData.origins.length > 0) {
			const first = beanData.origins[0];
			const details = [];
			if (first.country_full_name || first.country) details.push(`Origin: ${first.country_full_name || first.country}`);
			if (first.process) details.push(`Process: ${first.process}`);
			if (first.variety) details.push(`Variety: ${first.variety}`);
			if (details.length > 0) {
				text += `📍 ${details.join(' | ')}\n`;
			}
		}
		text += '\n';
	}

	if (allSelectedNotesList.length > 0) {
		text += `Flavour Profile: ${allSelectedNotesList.join(', ')}\n\n`;
	}

	const formatObject = (obj: Record<string, string>) =>
		Object.entries(obj)
			.map(([k, v]) => `${k.charAt(0).toUpperCase() + k.slice(1)}: ${v}`)
			.join('\n');

	if (Object.keys(options.basics).length > 0) {
		text += `Taste Foundation:\n${formatObject(options.basics)}\n\n`;
	}

	if (Object.keys(options.mouthfeel).length > 0) {
		text += `Mouthfeel:\n${formatObject(options.mouthfeel)}\n\n`;
	}

	text += 'Shared via Kissaten Coffee Tracker';

	return text;
}
