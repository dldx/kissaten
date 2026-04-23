import { z } from "zod";

export const beanOriginSchema = z.object({
	country: z.string().min(1, "Country is required").max(100),
	region: z.string().max(100).optional().nullable(),
	producer: z.string().max(100).optional().nullable(),
	farm: z.string().max(100).optional().nullable(),
	elevation_min: z.number().int().min(0).max(3000).default(0),
	elevation_max: z.number().int().min(0).max(3000).default(0),
	latitude: z.number().min(-90).max(90).optional().nullable(),
	longitude: z.number().min(-180).max(180).optional().nullable(),
	process: z.string().max(100).optional().nullable(),
	variety: z.string().max(100).optional().nullable(),
	harvest_date: z.string().optional().nullable(),
	fob_price: z.number().gt(0).optional().nullable(),
	farm_gate_price: z.number().gt(0).optional().nullable(),
	price_paid_to_producer: z.number().gt(0).optional().nullable(),
	importer_name: z.string().max(200).optional().nullable(),
});

export const beanFormSchema = z.object({
	name: z.string().min(1, "Name is required").max(200),
	roaster: z.string().min(1, "Roaster is required").max(100),
	roaster_location: z.string().max(2).optional().nullable().describe("ISO country code"),
	url: z.string().url("Must be a valid URL").optional().or(z.literal("")),
	image_url: z.string().url().optional().nullable(),
	description: z.string().max(8000).optional().nullable(),
	origins: z.array(beanOriginSchema).min(1, "At least one origin is required"),
	is_single_origin: z.boolean().default(true),
	roast_level: z.enum(["Extra-Light", "Light", "Medium-Light", "Medium", "Medium-Dark", "Dark"]).optional().nullable(),
	roast_profile: z.enum(["Espresso", "Filter", "Omni", "Both"]).optional().nullable(),
	price: z.number().gt(0, "Price must be positive").optional().nullable(),
	weight: z.number().int().gt(0, "Weight must be positive").optional().nullable(),
	currency: z.string().length(3).default("GBP"),
	is_decaf: z.boolean().default(false),
	cupping_score: z.number().min(70).max(100).optional().nullable(),
	tasting_notes: z.array(z.string()).default([]),
	image_data: z.string().optional().nullable(),
	price_paid_for_green_coffee: z.number().gt(0).optional().nullable(),
	currency_of_price_paid_for_green_coffee: z.string().length(3).optional().nullable(),
});

export type BeanFormSchema = z.infer<typeof beanFormSchema>;
export type BeanOriginSchema = z.infer<typeof beanOriginSchema>;
