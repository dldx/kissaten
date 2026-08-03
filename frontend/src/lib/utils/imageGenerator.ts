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

/** Splits text into lines that each fit within maxWidth, wrapping on spaces (falls back to char-splitting long words). */
function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
	const lines: string[] = [];
	const words = text.split(/\s+/);
	let currentLine = '';

	for (const word of words) {
		const testLine = currentLine ? `${currentLine} ${word}` : word;
		if (ctx.measureText(testLine).width <= maxWidth || !currentLine) {
			currentLine = testLine;
		} else {
			lines.push(currentLine);
			currentLine = word;
		}
	}
	if (currentLine) lines.push(currentLine);
	return lines;
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

	let currentY = padding + logoSize + 104 * scale;

	// Session Title
	tempCtx.textAlign = 'center';
	tempCtx.fillStyle = colors.title;
	tempCtx.font = `bold ${44 * scale}px ${fonts.heading}`;
	tempCtx.fillText(sessionName || 'Coffee Tasting', width / 2, currentY);
	currentY += 52 * scale;

	// Date/Notes
	tempCtx.font = `${26 * scale}px ${fonts.sans}`;
	tempCtx.fillStyle = colors.muted;
	const dateStr = dateOrNotes || new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
	const noteLines = wrapText(tempCtx, dateStr, width - (padding * 2));
	for (const line of noteLines) {
		tempCtx.fillText(line, width / 2, currentY);
		currentY += 36 * scale;
	}
	currentY += 36 * scale;

	// --- Coffee Bean Section ---
	if (beanData) {
		currentY += 12 * scale;
		const beanSectionX = padding;
		const beanSectionWidth = width - (padding * 2);
		const beanPadding = 24 * scale;
		const innerContentX = beanSectionX + beanPadding;
		const imgSize = 200 * scale;

		const contentStartY = currentY + beanPadding;
		const textTop = contentStartY + 24 * scale;
		const textRightLimit = width - padding;
		const textMaxWidth = textRightLimit - innerContentX;

		// 2. Bean Image (Left aligned like the tile)
		let imageOffset = 0;
		let beanImg: HTMLImageElement | null = null;
		if (beanData.image_url) {
			try {
				beanImg = new Image();
				beanImg.crossOrigin = 'anonymous';
				beanImg.src = beanData.image_url;
				await new Promise((resolve, reject) => {
					beanImg!.onload = resolve;
					beanImg!.onerror = reject;
				});
			} catch (e) {
				console.warn('Could not load bean image', e);
			}
		}
		imageOffset = imgSize + 28 * scale;

		// 3. Bean Content (Right of image)
		const textX = innerContentX + imageOffset;
		const beanTextMaxWidth = textRightLimit - textX;

		// ---- Derived bean data (mirrors CoffeeBeanTile) ----
		const firstOrigin = beanData.origins?.[0];

		// Origin display: country / region / farm (with blend fallback like the tile)
		const buildOriginLabel = (o?: typeof firstOrigin) =>
			[o?.country_full_name || o?.country, o?.region, o?.farm].filter(Boolean).join(', ');
		let originDisplay = '';
		if (beanData.origins && beanData.origins.length > 0) {
			if (beanData.is_single_origin) {
				originDisplay = buildOriginLabel(firstOrigin) || 'Unknown Origin';
			} else {
				const firstLabel = buildOriginLabel(firstOrigin);
				const allSame = beanData.origins.every((o) => buildOriginLabel(o) === firstLabel);
				originDisplay = allSame
					? firstLabel
					: beanData.origins.map((o) => buildOriginLabel(o)).filter(Boolean).join(' / ');
			}
		}

		// Elevation (own muted line, like the tile)
		let elevationStr = '';
		if (firstOrigin?.elevation_min && firstOrigin.elevation_min > 0) {
			elevationStr = firstOrigin.elevation_max && firstOrigin.elevation_max > firstOrigin.elevation_min
				? `${firstOrigin.elevation_min}-${firstOrigin.elevation_max}m`
				: `${firstOrigin.elevation_min}m`;
		}

		// Tag pills (mirror CoffeeBeanTile's flex-wrap badges)
		const pillColors = {
			red: { bg: isDarkMode ? 'rgba(127,29,29,0.45)' : '#fee2e2', fg: isDarkMode ? '#fecaca' : '#b91c1c' },
			green: { bg: isDarkMode ? 'rgba(6,95,70,0.45)' : '#dcfce7', fg: isDarkMode ? '#a7f3d0' : '#166534' },
			blue: { bg: isDarkMode ? 'rgba(8,145,178,0.45)' : '#dbeafe', fg: isDarkMode ? '#c4f1f9' : '#1e40af' },
			orange: { bg: isDarkMode ? 'rgba(124,45,18,0.45)' : '#ffedd5', fg: isDarkMode ? '#fdba74' : '#c2410c' },
			purple: { bg: isDarkMode ? 'rgba(76,29,149,0.45)' : '#f3e8ff', fg: isDarkMode ? '#c4b5fd' : '#7e22ce' },
			indigo: { bg: isDarkMode ? 'rgba(67,56,202,0.45)' : '#e0e7ff', fg: isDarkMode ? '#c7d2fe' : '#4338ca' },
		};
		const tagItems: { text: string; color: keyof typeof pillColors }[] = [];
		if (firstOrigin?.country || firstOrigin?.country_full_name) {
			tagItems.push({ text: firstOrigin.country_full_name || firstOrigin.country || '', color: 'red' });
		}
		const varieties = beanData.origins?.flatMap((o) => o.variety_canonical || []) || [];
		const uniqueVarieties = [...new Set(varieties)];
		if (uniqueVarieties.length > 0) {
			tagItems.push({ text: uniqueVarieties.join(' / '), color: 'green' });
		} else if (firstOrigin?.variety) {
			tagItems.push({ text: firstOrigin.variety, color: 'green' });
		}
		const processes = beanData.origins?.map((o) => o.process).filter(Boolean) as string[];
		if (processes.length > 0) {
			tagItems.push({ text: processes.join(' / '), color: 'blue' });
		}
		if (beanData.roast_level) {
			tagItems.push({ text: beanData.roast_level, color: 'orange' });
		}
		if (beanData.roast_profile) {
			const profileText = beanData.roast_profile === 'Both'
				? 'Filter & Espresso profile'
				: `${beanData.roast_profile} profile`;
			tagItems.push({ text: profileText, color: 'purple' });
		}
		if (beanData.is_decaf) {
			tagItems.push({ text: 'Decaf', color: 'red' });
		}
		if (!beanData.is_single_origin) {
			tagItems.push({ text: 'Blend', color: 'indigo' });
		}

		// ---- Measure the text block first so the card height adapts ----
		let layoutY = textTop;

		// Roaster (Emerald small caps) — single line
		tempCtx.font = `bold ${18 * scale}px ${fonts.sans}`;
		layoutY += 32 * scale;

		// Bean Name — wraps to multiple lines
		tempCtx.font = `bold ${38 * scale}px ${fonts.heading}`;
		let beanNameLines = wrapText(tempCtx, beanData.name, beanTextMaxWidth);
		if (beanNameLines.length === 0) beanNameLines = [''];
		layoutY += 44 * scale + (beanNameLines.length - 1) * 44 * scale;

		// Origin display — wraps
		let originLines: string[] = [];
		if (originDisplay) {
			tempCtx.font = `${22 * scale}px ${fonts.sans}`;
			originLines = wrapText(tempCtx, originDisplay, beanTextMaxWidth);
			layoutY += originLines.length * 38 * scale;
		}

		// Elevation — own line
		let elevationLines: string[] = [];
		if (elevationStr) {
			tempCtx.font = `${18 * scale}px ${fonts.sans}`;
			elevationLines = wrapText(tempCtx, elevationStr, beanTextMaxWidth);
			layoutY += elevationLines.length * 32 * scale;
		}

		// Tag pills — wrap
		const pillLayout: { text: string; x: number; width: number; baseline: number; bg: string; fg: string }[] = [];
		if (tagItems.length > 0) {
			const pillH = 34 * scale;
			const pillPadX = 14 * scale;
			const pillGap = 10 * scale;
			const pillLineGap = 8 * scale;
			tempCtx.font = `bold ${18 * scale}px ${fonts.sans}`;
			let px = textX;
			let rowBaseline = layoutY;
			for (const tag of tagItems) {
				const w = tempCtx.measureText(tag.text).width;
				const pillW = w + pillPadX * 2;
				if (px !== textX && px + pillW > textRightLimit) {
					px = textX;
					rowBaseline += pillH + pillLineGap;
				}
				pillLayout.push({
					text: tag.text,
					x: px,
					width: pillW,
					baseline: rowBaseline,
					bg: pillColors[tag.color].bg,
					fg: pillColors[tag.color].fg,
				});
				px += pillW + pillGap;
			}
			const lastRow = pillLayout[pillLayout.length - 1];
			layoutY = lastRow.baseline + 10 * scale;
		}

		// Bottom of text content
		const textBlockBottom = layoutY + 26 * scale;
		const cardContentHeight = Math.max(imgSize, textBlockBottom - contentStartY) + (beanPadding * 2);

		// 1. Draw Container Background (sized to content)
		tempCtx.fillStyle = colors.beanBg;
		tempCtx.strokeStyle = colors.beanBorder;
		tempCtx.lineWidth = 2 * scale;
		tempCtx.beginPath();
		tempCtx.roundRect(beanSectionX, currentY, beanSectionWidth, cardContentHeight, 16 * scale);
		tempCtx.fill();
		tempCtx.stroke();

		// Draw bean image / placeholder ON TOP of the container background
		if (beanImg) {
			tempCtx.save();
			tempCtx.beginPath();
			tempCtx.roundRect(innerContentX, contentStartY, imgSize, imgSize, 16 * scale);
			tempCtx.clip();
			tempCtx.drawImage(beanImg, innerContentX, contentStartY, imgSize, imgSize);
			tempCtx.restore();
		} else {
			// Placeholder like the tile
			tempCtx.fillStyle = isDarkMode ? 'rgba(8, 145, 178, 0.1)' : 'rgba(16, 185, 129, 0.05)';
			tempCtx.beginPath();
			tempCtx.roundRect(innerContentX, contentStartY, imgSize, imgSize, 16 * scale);
			tempCtx.fill();
		}

		const contentBottom = currentY + cardContentHeight;

		// ---- Draw the text ----
		let textY = textTop;

		// Roaster (Emerald small caps)
		tempCtx.textAlign = 'left';
		tempCtx.font = `bold ${18 * scale}px ${fonts.sans}`;
		tempCtx.fillStyle = isDarkMode ? '#67e8f9' : '#059669'; // cyan-300 or emerald-600
		tempCtx.fillText(beanData.roaster.toUpperCase(), textX, textY);
		textY += 32 * scale;

		// Bean Name (wrapped, left-aligned, no shrinking)
		tempCtx.font = `bold ${38 * scale}px ${fonts.heading}`;
		tempCtx.fillStyle = colors.title;
		for (const line of beanNameLines) {
			tempCtx.fillText(line, textX, textY);
			textY += 44 * scale;
		}

		// Origin display (wrapped)
		for (const line of originLines) {
			tempCtx.font = `${22 * scale}px ${fonts.sans}`;
			tempCtx.fillStyle = isDarkMode ? '#6ee7b7' : '#374151'; // emerald-300 or gray-700
			tempCtx.fillText(line, textX, textY);
			textY += 38 * scale;
		}

		// Elevation (wrapped, muted)
		for (const line of elevationLines) {
			tempCtx.font = `${18 * scale}px ${fonts.sans}`;
			tempCtx.fillStyle = isDarkMode ? '#9ca3af' : '#6b7280';
			tempCtx.fillText(line, textX, textY);
			textY += 32 * scale;
		}

		// Tag pills (drawn from precomputed wrap layout)
		tempCtx.font = `bold ${18 * scale}px ${fonts.sans}`;
		const pillH = 34 * scale;
		const pillPadX = 14 * scale;
		for (const pill of pillLayout) {
			tempCtx.fillStyle = pill.bg;
			tempCtx.beginPath();
			tempCtx.roundRect(pill.x, pill.baseline - 24 * scale, pill.width, pillH, 17 * scale);
			tempCtx.fill();

			tempCtx.fillStyle = pill.fg;
			tempCtx.fillText(pill.text, pill.x + pillPadX, pill.baseline);
		}

		currentY = contentBottom + 36 * scale;
	}

	// Separator
	tempCtx.strokeStyle = colors.separator;
	tempCtx.lineWidth = 2 * scale;
	tempCtx.beginPath();
	tempCtx.moveTo(padding, currentY);
	tempCtx.lineTo(width - padding, currentY);
	tempCtx.stroke();
	currentY += 32 * scale;

	// --- Flavours Section ---
	tempCtx.textAlign = 'left';
	tempCtx.font = `bold ${30 * scale}px ${fonts.heading}`;
	tempCtx.fillStyle = colors.title;
	tempCtx.fillText('Flavour Profile', padding, currentY);
	currentY += 44 * scale;

	// Render chips
	let cursorX = padding;
	const chipHeight = 44 * scale;
	const chipPaddingX = 20 * scale;
	const chipGap = 12 * scale;
	const lineGap = 28 * scale;

	tempCtx.font = `bold ${20 * scale}px ${fonts.sans}`;

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
		tempCtx.roundRect(cursorX, currentY - (32 * scale), chipWidth, chipHeight, 22 * scale);
		tempCtx.fill();

		// Draw text
		tempCtx.fillStyle = chipColors.text;
		tempCtx.fillText(note, cursorX + chipPaddingX, currentY);

		cursorX += chipWidth + chipGap;
	}

	currentY += 56 * scale;

	// --- Basics & Mouthfeel (two-column layout) ---
	const gridX = padding;
	const colGap = 60 * scale;
	const gridWidth = width - (padding * 2);
	const colWidth = (gridWidth - colGap) / 2;
	const labelWidth = 120 * scale;
	const valueX = (colX: number) => colX + labelWidth;

	const renderColumn = (title: string, items: Record<string, string>, colX: number) => {
		tempCtx.textAlign = 'left';
		tempCtx.font = `bold ${30 * scale}px ${fonts.heading}`;
		tempCtx.fillStyle = colors.title;
		tempCtx.fillText(title, colX, currentY);
		let y = currentY + 44 * scale;

		tempCtx.font = `${20 * scale}px ${fonts.sans}`;
		const keys = Object.keys(items);
		for (let i = 0; i < keys.length; i++) {
			const key = keys[i];
			const val = items[key];

			// Label
			tempCtx.fillStyle = colors.muted;
			tempCtx.fillText(`${key}:`, colX, y);

			// Value
			tempCtx.fillStyle = colors.title;
			tempCtx.font = `bold ${22 * scale}px ${fonts.sans}`;
			tempCtx.fillText(val, valueX(colX), y);
			tempCtx.font = `${20 * scale}px ${fonts.sans}`; // reset for next label

			y += 40 * scale;
		}
		return y;
	};

	let basicsEndY = renderColumn('Basics', basics, gridX);
	let mouthfeelEndY = renderColumn('Body & Finish', mouthfeel, gridX + colWidth + colGap);
	const contentBottom = Math.max(basicsEndY, mouthfeelEndY);

	// --- Dynamic height: crop the tall temp canvas to the actual content ---
	const footerSpace = 100 * scale;
	const finalHeight = contentBottom + footerSpace;
	const finalCanvas = document.createElement('canvas');
	finalCanvas.width = width;
	finalCanvas.height = finalHeight;
	const finalCtx = finalCanvas.getContext('2d')!;

	// Background & frame on the final canvas
	finalCtx.fillStyle = colors.bg;
	finalCtx.fillRect(0, 0, width, finalHeight);
	finalCtx.strokeStyle = colors.border;
	finalCtx.lineWidth = 20 * scale;
	finalCtx.strokeRect(0, 0, width, finalHeight);

	// Copy the rendered content (top region of temp canvas)
	finalCtx.drawImage(canvas, 0, 0, width, finalHeight, 0, 0, width, finalHeight);

	// Footer pinned to the actual bottom
	finalCtx.textAlign = 'center';
	finalCtx.font = `italic ${18 * scale}px ${fonts.sans}`;
	finalCtx.fillStyle = colors.footer;
	finalCtx.fillText('kissaten.app', width / 2, finalHeight - padding);

	return new Promise((resolve) => {
		finalCanvas.toBlob((blob) => {
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
