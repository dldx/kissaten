<script lang="ts">
	import * as d3 from "d3";
	import { onMount } from "svelte";
	import type { SunburstData } from "$lib/types/sunburst";
	import { getFlavourCategoryHexColor } from "$lib/utils";
	import {
		fetchAndSetFlavourImage,
		clearFlavourImage,
	} from "$lib/services/flavourImageService";
	import { flavourImagesEnabled } from "$lib/stores/settingsStore";

	interface Props {
		data: SunburstData;
		className?: string;
		onTastingNoteClick?: (tastingNote: string) => void;
	}

	let { data, className = "", onTastingNoteClick }: Props = $props();

	let svgElement: SVGSVGElement;
	let containerEl: HTMLDivElement;
	let width = $state(800);
	let height = $state(800);
	let tooltip: HTMLDivElement;
	let currentZoomLevel = 0; // Track current zoom depth
	let isTransitioning = false; // Prevent hover artifacts during zoom
	let isMobile = $state(false); // Track if we're on mobile

	// Pinch-to-zoom and drag state
	let pinchZoomScale = 1; // Current pinch zoom scale
	let baseZoomScale = 1; // Base zoom scale before pinch
	let isPinching = false; // Whether user is currently pinching
	let lastPinchDistance = 0; // Last recorded pinch distance
	let pinchCenter = { x: 0, y: 0 }; // Center point of pinch gesture
	let showPinchHint = $state(false); // Show pinch-to-zoom hint on mobile
	let lastTapTime = 0; // For double-tap detection

	// Pan state
	let panOffset = { x: 0, y: 0 }; // Current pan offset
	let basePanOffset = { x: 0, y: 0 }; // Base pan offset before gesture
	let isDragging = false; // Whether user is currently dragging
	let lastTouchPosition = { x: 0, y: 0 }; // Last single touch position
	let gestureStartPosition = { x: 0, y: 0 }; // Position when gesture started

	function handleFlavourMouseEnter(notes: string[]) {
		if ($flavourImagesEnabled) {
			fetchAndSetFlavourImage(notes);
		}
	}

	function handleFlavourMouseLeave() {
		if ($flavourImagesEnabled) {
			clearFlavourImage();
		}
	}

	// Calculate distance between two touch points
	function getTouchDistance(touches: TouchList): number {
		if (touches.length < 2) return 0;
		const dx = touches[0].clientX - touches[1].clientX;
		const dy = touches[0].clientY - touches[1].clientY;
		return Math.sqrt(dx * dx + dy * dy);
	}

	// Calculate center point between two touches
	function getTouchCenter(touches: TouchList): { x: number; y: number } {
		if (touches.length < 2) return { x: 0, y: 0 };
		return {
			x: (touches[0].clientX + touches[1].clientX) / 2,
			y: (touches[0].clientY + touches[1].clientY) / 2
		};
	}

	// Handle touch start for pinch gestures and drag
	function handleTouchStart(event: TouchEvent) {
		if (!isMobile || isTransitioning) return;

		if (event.touches.length === 2) {
			event.preventDefault();
			isPinching = true;
			isDragging = false; // Stop dragging when pinching starts
			lastPinchDistance = getTouchDistance(event.touches);
			pinchCenter = getTouchCenter(event.touches);
			baseZoomScale = pinchZoomScale;
			basePanOffset = { ...panOffset };
		} else if (event.touches.length === 1) {
			// Single touch - check for double tap or start dragging
			const currentTime = Date.now();
			if (currentTime - lastTapTime < 300) {
				// Double tap detected - reset zoom and pan
				event.preventDefault();
				resetAllTransforms();
			} else {
				// Start potential drag gesture
				isDragging = true;
				isPinching = false;
				lastTouchPosition = {
					x: event.touches[0].clientX,
					y: event.touches[0].clientY
				};
				gestureStartPosition = { ...lastTouchPosition };
				basePanOffset = { ...panOffset };
			}
			lastTapTime = currentTime;
		}
	}

	// Handle touch move for pinch gestures and drag
	function handleTouchMove(event: TouchEvent) {
		if (!isMobile) return;

		event.preventDefault();

		if (isPinching && event.touches.length === 2) {
			// Pinch gesture
			const currentDistance = getTouchDistance(event.touches);
			if (lastPinchDistance > 0) {
				const scaleChange = currentDistance / lastPinchDistance;
				const newScale = baseZoomScale * scaleChange;

				// Apply bounds to zoom scale (0.5x to 3x)
				pinchZoomScale = Math.max(0.5, Math.min(3, newScale));

				// Update pinch center for combined zoom and pan
				pinchCenter = getTouchCenter(event.touches);
			}
		} else if (isDragging && event.touches.length === 1) {
			// Drag gesture
			const currentTouch = event.touches[0];
			const deltaX = currentTouch.clientX - lastTouchPosition.x;
			const deltaY = currentTouch.clientY - lastTouchPosition.y;

			// Apply pan offset with zoom scaling (pan should be less effective when zoomed in)
			const panScale = 1 / Math.max(1, pinchZoomScale);

			// Apply pan offset - no need to flip axes, just use direct delta
			panOffset.x = basePanOffset.x + deltaX * panScale;
			panOffset.y = basePanOffset.y + deltaY * panScale;

			// Apply bounds to prevent panning too far
			const maxPan = 200; // Maximum pan distance
			panOffset.x = Math.max(-maxPan, Math.min(maxPan, panOffset.x));
			panOffset.y = Math.max(-maxPan, Math.min(maxPan, panOffset.y));

			lastTouchPosition = {
				x: currentTouch.clientX,
				y: currentTouch.clientY
			};
		}

		// Apply combined transformation
		applyCombinedTransform();
	}

	// Handle touch end for pinch gestures and drag
	function handleTouchEnd(event: TouchEvent) {
		if (!isMobile) return;

		if (event.touches.length < 2) {
			isPinching = false;
			lastPinchDistance = 0;
		}

		if (event.touches.length === 0) {
			isDragging = false;
		}
	}

	// Apply combined zoom and pan transformation to the chart group
	function applyCombinedTransform() {
		if (!svgElement) return;

		// Find the main chart group (the one containing all the chart elements)
		const chartGroup = d3.select(svgElement).select('g');
		if (chartGroup.empty()) return;

		// Calculate the center point relative to the SVG, accounting for DPI scaling
		const rect = svgElement.getBoundingClientRect();
		const devicePixelRatio = window.devicePixelRatio || 1;

		// Convert screen coordinates to SVG coordinates
		const centerX = (pinchCenter.x - rect.left) * (svgElement.clientWidth / rect.width);
		const centerY = (pinchCenter.y - rect.top) * (svgElement.clientHeight / rect.height);

		// Convert to SVG coordinate system (center relative to SVG center)
		const svgCenterX = centerX - svgElement.clientWidth / 2;
		const svgCenterY = centerY - svgElement.clientHeight / 2;

		// Apply combined transformation: pan + zoom around center + pan offset
		const transform = `translate(${panOffset.x}, ${panOffset.y}) translate(${svgCenterX}, ${svgCenterY}) scale(${pinchZoomScale}) translate(${-svgCenterX}, ${-svgCenterY})`;
		chartGroup.attr('transform', transform);

		// Update text size based on zoom level
		updateTextSize();
	}

	// Apply pinch zoom transformation to the chart group (legacy function for compatibility)
	function applyPinchZoom() {
		applyCombinedTransform();
	}

	// Update text size based on zoom level
	function updateTextSize() {
		if (!svgElement) return;

		const chartGroup = d3.select(svgElement).select('g');
		if (chartGroup.empty()) return;

		// Calculate text scale based on zoom level
		// When zoomed in (scale > 1), make text smaller
		// When zoomed out (scale < 1), make text larger
		const textScale = Math.max(0.5, Math.min(1.5, 1 / pinchZoomScale));
		const fontSize = Math.max(6, Math.min(12, 10 * textScale)); // Base font size is 10px

		// Update all text elements in the chart
		chartGroup.selectAll('text')
			.style('font-size', `${fontSize}px`);
	}

	// Reset pan offset
	function resetPan() {
		panOffset = { x: 0, y: 0 };
		basePanOffset = { x: 0, y: 0 };
	}

	// Reset pinch zoom
	function resetPinchZoom() {
		pinchZoomScale = 1;
		baseZoomScale = 1;
	}

	// Reset both zoom and pan
	function resetAllTransforms() {
		resetPinchZoom();
		resetPan();
		if (svgElement) {
			const chartGroup = d3.select(svgElement).select('g');
			if (!chartGroup.empty()) {
				chartGroup.attr('transform', '');
				// Reset text size to default
				chartGroup.selectAll('text')
					.style('font-size', '10px');
			}
		}
	}

	// Update mobile detection based on screen width
	function updateMobileDetection() {
		if (typeof window !== 'undefined') {
			isMobile = window.innerWidth < 768; // Tailwind's md breakpoint
		}
	}

	function createChartWithData(chartData: SunburstData) {
		if (!svgElement) return;

		// Reset all transforms when creating new chart
		resetAllTransforms();

		d3.select(svgElement).selectAll("*").remove(); // Clear previous chart

	// Compute the hierarchy first to get its height for radius calculation.
	const hierarchy = d3
		.hierarchy(chartData as any)
		.sum((d: any) => d.value)
		.sort((a: any, b: any) => b.value - a.value);

	// The base radius of each level in the chart.
	// We will scale this based on zoom depth to provide more room for labels.
	// Use the smaller dimension to ensure the chart fits in both width and height
	const minDimension = Math.min(width, height);
	// Use a balanced base radius calculation for better scaling across screen sizes
	const baseRadius = minDimension / ((hierarchy.height + 1) * 2.0);
		let ringRadius = baseRadius;

	// Compute a target radius scale based on current zoom depth.
	// Increase per level up to a cap to avoid overflowing the viewBox.
	function computeRadiusScale(depth: number) {
		const totalLevels = hierarchy.height + 1;
		const remaining = Math.max(1, totalLevels - depth);
		const minViewportSide = Math.min(width, height);

		// Use a more conservative percentage of available space to prevent over-zooming
		const spaceUtilization = Math.min(0.85, Math.max(0.6, 0.5 + (minViewportSide / 1200))); // Adaptive based on screen size
		const targetOuter = (minViewportSide / 2) * spaceUtilization;
		const currentOuterAtBase = baseRadius * remaining;
		const viewportScale = targetOuter / currentOuterAtBase;

		// More conservative scaling that works better across different screen sizes
		let extra = 1.0;
		if (depth >= 1) extra = 1.05;
		if (depth >= 2) extra = 1.15;
		if (depth >= 3) extra = 1.3;
		if (depth >= 4) extra = 1.5;
		if (depth >= 5) extra = 1.7;

		const minScale = 1; // never shrink below base
		return Math.max(minScale, viewportScale * extra);
	}

		function useNonLinearRadius() {
			return currentZoomLevel >= 2; // Enable earlier for better space distribution
		}

		// Stepped weights for remaining visible levels (inner -> outer).
		// Tweak these arrays to customize how much radius each ring receives.
		// Optimized for better scaling across different screen sizes
		const steppedWeights: Record<number, number[]> = {
			1: [1],
			2: [0.6, 3.5],
			3: [1, 1.4, 2.4],
			4: [1, 1.3, 1.6, 2.4],
			5: [1, 1.2, 1.4, 1.6, 2.6],
			6: [1, 1.1, 1.3, 1.5, 1.7, 2.0],
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
		// Use square viewBox based on the smaller dimension for consistent circular chart
		const svg = d3
			.select(svgElement)
			.attr("viewBox", [-minDimension / 2, -minDimension / 2, minDimension, minDimension])
			.style("font", "10px sans-serif");

		// Store the color for each node based on its top-level ancestor
		root.descendants().forEach((d: any) => {
			let ancestor = d;
			while (ancestor.depth > 1) ancestor = ancestor.parent;
			d.color = color(ancestor.data.name);
		});
		const group = svg.append("g");

		// Append the arcs.
		const path = group
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

		// Make them clickable - both parent nodes (for zoom) and leaf nodes (for tasting note selection)
		// On mobile, leaf nodes should only show tooltip, not directly filter
		path.filter((d: any) => d.children || (onTastingNoteClick && !isMobile))
			.style("cursor", "pointer")
			.on("click", clicked);

		// On mobile, add click handlers to leaf nodes to show tooltip
		if (isMobile && onTastingNoteClick) {
			path.filter((d: any) => !d.children)
				.style("cursor", "pointer")
				.on("click", (event: MouseEvent, d: any) => {
					if (isTransitioning) return;
					// Trigger hover behavior to show tooltip with button
					hovered(event, d);
				});
		}

		const label = group
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

			// Different tooltip content for mobile leaf nodes
			const isLeafNode = !p.children;
			const actionText = p.children ? "<strong>Click to zoom in.</strong>" : "<strong>Click to filter by note.</strong>";

			if (isMobile && isLeafNode && onTastingNoteClick) {
				// Mobile leaf node with button
				tooltip.innerHTML = `
					<div class="max-w-xs font-bold break-words">${breadcrumb}</div>
					<div class="opacity-80 mb-2 text-xs">Spotted ${valueText} time${p.value === 1 ? "" : "s"}</div>
					<button
						class="bg-primary hover:bg-primary/90 px-3 rounded-md h-9 text-primary-foreground"
						onclick="window.addTastingNoteFilter('${p.data.name.replace(/'/g, "\\'")}')">
						Add to Filters
					</button>
				`;
			} else {
				// Regular tooltip
				tooltip.innerHTML = `
					<div class="max-w-xs font-bold break-words">${breadcrumb}</div>
					<div class="opacity-80 text-xs">Spotted ${valueText} time${p.value === 1 ? "" : "s"}. ${actionText}</div>
				`;
			}
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


		const parent = group
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

			// Reset all transforms when clicking on chart elements
			resetAllTransforms();

			// If this is a leaf node (no children) and we have a callback, emit the tasting note
			// On mobile, leaf nodes should only show tooltip, not directly filter
			if (!p.children && onTastingNoteClick && p.data?.name && !isMobile) {
				// Don't zoom, just emit the tasting note
				onTastingNoteClick(p.data.name);
				return;
			}

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
				).style("cursor", (d: any) => {
					// Show pointer for parent nodes (zoomable) or leaf nodes on desktop
					const isClickable = d.children || (!isMobile && onTastingNoteClick);
					return isClickable && arcVisible(d.current) ? "pointer" : "default";
				});
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
		// Initialize mobile detection
		updateMobileDetection();

		// Add resize listener to update mobile state
		const handleResize = () => {
			updateMobileDetection();
		};

		window.addEventListener('resize', handleResize);

		// Add touch event listeners for pinch-to-zoom
		if (containerEl) {
			containerEl.addEventListener('touchstart', handleTouchStart, { passive: false });
			containerEl.addEventListener('touchmove', handleTouchMove, { passive: false });
			containerEl.addEventListener('touchend', handleTouchEnd, { passive: false });
		}

		// Create global function for mobile button clicks
		(window as any).addTastingNoteFilter = (tastingNote: string) => {
			if (onTastingNoteClick) {
				onTastingNoteClick(tastingNote);
			}
		};

		if (data && svgElement) {
			createChartWithData(data);
		}

		// Show pinch-to-zoom hint on mobile after a short delay
		if (isMobile) {
			setTimeout(() => {
				showPinchHint = true;
				// Hide hint after 3 seconds
				setTimeout(() => {
					showPinchHint = false;
				}, 3000);
			}, 1000);
		}

		// Cleanup
		return () => {
			window.removeEventListener('resize', handleResize);
			if (containerEl) {
				containerEl.removeEventListener('touchstart', handleTouchStart);
				containerEl.removeEventListener('touchmove', handleTouchMove);
				containerEl.removeEventListener('touchend', handleTouchEnd);
			}
			delete (window as any).addTastingNoteFilter;
		};
	});
</script>

<div
	class="relative {className}"
	bind:this={containerEl}
	bind:clientWidth={width}
	bind:clientHeight={height}
>
	<svg bind:this={svgElement} class="w-full h-full"></svg>

	<!-- Tooltip (fixed at top center) -->
	<div
		bind:this={tooltip}
		class="top-16 md:top-0 left-1/2 z-20 fixed md:absolute bg-gray-900/95 opacity-0 shadow-lg px-2.5 py-1.5 border border-white/10 rounded-md text-white text-xs sm:text-sm transition-opacity -translate-x-1/2 duration-150 pointer-events-auto"
	></div>

	<!-- Pinch-to-zoom and drag hint for mobile -->
	{#if showPinchHint && isMobile}
		<div class="top-4 left-1/2 z-10 absolute bg-primary/90 shadow-lg px-3 py-2 rounded-md text-primary-foreground text-xs transition-opacity -translate-x-1/2 duration-300 pointer-events-none">
			Pinch to zoom • Drag to pan • Double-tap to reset
		</div>
	{/if}
</div>
