<script lang="ts">
	import * as d3 from "d3";
	import { onMount } from "svelte";
	import type { CoffeeBean, FarmSummary, RegionSummary } from "$lib/api";
	import { normalizeRegionName, normalizeFarmName } from "$lib/utils";

	interface Props {
		beans?: CoffeeBean[];
		farms?: FarmSummary[];
		regions?: RegionSummary[];
		className?: string;
		farmElevationMin?: number | null;
		farmElevationMax?: number | null;
		countryCode?: string;
		regionSlug?: string;
	}

	let { beans = [], farms = [], regions = [], className = "", farmElevationMin, farmElevationMax, countryCode, regionSlug }: Props = $props();

	let svgElement: SVGSVGElement;
	let containerEl: HTMLDivElement;
	let tooltipEl: HTMLDivElement;
	let width = $state(500);
	let height = $state(300);

// Extract elevation data from either beans, farms, or regions
	interface ElevationPoint {
		name: string;
		roaster: string;
		elevation: number;
		url?: string;
	}

	const elevationPoints = $derived.by(() => {
		const results: ElevationPoint[] = [];

		// If regions are provided, use their actual median elevation
		if (regions && regions.length > 0) {
			for (const region of regions) {
				// Only include regions that have elevation data
				if (region.median_elevation && region.median_elevation > 0) {
					const regionSlugForUrl = normalizeRegionName(region.region_name);
					const regionUrl = countryCode
						? `/origins/${countryCode.toLowerCase()}/${regionSlugForUrl}`
						: undefined;

					results.push({
						name: region.region_name,
						roaster: `${region.farm_count} farms`,
						elevation: region.median_elevation,
						url: regionUrl,
					});
				}
			}
			return results;
		}

		// If farms are provided, use farm data
		if (farms && farms.length > 0) {
			for (const farm of farms) {
				if (farm.avg_elevation && farm.avg_elevation > 0) {
					const farmSlug = normalizeFarmName(farm.farm_name);
					const farmUrl = countryCode && regionSlug
						? `/origins/${countryCode.toLowerCase()}/${regionSlug}/${farmSlug}`
						: undefined;

					results.push({
						name: farm.farm_name,
						roaster: farm.producer_name || 'Producer',
						elevation: farm.avg_elevation,
						url: farmUrl,
					});
				}
			}
			return results;
		}

		// Otherwise, use beans data
		const farmFallback =
			farmElevationMin && farmElevationMin > 0 && farmElevationMax && farmElevationMax > 0
				? (farmElevationMin + farmElevationMax) / 2
				: (farmElevationMin && farmElevationMin > 0)
					? farmElevationMin
					: (farmElevationMax && farmElevationMax > 0)
						? farmElevationMax
						: null;

		for (const bean of beans) {
			let addedForBean = false;
			for (const origin of bean.origins) {
				const elev =
					origin.elevation_min > 0
						? origin.elevation_max > 0
							? (origin.elevation_min + origin.elevation_max) / 2
							: origin.elevation_min
						: origin.elevation_max > 0
							? origin.elevation_max
							: 0;
				if (elev > 0) {
					results.push({
						name: bean.name,
						roaster: bean.roaster,
						elevation: elev,
						url: bean.bean_url_path
							? "/roasters" + bean.bean_url_path
							: undefined,
					});
					addedForBean = true;
				}
			}
			// If no per-origin elevation, fall back to farm-level elevation
			if (!addedForBean && farmFallback) {
				results.push({
					name: bean.name,
					roaster: bean.roaster,
					elevation: farmFallback,
					url: bean.bean_url_path
						? "/roasters" + bean.bean_url_path
						: undefined,
				});
			}
		}
		return results;
	});

	// Determine if we're showing farms/regions (use warehouse icon) or beans (use plant icon)
	const showingFarmsOrRegions = $derived((regions && regions.length > 0) || (farms && farms.length > 0));

	// Mountain shape: a main peak and a smaller side peak for character
	// Given a normalised x in [0,1], returns normalised y in [0,1]
	function mountainCurve(t: number): number {
		const mainPeak = 0.45;
		const mainHeight = 1.0;
		const mainWidth = 0.35;

		const sidePeak = 0.72;
		const sideHeight = 0.45;
		const sideWidth = 0.32;

		const mainSlope = Math.max(0, mainHeight - Math.abs(t - mainPeak) / mainWidth);
		const sideSlope = Math.max(0, sideHeight - Math.abs(t - sidePeak) / sideWidth);

		return Math.max(mainSlope, sideSlope);
	}

	// Given a normalised elevation [0,1], find the x values on the mountain surface
	// Returns [xLeft, xRight] — the two points on the silhouette at that height
	function mountainXAtHeight(
		normElev: number,
		peakX: number,
	): [number, number] {
		// We use the main peak for the bean placement logic
		const mainWidth = 0.35;
		const offset = (1 - normElev) * mainWidth;
		return [peakX - offset, peakX + offset];
	}

	function drawChart() {
		if (!svgElement || elevationPoints.length === 0) return;

		const svg = d3.select(svgElement);
		svg.selectAll("*").remove();

		const margin = { top: 26, right: 4, bottom: 14, left: 10 };
		const w = width - margin.left - margin.right;
		const h = height - margin.top - margin.bottom;

		const g = svg
			.append("g")
			.attr("transform", `translate(${margin.left},${margin.top})`);

		// Fixed elevation range: 0 to 3000m
		const baseElev = 0;
		const elevMax = 3000;

		// Y scale: elevation → pixel
		const yScale = d3
			.scaleLinear()
			.domain([baseElev, elevMax])
			.range([h, 0]);

		// Mountain parameters (in normalised 0-1 space, mapped to pixel x)
		const peakNorm = 0.45;

		// Generate mountain path points
		const mountainPoints: [number, number][] = [];
		const steps = 100;
		for (let i = 0; i <= steps; i++) {
			const t = i / steps;
			const normY = mountainCurve(t);
			const pixelX = t * w;
			// Map normalised Y to elevation space
			const elev = baseElev + normY * (elevMax - baseElev);
			const pixelY = yScale(elev);
			mountainPoints.push([pixelX, pixelY]);
		}

		// Defs for gradients and filters
		const defs = svg.append("defs");

		// Drop shadow for plant icons
		const dropShadow = defs.append("filter")
			.attr("id", "plant-shadow")
			.attr("x", "-50%")
			.attr("y", "-50%")
			.attr("width", "200%")
			.attr("height", "200%");
		dropShadow.append("feGaussianBlur")
			.attr("in", "SourceAlpha")
			.attr("stdDeviation", 1.5);
		dropShadow.append("feOffset")
			.attr("dx", 0)
			.attr("dy", 1)
			.attr("result", "offsetblur");
		dropShadow.append("feComponentTransfer")
			.append("feFuncA")
			.attr("type", "linear")
			.attr("slope", 0.3);
		const feMerge = dropShadow.append("feMerge");
		feMerge.append("feMergeNode");
		feMerge.append("feMergeNode").attr("in", "SourceGraphic");


		// Draw mountain silhouette
		const mountainArea = d3
			.area<[number, number]>()
			.x((d) => d[0])
			.y0(h)
			.y1((d) => d[1])
			.curve(d3.curveBasis);

		g.append("path")
			.datum(mountainPoints)
			.attr("d", mountainArea)
			.attr("fill", "#86efac")
			.attr("stroke", "none")
			.attr("opacity", 0.9);

		// Compute tick values: use farm-level min/max elevations (matching the badge display), plus 0 and 3000m endpoints
		const dataMin = d3.min(elevationPoints, (d) => d.elevation) || 0;
		const dataMax = d3.max(elevationPoints, (d) => d.elevation) || 3000;
		const farmMin = farmElevationMin !== null && farmElevationMin !== undefined ? farmElevationMin : dataMin;
		const farmMax = farmElevationMax !== null && farmElevationMax !== undefined ? farmElevationMax : dataMax;

		// Always show 0, 3000, and the actual data range min/max
		const tickValues = [0, dataMin, dataMax, 3000].filter((v, i, arr) => arr.indexOf(v) === i).sort((a, b) => a - b);

		// Y axis — rendered at right edge with labels inside the chart
		const yAxis = d3
			.axisLeft(yScale)
			.tickValues(tickValues)
			.tickSize(0)
			.tickFormat((d) => `${d}m`);
		const yAxisGroup = g
			.append("g")
			.call(yAxis)
			.attr("transform", `translate(${w}, 0)`)
			.attr("class", "y-axis");
		yAxisGroup.select(".domain").attr("stroke", "#94a3b8").attr("opacity", 0);
		yAxisGroup
			.selectAll(".tick line")
			.remove();
		yAxisGroup
			.selectAll(".tick text")
			.attr("fill", "#475569")
			.attr("font-size", "10px")
			.attr("font-weight", "600")
			.attr("text-anchor", "end")
			.attr("dx", "-6");

		// Dashed lines from right mountain surface to axis label
		// Stop ~44px before the right edge so lines don't overlap the text labels.
		const labelGap = 44;
		for (const tick of tickValues) {
			if (tick === 0 || tick === elevMax) continue;
			const normElev = (tick - baseElev) / (elevMax - baseElev);
			const [, xRight] = mountainXAtHeight(normElev, peakNorm);
			const surfaceX = Math.min(xRight * w, w - labelGap - 2);
			const lineY = yScale(tick);
			g.append("line")
				.attr("x1", surfaceX)
				.attr("y1", lineY)
				.attr("x2", w - labelGap)
				.attr("y2", lineY)
				.attr("stroke", "#94a3b8")
				.attr("stroke-width", 1)
				.attr("stroke-dasharray", "4,3")
				.attr("opacity", 0.6);
		}

		// Plant color palette — greens and browns. Keep the colours relatively similar in luminance
		const colorPalette = ["#4d7c0f", "#6b8e23", "#556b2f", "#8b4513", "#a0522d", "#228b22", "#2e8b57"];
		const rng = d3.randomLcg(42);

		// Place tree emojis — start at the mountain centre at each elevation
		const dotRadius = 10; // collision radius for the emoji

		const beanDotData = elevationPoints.map((b) => {
			const normElev = (b.elevation - baseElev) / (elevMax - baseElev);
			const [xLeft, xRight] = mountainXAtHeight(normElev, peakNorm);
			const centerX = ((xLeft + xRight) / 2) * w;
			const targetY = yScale(b.elevation);
			const color = colorPalette[Math.floor(rng() * colorPalette.length)];
			return { ...b, x: centerX, y: targetY, vx: 0, vy: 0, targetY, color };
		});

		// forceCollide separates overlapping plants horizontally.
		// fixY gently restores each node toward its target elevation each tick.
		// d3 custom forces must be callable functions (called as force(alpha) each tick).
		const fixYForce = () => {
			for (const d of beanDotData as any[]) {
				d.vy += (d.targetY - d.y) * 0.3;
			}
		};

		// Draw tree emojis immediately at starting positions
		const dotGroup = g.append("g").attr("class", "bean-dots");

		// Start as tiny icons, grow into plants once simulation settles
		const treeNodes = dotGroup
			.selectAll("g.bean-tree")
			.data(beanDotData)
			.join("g")
			.attr("class", "bean-tree")
			.attr("transform", (d: any) => `translate(${d.x},${d.targetY}) scale(0.15)`)
			.attr("cursor", "pointer")
			.attr("filter", "url(#plant-shadow)")
			.each(function(d: any) {
				const g = d3.select(this);
				// Use warehouse icon for farms/regions, plant icon for beans
				if (showingFarmsOrRegions) {
					// Warehouse icon
					g.html(`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 640 512"><rect x="0" y="0" width="640" height="512" fill="transparent" pointer-events="all"/><path fill="${d.color}" d="M504 352H136.4c-4.4 0-8 3.6-8 8l-.1 48c0 4.4 3.6 8 8 8H504c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8m0 96H136.1c-4.4 0-8 3.6-8 8l-.1 48c0 4.4 3.6 8 8 8h368c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8m0-192H136.6c-4.4 0-8 3.6-8 8l-.1 48c0 4.4 3.6 8 8 8H504c4.4 0 8-3.6 8-8v-48c0-4.4-3.6-8-8-8m106.5-139L338.4 3.7a48.15 48.15 0 0 0-36.9 0L29.5 117C11.7 124.5 0 141.9 0 161.3V504c0 4.4 3.6 8 8 8h80c4.4 0 8-3.6 8-8V256c0-17.6 14.6-32 32.6-32h382.8c18 0 32.6 14.4 32.6 32v248c0 4.4 3.6 8 8 8h80c4.4 0 8-3.6 8-8V161.3c0-19.4-11.7-36.8-29.5-44.3"/></svg>`);
				} else {
					// Plant icon
					g.html(`<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 256 256"><rect x="0" y="0" width="256" height="256" fill="transparent" pointer-events="all"/><path stroke="white" fill="${d.color}" d="M205.41 159.07a60.9 60.9 0 0 1-31.83 8.86a71.7 71.7 0 0 1-27.36-5.66A55.55 55.55 0 0 0 136 194.51V224a8 8 0 0 1-8.53 8a8.18 8.18 0 0 1-7.47-8.25v-12.44l-38.62-38.62A52.5 52.5 0 0 1 63.44 176a45.8 45.8 0 0 1-23.92-6.67C17.73 156.09 6 125.62 8.27 87.79a8 8 0 0 1 7.52-7.52c37.83-2.23 68.3 9.46 81.5 31.25a46 46 0 0 1 6.45 28.48a4 4 0 0 1-6.89 2.43l-19.2-20.1a8 8 0 0 0-11.31 11.31l53.88 55.25c.06-.78.13-1.56.21-2.33a68.56 68.56 0 0 1 18.64-39.46l50.59-53.46a8 8 0 0 0-11.31-11.32l-49 51.82a4 4 0 0 1-6.78-1.74c-4.74-17.48-2.65-34.88 6.4-49.82c17.86-29.48 59.42-45.26 111.18-42.22a8 8 0 0 1 7.52 7.52c3 51.77-12.78 93.33-42.26 111.19"/></svg>`);
				}
			});

		// Run simulation live — dots visibly jostle into position, then grow into trees
		const sim = d3.forceSimulation(beanDotData as any)
			.force("collide", d3.forceCollide(dotRadius + 2).strength(1).iterations(3))
			.force("fixY", fixYForce as any)
			.alphaDecay(0.15)
			.velocityDecay(0.6)
			.on("tick", () => {
				treeNodes.each(function(d: any) {
					const normElev = (d.elevation - baseElev) / (elevMax - baseElev);
					const [xLeft, xRight] = mountainXAtHeight(normElev, peakNorm);
					const minX = xLeft * w + dotRadius;
					const maxX = xRight * w - dotRadius;
					const clampedX = Math.max(minX, Math.min(maxX, d.x));
					d3.select(this)
						.attr("transform", `translate(${clampedX - 12},${d.targetY - 12}) scale(0.15)`);
				});
			})
			.on("end", () => {
				treeNodes.each(function(d: any) {
					const normElev = (d.elevation - baseElev) / (elevMax - baseElev);
					const [xLeft, xRight] = mountainXAtHeight(normElev, peakNorm);
					const minX = xLeft * w + dotRadius;
					const maxX = xRight * w - dotRadius;
					const clampedX = Math.max(minX, Math.min(maxX, d.x));
					d3.select(this)
						.transition()
						.duration(500)
						.delay((_d, i) => i * 40)
						.ease(d3.easeBounceOut)
						.attr("transform", `translate(${clampedX - 12},${d.targetY - 12}) scale(0.7)`);
				});
			});

		// Tooltip interactions
		const tooltipDiv = d3.select(tooltipEl);

		dotGroup
			.selectAll("g.bean-tree")
			.on("mouseenter", function (_event, d: any) {
				const normElev = (d.elevation - baseElev) / (elevMax - baseElev);
				const [xLeft, xRight] = mountainXAtHeight(normElev, peakNorm);
				const minX = xLeft * w + dotRadius;
				const maxX = xRight * w - dotRadius;
				const clampedX = Math.max(minX, Math.min(maxX, d.x));
				d3.select(this)
					.transition()
					.duration(200)
					.attr("transform", `translate(${clampedX - 15},${d.targetY - 15}) scale(0.9)`);

				tooltipDiv
					.style("opacity", "1")
					.style("pointer-events", "auto")
					.html(
						`<div class="font-semibold text-sm">${d.name}</div>
						 <div class="text-gray-500 text-xs">${d.roaster}</div>
						 <div class="flex items-center gap-1 mt-1 font-medium text-orange-700 dark:text-amber-300 text-xs"><svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="16 12 12 8 8 12"/><line x1="12" y1="16" x2="12" y2="8"/></svg> ${Math.round(d.elevation)}m</div>`,
					);
			})
			.on("mousemove", function (event) {
				const [mx, my] = d3.pointer(event, containerEl);
				tooltipDiv
					.style("left", `${mx + 15}px`)
					.style("top", `${my - 10}px`);
			})
			.on("mouseleave", function (_event, d: any) {
				const normElev = (d.elevation - baseElev) / (elevMax - baseElev);
				const [xLeft, xRight] = mountainXAtHeight(normElev, peakNorm);
				const minX = xLeft * w + dotRadius;
				const maxX = xRight * w - dotRadius;
				const clampedX = Math.max(minX, Math.min(maxX, d.x));
				d3.select(this)
					.transition()
					.duration(200)
					.attr("transform", `translate(${clampedX - 12},${d.targetY - 12}) scale(0.7)`);

				tooltipDiv
					.style("opacity", "0")
					.style("pointer-events", "none");
			})
			.on("click", function (_event, d: any) {
				if (d.url) {
					window.location.href = d.url;
				}
			});

	}

	onMount(() => {
		const resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				width = entry.contentRect.width;
				height = Math.max(160, Math.min(220, width * 0.4));
			}
		});

		if (containerEl) {
			resizeObserver.observe(containerEl);
			width = containerEl.clientWidth;
			height = Math.max(160, Math.min(220, width * 0.4));
		}

		return () => resizeObserver.disconnect();
	});

	$effect(() => {
		if (elevationPoints.length > 0 && width > 0) {
			drawChart();
		}
	});
</script>

{#if elevationPoints.length > 0}
	<div
		class="relative w-full {className}"
		bind:this={containerEl}
	>
		<svg
			bind:this={svgElement}
			{width}
			{height}
			viewBox="0 0 {width} {height}"
			class="w-full h-auto"
		></svg>
		<div
			bind:this={tooltipEl}
			class="z-50 absolute bg-white dark:bg-slate-800 opacity-0 shadow-lg px-3 py-2 border border-gray-200 dark:border-slate-600 rounded-lg transition-opacity duration-150 pointer-events-none"
			style="left: 0; top: 0;"
		></div>
	</div>
{/if}

<style>
	:global(.bean-tree) {
		user-select: none;
	}
</style>
