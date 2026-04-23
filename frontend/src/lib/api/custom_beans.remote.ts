import { command, getRequestEvent, query } from '$app/server';
import { db } from '$lib/server/database';
import { customBeans } from '$lib/server/database/schema';
import { eq, desc, and } from 'drizzle-orm';
import { z } from 'zod';
import { nanoid } from 'nanoid';
import { beanFormSchema } from '$lib/schemas/beanFormSchema';
import type { CoffeeBean } from '$lib/api';

function requireAuth() {
	const { locals } = getRequestEvent();
	if (!locals.user) {
		throw new Error('Authentication required. Please sign in to continue.');
	}
	return locals.user;
}

export const extractBeanFromImage = command(z.string(), async (base64Image) => {
	requireAuth();

	// Extract content type and data
	const matches = base64Image.match(/^data:([A-Za-z-+/]+);base64,(.+)$/);
	if (!matches || matches.length !== 3) {
		throw new Error('Invalid image format');
	}

	const contentType = matches[1];
	const imageBuffer = Buffer.from(matches[2], 'base64');

	const formData = new FormData();
	const blob = new Blob([imageBuffer], { type: contentType });
	formData.append('file', blob, 'image.png');

	const response = await fetch('http://localhost:8000/v1/ai/extract', {
		method: 'POST',
		body: formData
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to extract bean data');
	}

	const result = await response.json();
	return result.data as CoffeeBean;
});

export const getCustomBeans = query(async () => {
	const { locals } = getRequestEvent();

	// If not authenticated, silently return empty array instead of 500 error
	if (!locals.user) {
		return [];
	}

	const currentUser = locals.user;

	const results = await db
		.select()
		.from(customBeans)
		.where(eq(customBeans.userId, currentUser.id))
		.orderBy(desc(customBeans.updatedAt));

	return results.map(row => {
		try {
			const data = JSON.parse(row.beanData) as CoffeeBean;

			// Migrating custom beans: ensure variety_canonical exists for UI consistency
			if (data.origins && data.origins.length > 0) {
				data.origins = data.origins.map(o => ({
					...o,
					variety_canonical: o.variety_canonical || (o.variety ? [o.variety] : [])
				}));
			}

			// Ensure it has its local ID for references
			return {
				...data,
				id: row.id,
				is_custom: true,
				bean_url_path: `/custom/${row.id}`
			};
		} catch (e) {
			console.error(`Failed to parse custom bean data for ${row.id}:`, e);
			return null;
		}
	}).filter(b => b !== null);
});

export const addCustomBean = command(beanFormSchema, async (data) => {
	const currentUser = requireAuth();

	const id = `custom_${nanoid()}`;

	// Prepare the CoffeeBean object for storage
	const coffeeBean: Partial<CoffeeBean> = {
		...data,
		id: id,
		url: data.url || `https://kissaten.app/custom/${id}`,
		bean_url_path: `/custom/${id}`,
		scraped_at: new Date().toISOString(),
		date_added: new Date().toISOString(),
		scraper_version: 'custom-user-submission',
		filename: `custom_${id}.json`,
		in_stock: true,
		score: 0,
		roaster_country_code: data.origins[0]?.country || 'XX',
		image_url: data.image_data || data.image_url,
		// Map origins for consistent display in the UI (global vs custom)
		origins: data.origins.map(o => ({
			...o,
			variety_canonical: o.variety ? [o.variety] : []
		}))
	};

	await db.insert(customBeans).values({
		id,
		userId: currentUser.id,
		beanData: JSON.stringify(coffeeBean),
	});

	return {
		id,
		bean_url_path: `/custom/${id}`,
		bean: { ...coffeeBean, id, is_custom: true } as CoffeeBean
	};
});

export const deleteCustomBean = command(z.string(), async (id) => {
	const currentUser = requireAuth();

	await db.delete(customBeans)
		.where(and(eq(customBeans.id, id), eq(customBeans.userId, currentUser.id)));

	return { success: true };
});
