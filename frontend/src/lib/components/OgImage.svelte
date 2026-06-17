<svelte:options css="injected" />

<script lang="ts">
	import type { CoffeeBean } from "$lib/api";
	import {
		Ban,
		Citrus,
		Coffee,
		Combine,
		Droplets,
		Flame,
		Leaf,
		MapPin,
		Sparkles,
		Warehouse,
	} from "lucide-svelte";

	type Variant = 'default' | 'bean' | 'roaster' | 'origin' | 'farm' | 'process' | 'varietal' | 'flavour';

	interface Props {
		variant?: Variant;
		title?: string;
		subtitle?: string;
		price?: string;
		tagline?: string;
		bean?: CoffeeBean | null;
		logoSvg?: string;
		beanImageData?: string | null;
	}

	let {
		variant = 'default',
		title = 'Kissaten',
		subtitle = '',
		price = '',
		tagline = 'Discover extraordinary coffee',
		bean = null,
		logoSvg = '',
		beanImageData = null
	}: Props = $props();

	const accent = $derived.by(() => {
		switch (variant) {
			case 'bean':
				return '#f59e0b';
			case 'roaster':
				return '#ef4444';
			case 'origin':
				return '#10b981';
			case 'farm':
				return '#059669';
			case 'process':
				return '#06b6d4';
			case 'varietal':
				return '#a855f7';
			case 'flavour':
				return '#ec4899';
			default:
				return '#10b981';
		}
	});

	const variantLabel = $derived.by(() => {
		switch (variant) {
			case 'roaster':
				return 'Coffee Roaster';
			case 'origin':
				return 'Coffee Origin';
			case 'farm':
				return 'Coffee Farm';
			case 'process':
				return 'Processing Method';
			case 'varietal':
				return 'Coffee Varietal';
			case 'flavour':
				return 'Tasting Note';
			case 'bean':
				return 'Coffee Bean';
			default:
				return '';
		}
	});

	const beanImage = $derived(beanImageData);

	const beanVarieties = $derived.by(() => {
		if (!bean?.origins) return [];
		return [
			...new Set(
				bean.origins
					.map((o) => o.variety_canonical)
					.filter((v): v is string[] => Array.isArray(v))
					.reduce((acc: string[], val: string[]) => acc.concat(val), [])
			)
		];
	});

	const beanProcesses = $derived(
		bean
			? [
					...new Set(
						bean.origins
							?.map((o) => o.process)
							.filter((p): p is string => !!p) ?? []
					)
				]
			: []
	);

	const beanOrigin = $derived(bean?.origins?.[0] ?? null);

	const beanOriginLabel = $derived.by(() => {
		if (!beanOrigin) return '';
		const parts: string[] = [];
		if (beanOrigin.country_full_name) parts.push(beanOrigin.country_full_name);
		if (beanOrigin.region) parts.push(beanOrigin.region);
		if (beanOrigin.farm) parts.push(beanOrigin.farm);
		return parts.join(', ');
	});

	const beanElevation = $derived.by(() => {
		const o = beanOrigin;
		if (!o?.elevation_min || o.elevation_min <= 0) return '';
		if (o.elevation_max && o.elevation_max > o.elevation_min) {
			return `${o.elevation_min}-${o.elevation_max}m elevation`;
		}
		return `${o.elevation_min}m elevation`;
	});

	const tastingNoteItems = $derived.by(() => {
		if (!bean?.tasting_notes) return [];
		return bean.tasting_notes
			.slice(0, 5)
			.map((n) => (typeof n === 'string' ? n : n.note))
			.filter(Boolean);
	});

	const isBeanVariant = $derived(variant === 'bean' && bean !== null);

	const titleFontSize = $derived.by(() => {
		if (!bean?.name) return '58px';
		const len = bean.name.length;
		if (len > 85) return '32px';
		if (len > 65) return '38px';
		if (len > 45) return '46px';
		if (len > 30) return '52px';
		return '58px';
	});

	const isBeanImage = $derived.by(() => {
		if (!bean) return false;
		const raw = (bean as any).image_data || bean.image_url || null;
		return !!raw;
	});
	const isLogoFallback = $derived.by(() => {
		if (!bean) return false;
		const raw = (bean as any).image_data || bean.image_url || null;
		return !raw && !!beanImageData;
	});
