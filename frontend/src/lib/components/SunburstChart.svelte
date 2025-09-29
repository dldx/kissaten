<script lang="ts">
	import * as d3 from "d3";
	import { onMount } from "svelte";
	import type { SunburstData } from "$lib/types/sunburst";
	import { getFlavourCategoryHexColor } from "$lib/utils";
	import {
		fetchAndSetFlavourImage,
		clearFlavourImage,
	} from "$lib/services/flavourImageService";

	interface Props {
		data: SunburstData;
		width?: number;
		height?: number;
		className?: string;
	}

	let { data, width = 800, height = 800, className = "" }: Props = $props();

	let svgElement: SVGSVGElement;
	let containerEl: HTMLDivElement;
	let tooltip: HTMLDivElement;
	let currentZoomLevel = 0; // Track current zoom depth
	let isTransitioning = false; // Prevent hover artifacts during zoom

	function handleFlavourMouseEnter(notes: string[]) {
		fetchAndSetFlavourImage(notes);
	}

	function handleFlavourMouseLeave() {
		clearFlavourImage();
	}

	function createChartWithData(chartData: SunburstData) {
		if (!svgElement) return;
		d3.select(svgElement).selectAll("*").remove(); // Clear previous chart

		// Compute the hierarchy first to get its height for radius calculation.
		const hierarchy = d3
			.hierarchy(chartData as any)
			.sum((d: any) => d.value)
			.sort((a: any, b: any) => b.value - a.value);

		// The base radius of each level in the chart.
		// We will scale this based on zoom depth to provide more room for labels.
		const baseRadius = width / ((hierarchy.height + 1) * 2.2);
		let ringRadius = baseRadius;

		// Compute a target radius scale based on current zoom depth.
		// Increase per level up to a cap to avoid overflowing the viewBox.
		function computeRadiusScale(depth: number) {
			const totalLevels = hierarchy.height + 1;
			const remaining = Math.max(1, totalLevels - depth);
			const minViewportSide = Math.min(width, height);
			const targetOuter = (minViewportSide / 2) * 0.98; // fill ~98% of half-size
			const currentOuterAtBase = baseRadius * remaining;
			const viewportScale = targetOuter / currentOuterAtBase;
			const extra = depth >= 4 ? 1.1 : 1.0; // stronger boost when deep
			const minScale = 1; // never shrink below base
			return Math.max(minScale, viewportScale * extra);
		}

		// Exponent factor to stretch outer rings much more than inner rings when enabled.
		function computeRadialGamma(depth: number) {
			const baseGamma = 1.5;
			const perLevelGamma = 0.5;
			const maxLevelsToScale = 2;
			return (
				baseGamma + perLevelGamma * Math.min(depth, maxLevelsToScale)
			);
		}

		function useNonLinearRadius() {
			return currentZoomLevel >= 4;
		}

		// Stepped weights for remaining visible levels (inner -> outer).
		// Tweak these arrays to customize how much radius each ring receives.
		const steppedWeights: Record<number, number[]> = {
			1: [1],
			2: [1, 2.2],
			3: [1, 1.2, 3.0],
			4: [1, 1.2, 1.6, 3.2],
			5: [1, 1.1, 1.1, 1.1, 3.4],
			6: [1, 1.05, 1.2, 1.4, 1.8, 3.6],
		};

		function getWeights(remaining: number): number[] {
			const base = steppedWeights[remaining] ?? steppedWeights[6] ?? [];
			// Ensure length matches remaining levels
			let weights = base.slice(0, remaining);
			if (weights.length < remaining) {
				const outerBoost =
					weights.length > 0 ? weights[weights.length - 1] : 3.0;
				weights = weights.concat(
					new Array(Math.max(0, remaining - weights.length - 1)).fill(
						1,
					),
				);
				weights.push(outerBoost);
			}
			return weights;
		}

		// Map hierarchical y (ring index) into actual radius using stepped weights when enabled.
		function mapRadius(y: number, ringR: number) {
			const totalLevels = hierarchy.height + 1;
			const remaining = Math.max(1, totalLevels - currentZoomLevel);
			if (!useNonLinearRadius()) return y * ringR; // linear mapping

			const weights = getWeights(remaining);
			const cum: number[] = [0];
			for (let i = 0; i < remaining; i++)
				cum.push(cum[i] + (weights[i] ?? 1));
			const totalW = cum[cum.length - 1] || 1;

			// y is in [0, remaining]; map piecewise linearly between steps using weights
			const clampedY = Math.max(0, Math.min(remaining, y));
			const idx = Math.min(
				remaining - 1,
				Math.max(0, Math.floor(clampedY)),
			);
			const frac = clampedY - idx;
			const segStart = cum[idx];
			const segEnd = cum[idx + 1];
			const mapped = segStart + frac * (segEnd - segStart);
			return (mapped / totalW) * ringR * remaining;
		}

		// Helper for truncating labels to fit available arc length.
		// Uses a simple average character width heuristic for the current font size.
		const AVG_CHAR_PX = 1.25; // approx width for 10px sans-serif
		const LABEL_PADDING_PX = 0; // avoid touching arc boundaries
		function truncatedLabel(d: any) {
			const node = d.current ?? d;
			const name: string = d.data?.name ?? "";
			if (!name) return "";
			const angle = Math.max(0, node.x1 - node.x0);
			const yMid = mapRadius((node.y0 + node.y1) / 2, ringRadius);
			const availablePx = Math.max(0, yMid * angle - LABEL_PADDING_PX);
			const maxChars = Math.floor(availablePx / AVG_CHAR_PX);
			if (maxChars <= 0) return "";
			if (name.length <= maxChars) return name;
			return name.slice(0, Math.max(0, maxChars - 1)) + "…";
		}

		// Create a dynamic color scale based on the categories present in the data.
		const categories = (chartData.children || []).map((d) => d.name);
		const color = d3.scaleOrdinal(
			categories,
			categories.map(getFlavourCategoryHexColor),
		);

		// Compute the layout.
		const root = d3.partition().size([2 * Math.PI, hierarchy.height + 1])(
			hierarchy,
		);
		root.each((d: any) => (d.current = d));
		let focusedNode: any = root;

		// Create the arc generator.
		const arc = d3
			.arc<any>()
			.startAngle((d) => d.x0)
			.endAngle((d) => d.x1)
			.padAngle(0) //(d) => Math.min((d.x1 - d.x0) / 2, 0.005))
			.padRadius(() => ringRadius * 1.5)
			.innerRadius((d) => mapRadius(d.y0, ringRadius))
			.outerRadius((d) => {
				const inner = mapRadius(d.y0, ringRadius);
				const outer = mapRadius(d.y1, ringRadius);
				return Math.max(inner, outer - 1);
			});

		// Create the SVG container.
		const svg = d3
			.select(svgElement)
			.attr("viewBox", [-width / 2, -height / 2, width, width])
			.style("font", "10px sans-serif");

		// Store the color for each node based on its top-level ancestor
		root.descendants().forEach((d: any) => {
			let ancestor = d;
			while (ancestor.depth > 1) ancestor = ancestor.parent;
			d.color = color(ancestor.data.name);
		});

		// Append the arcs.
		const path = svg
			.append("g")
			.selectAll("path")
			.data(root.descendants().slice(1))
			.join("path")
			.attr("fill", (d: any) => d.color)
			.attr("fill-opacity", (d: any) =>
				arcVisible(d.current) ? (d.children ? 0.8 : 0.6) : 0,
			)
			.attr("stroke", (d: any) => "#111")
			.attr("stroke-width", (d: any) =>
				arcVisible(d.current) ? (d.children ? 0.5 : 0.25) : 0,
			)
			.attr("pointer-events", (d: any) =>
				arcVisible(d.current) ? "auto" : "none",
			)
			.attr("d", (d: any) => arc(d.current));

		// Hover highlight: emphasize ancestors and show tooltip
		path.on("mouseover", hovered).on("mouseout", unhovered);

		// Make them clickable if they have children.
		path.filter((d: any) => d.children)
			.style("cursor", "pointer")
			.on("click", clicked);

		const format = d3.format(",d");
		// path.append('title').text(
		// 	(d: any) =>
		// 		`${d
		// 			.ancestors()
		// 			.map((d: any) => d.data.name)
		// 			.reverse()
		// 			.join('/')}\n${format(d.value)}`
		// );

		const label = svg
			.append("g")
			.attr("pointer-events", "none")
			.attr("text-anchor", "middle")
			.style("user-select", "none")
			.selectAll("text")
			.data(root.descendants().slice(1))
			.join("text")
			.attr("dy", "0.35em")
			.attr("fill-opacity", (d: any) => +labelVisible(d.current))
			.attr("transform", (d: any) => labelTransform(d.current))
			.text((d: any) => truncatedLabel(d));

		function hovered(event: MouseEvent, p: any) {
			if (isTransitioning) return;
			handleFlavourMouseEnter([
				...new Set(
					p
						.ancestors()
						.map((d: any) => d.data.name.replace(/Other/g, ""))
						.filter(
							(d: string) =>
								d != "" &&
								d != "General" &&
								d != "Tasting Notes",
						)
						.slice(0, 5),
				),
			] as string[]);
			const ancestors: any[] = p.ancestors();
			// Highlight ancestor chain, respecting base visibility so hidden arcs stay hidden
			path.attr("fill-opacity", (d: any) => {
				const base = arcVisible(d.current)
					? d.children
						? 0.8
						: 0.6
					: 0;
				if (base === 0) return 0;
				return ancestors.includes(d)
					? Math.max(base, 0.95)
					: Math.min(base, 0.15);
			})
				.attr("stroke", (d: any) =>
					ancestors.includes(d) ? "#111" : null,
				)
				.attr("stroke-width", (d: any) =>
					ancestors.includes(d) ? 0.5 : null,
				);

			// Tooltip content
			const format = d3.format(",d");
			const breadcrumb = p
				.ancestors()
				.map((d: any, index: number) =>
					index === 0
						? d.data.name
						: `<span class="font-normal">${d.data.name}</span>`,
				)
				.reverse()
				.join('<span class="font-normal"> > </span>');
			const valueText = format(p.value ?? 0);
			tooltip.innerHTML = `<div class="font-bold">${breadcrumb}</div><div class="opacity-80 text-xs">Spotted ${valueText} time${p.value === 1 ? "" : "s"}</div>`;
			tooltip.style.opacity = "1";
		}

		// Tooltip uses fixed positioning; no cursor-follow behavior

		function unhovered() {
			if (isTransitioning) return;
			handleFlavourMouseLeave();
			// Restore to visibility logic
			path.attr("fill-opacity", (d: any) =>
				arcVisible(d.current) ? (d.children ? 0.8 : 0.6) : 0,
			)
				.attr("stroke", (d: any) =>
					arcVisible(d.current) ? (d.children ? "#111" : null) : null,
				)
				.attr("stroke-width", (d: any) =>
					arcVisible(d.current) ? (d.children ? 0.5 : 0.25) : 0,
				);
			if (tooltip) tooltip.style.opacity = "0";
		}

		function parentHovered(event: MouseEvent) {
			if (isTransitioning || currentZoomLevel <= 0) return;
			if (!focusedNode) return;
			const format = d3.format(",d");
			const breadcrumb = focusedNode
				.ancestors()
				.map((d: any) => d.data.name)
				.reverse()
				.join(" / ");
			const valueText = format(focusedNode.value ?? 0);
			tooltip.innerHTML = `<div class="font-medium">${breadcrumb}</div><div class=\"opacity-80 text-xs\">${valueText}</div>`;
			tooltip.style.opacity = "1";
		}

		function parentUnhovered() {
			if (tooltip) tooltip.style.opacity = "0";
		}

		const parent = svg
			.append("circle")
			.datum(root)
			.attr("r", mapRadius(1, ringRadius))
			.attr("fill", "none")
			.attr("pointer-events", "all")
			.on("click", clicked)
			.on("mouseover", parentHovered)
			.on("mouseout", parentUnhovered);

		// Handle zoom on click.
		function clicked(event: MouseEvent, p: any) {
			if (isTransitioning) return; // Prevent new transitions while one is running
			parent.datum(p.parent || root);

			// Update zoom level based on the clicked node's depth
			// If we're going back to root (p.parent is null), reset to level 0
			currentZoomLevel = p.parent ? p.depth : 0;
			focusedNode = p;

			// Update the ring radius target for this zoom level
			const targetScale = computeRadiusScale(currentZoomLevel);
			const radiusStart = ringRadius;
			const radiusEnd = baseRadius * targetScale;

			// Clear any hover styles and disable interactions during transition
			isTransitioning = true;
			path.attr("stroke", null).attr("stroke-width", null);
			path.attr("pointer-events", "none");
			if (tooltip) tooltip.style.opacity = "0";

			root.each(
				(d: any) =>
					(d.target = {
						x0:
							Math.max(
								0,
								Math.min(1, (d.x0 - p.x0) / (p.x1 - p.x0)),
							) *
							2 *
							Math.PI,
						x1:
							Math.max(
								0,
								Math.min(1, (d.x1 - p.x0) / (p.x1 - p.x0)),
							) *
							2 *
							Math.PI,
						y0: Math.max(0, d.y0 - p.depth),
						y1: Math.max(0, d.y1 - p.depth),
					}),
			);

			const t = svg.transition().duration(750);

			// Smoothly tween the ring radius so arcs grow/shrink with zoom depth
			t.tween("radius", () => {
				const i = d3.interpolateNumber(radiusStart, radiusEnd);
				return (tt: number) => {
					ringRadius = i(tt);
					parent.attr("r", mapRadius(1, ringRadius));
				};
			});

			// Transition the data on all arcs, even the ones that aren't visible,
			// so that if this transition is interrupted, entering arcs will start
			// the next transition from the desired position.
			path.transition(t as any)
				.tween("data", (d: any) => {
					const i = d3.interpolate(d.current, d.target);
					return (t: number) => (d.current = i(t));
				})
				.filter(function (d: any) {
					const self = this as SVGPathElement;
					const fill = self.getAttribute("fill-opacity") ?? "0";
					return Boolean(+fill) || arcVisible(d.target);
				})
				// Keep the fill color constant - it was pre-computed
				.attr("fill", (d: any) => d.color)
				// Transition opacity to target visibility
				.attr("fill-opacity", (d: any) =>
					arcVisible(d.target) ? (d.children ? 0.8 : 0.6) : 0,
				)
				.attrTween("d", (d: any) => () => arc(d.current) ?? "");

			label
				.filter(function (d: any) {
					const self = this as SVGTextElement;
					const fill = self.getAttribute("fill-opacity") ?? "0";
					return Boolean(+fill) || labelVisible(d.target);
				})
				.transition(t as any)
				.attr("fill-opacity", (d: any) => +labelVisible(d.target))
				// Continuously recompute truncated text as geometry changes
				.tween("text", function (d: any) {
					const self = this as SVGTextElement;
					return () => {
						(self as any).textContent = truncatedLabel(d);
					};
				})
				.attrTween("transform", ((d: any) => {
					// Use d.current which is being animated by the path tween
					const tween = () => labelTransform(d.current);
					return tween as unknown as (
						this: SVGTextElement,
						t: number,
					) => string;
				}) as any);

			// Ensure we re-enable interactions after the overall transition completes
			t.on("end", () => {
				isTransitioning = false;
				// At this point, d.current has been updated to d.target values
				path.attr("pointer-events", (d: any) =>
					arcVisible(d.current) ? "auto" : "none",
				).style("cursor", (d: any) =>
					d.children && arcVisible(d.current) ? "pointer" : "default",
				);
				// Finalize truncated label text after transition
				label.text((d: any) => truncatedLabel(d));
			});
		}

		function arcVisible(d: any) {
			if (!d) return false;

			// Hide children of "Other" nodes when zoomed out less than 2 levels
			if (d.parent?.data.isOther && currentZoomLevel < 2) {
				return false;
			}

			return d.y1 <= hierarchy.height + 1 && d.y0 >= 0 && d.x1 > d.x0;
		}

		function labelVisible(d: any) {
			if (!d) return false;

			// Hide labels of children of "Other" nodes when zoomed out less than 2 levels
			if (d.parent?.data.isOther && currentZoomLevel < 2) {
				return false;
			}

			return (
				d.y1 <= hierarchy.height + 1 &&
				d.y0 >= 0 &&
				(d.y1 - d.y0) * (d.x1 - d.x0) > 0.03
			);
		}

		function labelTransform(d: any) {
			const x = (((d.x0 + d.x1) / 2) * 180) / Math.PI;
			const y = mapRadius((d.y0 + d.y1) / 2, ringRadius);
			return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
		}
	}

	$effect.pre(() => {
		// Rerender chart when data changes
		if (data && svgElement) {
			createChartWithData(data);
		}
	});

	onMount(() => {
		if (data && svgElement) {
			createChartWithData(data);
		}
	});
</script>

<div
	class="relative {className}"
	style="min-height: {height}px"
	bind:this={containerEl}
>
	<svg bind:this={svgElement} class="w-full h-auto"></svg>

	<!-- Tooltip (fixed at top center) -->
	<div
		bind:this={tooltip}
		class="top-2 left-1/2 z-20 absolute bg-gray-900/95 opacity-0 shadow-lg px-2.5 py-1.5 border border-white/10 rounded-md text-white text-xs sm:text-sm whitespace-nowrap transition-opacity -translate-x-1/2 duration-150 pointer-events-none"
	></div>
</div>
