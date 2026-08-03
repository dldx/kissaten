<script lang="ts">
	import type { TastingSession } from "$lib/db/localdb";
	import { getHistoryUrl } from "$lib/utils/tasting_utils";
	import { formatShortDate } from "$lib/utils/history";
	import { getCategoryForNote } from "$lib/tasting/conversation";
	import { cn, getFlavourCategoryColors } from "$lib/utils";
	import { Badge } from "$lib/components/ui/badge";
	import { Button } from "$lib/components/ui/button";
	import { defaultWidths } from "$lib/utils/cfImage";
	import ResponsiveImage from "$lib/components/ResponsiveImage.svelte";
	import { ChevronRight, Coffee, Pencil, Trash2 } from "lucide-svelte";
	import { page } from "$app/state";

	interface Props {
		session: TastingSession;
		onDelete?: () => void;
	}

	const MAX_CHIPS = 5;

	let { session, onDelete }: Props = $props();

	const visibleNotes = $derived(session.selectedNotes.slice(0, MAX_CHIPS));
	const extraNoteCount = $derived(
		Math.max(0, session.selectedNotes.length - MAX_CHIPS),
	);

	const roaster = $derived(
		session.roasterName || session.beanData?.roaster || "",
	);

	const title = $derived(
		session.name || session.beanName || "Tasting Session",
	);

	const countryNameFromCode = (code: string) => {
		if (!code) return "";
		const options = page.data.originOptions || [];
		const country = options.find((o: any) => o.value === code.toUpperCase());
		return country ? country.text : code;
	};

	const originText = $derived.by(() => {
		const o = session.beanData?.origins?.[0];
		if (!o) return "";
		const countryName = o.country_full_name || (o.country ? countryNameFromCode(o.country) : "");
		return [
			countryName,
			o.region || "",
			o.farm || "",
		]
			.filter(Boolean)
			.join(", ");
	});

	const thumbImage = $derived((session.beanData as any)?.image_data || session.beanData?.image_url || "");
	const logoSrc = $derived(
		session.beanUrlPath
			? `/static/data/roasters/${session.beanUrlPath.split("/")[1]}/logo_sticker.png`
			: "",
	);

	let imageError = $state(false);
	let logoError = $state(false);

	const showThumb = $derived(thumbImage && !imageError);
	const showLogo = $derived(logoSrc && !logoError);
</script>

<div
	class="group relative flex items-center bg-emerald-50/20 hover:bg-emerald-50/30 p-3 border border-emerald-500/20 rounded-lg shadow-sm transition-all duration-200 dark:border-cyan-500/30 dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:hover:border-cyan-400/60 dark:hover:shadow-2xl dark:hover:shadow-cyan-500/20 cursor-pointer"
>
	<a
		href={getHistoryUrl(session)}
		class="absolute inset-0 z-0 rounded-lg"
		aria-label={session.name || session.beanName || "View tasting session"}
	></a>

	{#if showThumb}
		<div class="relative mr-3 shrink-0">
			<img
				src={thumbImage}
				alt={session.beanName || "Coffee bean"}
				onerror={() => { imageError = true; }}
				class="bg-muted dark:opacity-90 shadow-sm border border-emerald-500/10 dark:border-cyan-500/30 rounded-lg w-16 sm:w-20 h-16 sm:h-20 object-cover"
			/>
		</div>
	{:else}
		<div
			class="flex justify-center items-center bg-emerald-500/5 dark:bg-cyan-900/20 mr-3 border border-emerald-500/10 dark:border-cyan-500/30 rounded-lg w-16 sm:w-20 h-16 sm:h-20 shrink-0 placeholder-bg"
		>
			{#if showLogo}
				<ResponsiveImage
					src={logoSrc}
					alt="{session.roasterName ?? ''} logo"
					widths={defaultWidths.logo}
					sizes="80px"
					fit="contain"
					onerror={() => { logoError = true; }}
					class="drop-shadow-xs max-w-[70%] max-h-[70%] object-contain"
				/>
			{:else}
				<Coffee class="w-6 h-6 text-muted-foreground/40" />
			{/if}
		</div>
	{/if}

	<div class="pointer-events-none flex min-w-0 flex-1 flex-col justify-center pr-9 text-left">
		<div class="mb-0.5 flex items-center justify-between gap-2 min-w-0">
			<span
				class="font-bold text-[9px] text-emerald-600 sm:text-[10px] dark:text-cyan-300/80 truncate uppercase tracking-wider"
			>
				{roaster || "Roaster"}
			</span>
			<span
				class="shrink-0 text-muted-foreground/70 text-[9px] sm:text-[10px] truncate"
			>
				{formatShortDate(session.date)}
			</span>
		</div>
		<h3
			class="font-extrabold text-foreground dark:text-cyan-100 text-sm sm:text-base truncate leading-tight transition-colors"
		>
			{title}
		</h3>
		{#if originText}
			<p
				class="mt-0.5 font-medium text-[11px] text-gray-700 dark:text-emerald-300 sm:text-xs truncate"
			>
				{originText}
			</p>
		{/if}

		{#if session.brewingNotes}
			<div
				class="mt-1.5 flex items-start gap-1 text-muted-foreground/80 line-clamp-2 text-[11px] sm:text-xs leading-snug"
			>
				<Pencil class="mt-0.5 shrink-0 w-3 h-3" />
				<span>{session.brewingNotes}</span>
			</div>
		{/if}

		{#if session.selectedNotes.length > 0}
			<div class="mt-2 flex flex-wrap gap-1 items-center">
				{#each visibleNotes as note}
					{@const cat = getCategoryForNote(note)}
					{@const colors = getFlavourCategoryColors(
						cat?.isDefect ? "defects" : cat?.name || "Other",
					)}
					<span
						class={cn(
							"px-1.5 py-0.5 border rounded text-[10px] sm:text-xs font-medium whitespace-nowrap",
							cat?.isDefect
								? "border-destructive/30 bg-destructive/10 text-destructive"
								: cn(
										colors.bg,
										colors.text,
										colors.border,
										colors.darkBg,
										colors.darkText,
										colors.darkBorder,
									),
						)}
					>
						{note}
					</span>
				{/each}
				{#if extraNoteCount > 0}
					<Badge
						variant="outline"
						class="text-muted-foreground text-[10px] sm:text-xs"
					>
						+{extraNoteCount}
					</Badge>
				{/if}
			</div>
		{/if}
	</div>

	{#if onDelete}
		<Button
			variant="ghost"
			size="icon"
			class="absolute top-1.5 right-1.5 z-20 pointer-events-auto text-muted-foreground hover:text-destructive h-8 w-8"
			onclick={onDelete}
			aria-label="Delete session"
		>
			<Trash2 size={16} />
		</Button>
	{/if}

	<ChevronRight
		size={18}
		class="pointer-events-none absolute right-3 top-1/2 z-10 -translate-y-1/2 text-muted-foreground/50 group-hover:text-primary transition-transform group-hover:translate-x-0.5"
	/>
</div>