</script>

{#if isBeanVariant && bean}
	<div
		id="og-image"
		style:background="linear-gradient(135deg, {accent}22 0%, #0a0b1f 60%, #0a0b1f 100%)"
		style:width="1200px"
		style:height="630px"
		style:position="relative"
		style:overflow="hidden"
		style:display="flex"
		style:align-items="center"
		style:font-family="'Quicksand', sans-serif"
		style:color="white"
	>
		<div
			style:position="absolute"
			style:top="-150px"
			style:right="-100px"
			style:width="520px"
			style:height="520px"
			style:border-radius="50%"
			style:background="radial-gradient(circle, {accent}44 0%, transparent 70%)"
		></div>
		<div
			style:position="absolute"
			style:bottom="-180px"
			style:left="-180px"
			style:width="500px"
			style:height="500px"
			style:border-radius="50%"
			style:background="radial-gradient(circle, {accent}22 0%, transparent 70%)"
		></div>

		<div
			style:position="absolute"
			style:top="50px"
			style:left="60px"
			style:width="380px"
			style:height="70px"
			style:display="flex"
			style:align-items="center"
			style:z-index="3"
		>
			{#if logoSvg}
				<div style:width="380px" style:height="70px" style:display="flex" style:align-items="center" >
					{@html logoSvg}
				</div>
			{/if}
		</div>

		<div
			style:position="absolute"
				style:font-weight="700"
				style:color="#22d3ee"
				style:letter-spacing="0.02em"
				style:flex-shrink="0"
			style:bottom="36px"
			style:right="60px"
			style:font-size="40px"
			style:opacity="0.55"
			style:z-index="3"
		>
			kissaten.app
		</div>

		<div
			style:display="flex"
			style:align-items="center"
			style:gap="48px"
			style:padding="0 60px"
			style:width="100%"
			style:z-index="2"
		>
			<div
				style:position="relative"
				style:flex-shrink="0"
				style:width="380px"
				style:height="380px"
			>
				{#if beanImage}
					<img
						src={beanImage}
						alt={bean.name}
						style:width="380px"
						style:height="380px"
						style:object-fit={isBeanImage ? "cover" : "contain"}
						style:margin={isBeanImage ? "10px" : "0"}
						style:padding={isBeanImage ? "0" : "40px"}
					/>
				{:else}
					<div
						style:width="380px"
						style:height="380px"
						style:display="flex"
						style:align-items="center"
						style:justify-content="center"
						style:background="rgba(245,158,11,0.08)"
						style:border-radius="24px"
						style:border="2px dashed {accent}55"
					>
						<Sparkles size={72} color={accent} />
					</div>
				{/if}
				{#if bean.cupping_score}
					<div
						style:position="absolute"
						style:top="-14px"
						style:right="-14px"
						style:background="#facc15"
						style:color="#713f12"
						style:font-weight="800"
						style:font-size="24px"
						style:padding="10px 16px"
						style:border-radius="999px"
						style:box-shadow="0 6px 16px rgba(0,0,0,0.4)"
						style:border="3px solid #0a0b1f"
					>
						{bean.cupping_score}
					</div>
				{/if}
			</div>

			<div
				style:flex="1"
				style:display="flex"
				style:flex-direction="column"
				style:gap="12px"
				style:min-width="0"
			>
				<div
					style:font-size="18px"
					style:font-weight="700"
					style:color={accent}
					style:letter-spacing="0.12em"
				>
					{(bean.roaster || 'Unknown Roaster').toUpperCase().replace("&", "+")}
				</div>

				<div
					style:font-size={titleFontSize}
					style:font-weight="800"
					style:line-height="1.05"
					style:letter-spacing="-0.03em"
					style:word-wrap="break-word"
				>
					{bean.name.replace("&", "+")}
				</div>

				{#if beanOriginLabel}
					<div
						style:font-size="22px"
						style:opacity="0.88"
						style:display="flex"
						style:align-items="center"
						style:gap="8px"
						style:margin-top="4px"
					>
						<MapPin size={20} />
						<span>{beanOriginLabel}</span>
					</div>
				{/if}
				{#if beanElevation}
					<div style:font-size="18px" style:opacity="0.65">{beanElevation}</div>
				{/if}

				<div
					style:display="flex"
					style:flex-wrap="wrap"
					style:gap="8px"
					style:margin-top="10px"
				>
					{#if beanOrigin?.country}
						<div
							style:display="inline-flex"
							style:align-items="center"
							style:gap="6px"
							style:background="rgba(239,68,68,0.18)"
							style:border="1px solid rgba(239,68,68,0.45)"
							style:padding="6px 12px"
							style:border-radius="999px"
							style:font-size="14px"
							style:font-weight="500"
						>
						<MapPin size={13} />
							<span style:opacity="0.9"
								>{beanOrigin.country_full_name || beanOrigin.country}</span
							>
						</div>
					{/if}
					{#each beanVarieties.slice(0, 2) as variety (variety)}
						<div
							style:display="inline-flex"
							style:align-items="center"
							style:gap="5px"
							style:background="rgba(16,185,129,0.18)"
							style:border="1px solid rgba(16,185,129,0.45)"
							style:padding="6px 12px"
							style:border-radius="999px"
							style:font-size="14px"
							style:font-weight="500"
						>
							<Leaf size={13} />
							<span>{variety}</span>
						</div>
					{/each}
					{#each beanProcesses.slice(0, 2) as process (process)}
						<div
							style:display="inline-flex"
							style:align-items="center"
							style:gap="5px"
							style:background="rgba(34,211,238,0.18)"
							style:border="1px solid rgba(34,211,238,0.45)"
							style:padding="6px 12px"
							style:border-radius="999px"
							style:font-size="14px"
							style:font-weight="500"
						>
							<Droplets size={13} />
							<span>{process}</span>
						</div>
					{/each}
					{#if bean.roast_level}
						<div
							style:display="inline-flex"
							style:align-items="center"
							style:gap="5px"
							style:background="rgba(251,146,60,0.18)"
							style:border="1px solid rgba(251,146,60,0.45)"
							style:padding="6px 12px"
							style:border-radius="999px"
							style:font-size="14px"
							style:font-weight="500"
						>
							<Flame size={13} />
							<span>{bean.roast_level}</span>
						</div>
					{/if}
					{#if bean.roast_profile}
						<div
							style:display="inline-flex"
							style:align-items="center"
							style:gap="5px"
							style:background="rgba(168,85,247,0.18)"
							style:border="1px solid rgba(168,85,247,0.45)"
							style:padding="6px 12px"
							style:border-radius="999px"
							style:font-size="14px"
							style:font-weight="500"
						>
							<Coffee size={13} />
							<span
								>{bean.roast_profile == 'Both'
									? 'Filter + Espresso'
									: bean.roast_profile}</span
							>
						</div>
					{/if}
					{#if bean.is_decaf}
						<div
							style:display="inline-flex"
							style:align-items="center"
							style:gap="5px"
							style:background="rgba(239,68,68,0.18)"
							style:border="1px solid rgba(239,68,68,0.45)"
							style:padding="6px 12px"
							style:border-radius="999px"
							style:font-size="14px"
							style:font-weight="500"
						>
							<Ban size={13} />
							<span>Decaf</span>
						</div>
					{/if}
					{#if !bean.is_single_origin}
						<div
							style:display="inline-flex"
							style:align-items="center"
							style:gap="5px"
							style:background="rgba(236,72,153,0.18)"
							style:border="1px solid rgba(236,72,153,0.45)"
							style:padding="6px 12px"
							style:border-radius="999px"
							style:font-size="14px"
							style:font-weight="500"
						>
							<Combine size={13} />
							<span>Blend</span>
						</div>
					{/if}
				</div>

				{#if tastingNoteItems.length > 0}
					<div
						style:display="flex"
						style:flex-wrap="wrap"
						style:gap="6px"
						style:margin-top="10px"
					>
						{#each tastingNoteItems as note (note)}
							<div
								style:background="rgba(255,255,255,0.08)"
								style:border="1px solid rgba(255,255,255,0.18)"
								style:padding="5px 12px"
								style:border-radius="999px"
								style:font-size="14px"
								style:font-weight="500"
							>
								{note}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
{:else}
	<div
		id="og-image"
		style:background="#0a0b1f"
		style:width="1200px"
		style:height="630px"
		style:position="relative"
		style:overflow="hidden"
		style:display="flex"
		style:flex-direction="column"
		style:justify-content="space-between"
		style:padding="72px"
		style:font-family="'Quicksand', sans-serif"
		style:color="#e0f7fa"
	>
		<div
			style:position="absolute"
			style:top="0"
			style:left="0"
			style:right="0"
			style:height="3px"
			style:background={accent}
		></div>

		<div
			style:position="relative"
			style:z-index="2"
			style:display="flex"
			style:align-items="center"
		>
			{#if logoSvg}
				<div
					style:height="72px"
					style:width="390px"
					style:display="flex"
					style:align-items="center"
				>
					{@html logoSvg}
				</div>
			{:else}
				<div style:font-size="48px" style:font-weight="800" style:letter-spacing="-0.03em">Kissaten</div>
			{/if}
		</div>

		<div style:position="relative" style:z-index="2" style:max-width="1000px">
			{#if variantLabel}
				<div
					style:display="inline-flex"
					style:align-items="center"
					style:gap="10px"
					style:padding="10px 18px"
					style:margin-bottom="12px"
					style:margin-top="12px"
					style:border="1.5px solid {accent}"
					style:border-radius="999px"
					style:font-size="18px"
					style:font-weight="600"
					style:color={accent}
					style:letter-spacing="0.1em"
				>
					{#if variant === 'roaster'}
						<Flame size={18} color={accent} />
					{:else if variant === 'origin'}
						<MapPin size={18} color={accent} />
					{:else if variant === 'farm'}
						<Warehouse size={18} color={accent} />
					{:else if variant === 'process'}
						<Droplets size={18} color={accent} />
					{:else if variant === 'varietal'}
						<Leaf size={18} color={accent} />
					{:else if variant === 'flavour'}
						<Citrus size={18} color={accent} />
					{/if}
					<span>{variantLabel.toUpperCase()}</span>
				</div>
			{/if}

			{#if title}
				<div
					style:font-size="84px"
					style:font-weight="800"
					style:line-height="1.05"
					style:letter-spacing="-0.035em"
					style:word-wrap="break-word"
				>{title}</div>
			{/if}

			{#if subtitle}
				<div
					style:font-size="38px"
					style:font-weight="500"
					style:margin-top="20px"
					style:color="rgba(224, 247, 250, 0.75)"
					style:line-height="1.25"
				>{subtitle}</div>
			{/if}

			{#if price}
				<div
					style:font-size="40px"
					style:font-weight="700"
					style:margin-top="28px"
					style:display="inline-block"
					style:padding="10px 22px"
					style:border="1.5px solid {accent}"
					style:border-radius="14px"
					style:color={accent}
				>{price}</div>
			{/if}
		</div>

		<div
			style:position="relative"
			style:z-index="2"
			style:display="flex"
			style:justify-content="space-between"
			style:align-items="flex-end"
			style:gap="32px"
		>
			<div
				style:font-size="26px"
				style:font-weight="700"
				style:color="rgba(224, 247, 250, 0.7)"
				style:max-width="780px"
				style:line-height="1.3"
			>{tagline}</div>
			<div
				style:font-size="40px"
				style:font-weight="700"
				style:color="#22d3ee"
				style:letter-spacing="0.02em"
				style:flex-shrink="0"
			>kissaten.app</div>
		</div>
	</div>
{/if}
