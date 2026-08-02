import type { CoffeeBean } from "$lib/api";
import type { FeedbackFieldOption } from "$lib/types/feedback";
import { formatPrice } from "$lib/utils";

const MAX_VALUE_LENGTH = 60;
const EMPTY = "—";

function truncate(value: string | null | undefined): string | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const trimmed = String(value).trim();
  if (!trimmed) return undefined;
  if (trimmed.length <= MAX_VALUE_LENGTH) return trimmed;
  return trimmed.slice(0, MAX_VALUE_LENGTH - 1) + "…";
}

function formatDateShort(dateStr: string | null | undefined): string | undefined {
  if (!dateStr) return undefined;
  try {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return undefined;
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
    });
  } catch {
    return undefined;
  }
}

function formatTastingNotes(
  notes: CoffeeBean["tasting_notes"] | undefined,
): string | undefined {
  if (!notes || notes.length === 0) return undefined;
  const first = notes.slice(0, 3).map((n) =>
    typeof n === "string" ? n : n.note,
  );
  return first.join(", ");
}

function formatElevation(
  origin: { elevation_min: number; elevation_max: number } | undefined,
): string | undefined {
  if (!origin) return undefined;
  if (!origin.elevation_min || origin.elevation_min <= 0) return undefined;
  if (origin.elevation_max && origin.elevation_max > origin.elevation_min) {
    return `${origin.elevation_min}-${origin.elevation_max}m`;
  }
  return `${origin.elevation_min}m`;
}

function formatCoordinates(
  origin: { latitude?: number | null; longitude?: number | null } | undefined,
): string | undefined {
  if (!origin?.latitude || !origin?.longitude) return undefined;
  return `${origin.latitude.toFixed(4)}, ${origin.longitude.toFixed(4)}`;
}

function formatVariety(
  canonical: string[] | null | undefined,
  fallback: string | null | undefined,
): string | undefined {
  if (canonical && canonical.length > 0) return canonical.join(", ");
  if (fallback) return fallback;
  return undefined;
}

const TOP_LEVEL_GROUPS: Array<{
  group: string;
  items: Array<{
    key: string;
    label: string;
    input: FeedbackFieldOption["input"];
    getValue: (bean: CoffeeBean) => string | undefined;
  }>;
}> = [
  {
    group: "Bean details",
    items: [
      {
        key: "description",
        label: "Description",
        input: { type: "textarea", rows: 5 },
        getValue: (b) => {
          const d = b.description?.trim();
          return d ? d : undefined;
        },
      },
    ],
  },
  {
    group: "Pricing & stock",
    items: [
      {
        key: "price",
        label: "Price",
        input: { type: "number", min: 0, step: 0.01 },
        getValue: (b) =>
          b.price != null ? formatPrice(b.price, b.currency) : undefined,
      },
      {
        key: "weight",
        label: "Weight (grams)",
        input: { type: "number", min: 0, step: 1 },
        getValue: (b) => (b.weight ? `${b.weight}g` : undefined),
      },
      {
        key: "in_stock",
        label: "In stock",
        input: { type: "select", options: ["In stock", "Out of stock"] },
        getValue: (b) =>
          b.in_stock === null ? undefined : b.in_stock ? "Yes" : "No",
      },
      {
        key: "cupping_score",
        label: "Cupping score",
        input: { type: "number", min: 0, max: 100, step: 0.5 },
        getValue: (b) =>
          b.cupping_score && b.cupping_score > 0
            ? `${b.cupping_score}/100`
            : undefined,
      },
    ],
  },
  {
    group: "Roast",
    items: [
      {
        key: "roast_level",
        label: "Roast level",
        input: {
          type: "select",
          options: [
            "Extra-Light",
            "Light",
            "Medium-Light",
            "Medium",
            "Medium-Dark",
            "Dark",
          ],
        },
        getValue: (b) => truncate(b.roast_level),
      },
      {
        key: "roast_profile",
        label: "Roast profile",
        input: {
          type: "select",
          options: ["Espresso", "Filter", "Omni", "Both"],
        },
        getValue: (b) => truncate(b.roast_profile),
      },
    ],
  },
  {
    group: "Tasting",
    items: [
      {
        key: "tasting_notes",
        label: "Tasting notes",
        input: { type: "tags" },
        getValue: (b) => formatTastingNotes(b.tasting_notes),
      },
    ],
  },
];

const PER_ORIGIN_FIELDS: Array<{
  key: string;
  label: string;
  input: FeedbackFieldOption["input"];
  getValue: (origin: CoffeeBean["origins"][number]) => string | undefined;
}> = [
  {
    key: "country",
    label: "Country",
    input: { type: "text" },
    getValue: (o) => truncate(o.country_full_name || o.country),
  },
  {
    key: "region",
    label: "Region",
    input: { type: "text" },
    getValue: (o) => truncate(o.region),
  },
  {
    key: "producer",
    label: "Producer",
    input: { type: "text" },
    getValue: (o) => truncate(o.producer),
  },
  {
    key: "farm",
    label: "Farm",
    input: { type: "text" },
    getValue: (o) => truncate(o.farm),
  },
  {
    key: "elevation",
    label: "Elevation (m)",
    input: { type: "text" },
    getValue: (o) => formatElevation(o),
  },
  {
    key: "coordinates",
    label: "Coordinates",
    input: { type: "text" },
    getValue: (o) => formatCoordinates(o),
  },
  {
    key: "process",
    label: "Process",
    input: { type: "text" },
    getValue: (o) => truncate(o.process),
  },
  {
    key: "variety",
    label: "Variety",
    input: { type: "text" },
    getValue: (o) => formatVariety(o.variety_canonical, o.variety),
  },
  {
    key: "harvest_date",
    label: "Harvest date",
    input: { type: "month" },
    getValue: (o) => formatDateShort(o.harvest_date),
  },
];

function originLabel(bean: CoffeeBean, index: number): string {
  const origin = bean.origins?.[index];
  const country = origin?.country_full_name || origin?.country;
  if (bean.origins.length > 1) {
    return `Origin ${index + 1}${country ? ` — ${country}` : ""}`;
  }
  return country ? `Origin — ${country}` : "Origin";
}

export function getBeanFeedbackFields(bean: CoffeeBean): FeedbackFieldOption[] {
  const result: FeedbackFieldOption[] = [];
  for (const g of TOP_LEVEL_GROUPS) {
    for (const item of g.items) {
      const value = item.getValue(bean);
      result.push({
        key: item.key,
        label: item.label,
        group: g.group,
        input: item.input,
        value: value ?? EMPTY,
      });
    }
  }

  const origins = bean.origins ?? [];
  for (let i = 0; i < origins.length; i++) {
    const group = originLabel(bean, i);
    for (const field of PER_ORIGIN_FIELDS) {
      const value = field.getValue(origins[i]);
      result.push({
        key: field.key,
        label: field.label,
        group,
        originIndex: i,
        input: field.input,
        value: value ?? EMPTY,
      });
    }
  }

  return result;
}
