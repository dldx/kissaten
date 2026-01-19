<script lang="ts">
    import { onMount, untrack } from "svelte";
    import * as d3 from "d3";
    import forceBoundary from "d3-force-boundary";
    import type { Roaster } from "$lib/api";
    import { Coffee, MapPin, Globe, ExternalLink, X } from "lucide-svelte";
    import { Button } from "$lib/components/ui/button";
    import { fade } from "svelte/transition";
    import { addUtmParams } from "$lib/utils";

    interface Props {
        roasters: Roaster[];
        debouncedSearchQuery?: string;
    }

    let { roasters, debouncedSearchQuery = "" }: Props = $props();

    let container = $state<HTMLDivElement>();
    let svgElement = $state<SVGSVGElement>();
    let width = $state(0);
    let height = $state(0);

    let renderingNodes = $state<any[]>([]);
    let internalNodes: any[] = [];
    let simulation: d3.Simulation<any, undefined>;

    let hoveredRoaster = $state<any | null>(null);
    let selectedRoaster = $state<any | null>(null);

    // Tooltip state
    const activeRoaster = $derived(selectedRoaster || hoveredRoaster);
    let tooltipPos = $state({ x: 0, y: 0 });

    const STICKER_SIZE = $derived(width < 640 ? 70 : 130);
    const PADDING = $derived(width < 640 ? 20 : 20);

    let imageErrors = $state<Record<string, boolean>>({});
    let searchCollisionDisabled = $state(false);
    let searchTimeout: any;

    // Coffee ring textures for background decoration
    interface CoffeeRing {
        x: number;
        y: number;
        size: number;
        rotation: number;
        opacity: number;
        image: number; // 1 or 2
    }
    let coffeeRings = $state<CoffeeRing[]>([]);

    function getCacheKey() {
        if (width === 0 || height === 0) return null;
        const ids = roasters
            .map((r) => r.id)
            .sort()
            .join(",");
        return `roaster-positions-2332-${width}-${height}-${ids}`;
    }

    function savePositions() {
        if (debouncedSearchQuery) return;
        const key = getCacheKey();
        if (!key) return;

        const positions = internalNodes.map((n) => ({
            id: n.id,
            x: n.x,
            y: n.y,
        }));

        try {
            localStorage.setItem(key, JSON.stringify(positions));
        } catch (e) {
            console.warn("Failed to save roaster positions to cache", e);
        }
    }

    function loadCachedPositions() {
        const key = getCacheKey();
        if (!key) return null;

        try {
            const cached = localStorage.getItem(key);
            if (cached) {
                return JSON.parse(cached);
            }
        } catch (e) {
            console.warn("Failed to load roaster positions from cache", e);
        }
        return null;
    }

    // Update tooltip position when active roaster moves or changes
    $effect(() => {
        // Access renderingNodes to trigger re-run on every simulation tick
        renderingNodes;
        if (activeRoaster && svgElement) {
            const rect = svgElement.getBoundingClientRect();
            tooltipPos = {
                x: rect.left + activeRoaster.x,
                y: rect.top + activeRoaster.y,
            };
        }
    });

    // Optimized search matching
    const matchedIds = $derived.by(() => {
        if (!debouncedSearchQuery) return new Set<number>();
        const q = debouncedSearchQuery.toLowerCase().trim();
        if (q.length === 0) return new Set<number>();
        const terms = q.split(/\s+/);

        return new Set(
            roasters
                .filter((r) => {
                    const name = (r.name || "").toLowerCase();
                    const location = (r.location || "").toLowerCase();
                    return terms.every(
                        (t) => name.includes(t) || location.includes(t),
                    );
                })
                .map((r) => r.id),
        );
    });

    const isMatch = (node: any) => matchedIds.has(node.id);

    function getCollisionRadius(d: any) {
        if (searchCollisionDisabled && isMatch(d)) {
            return 0;
        }
        return STICKER_SIZE / 2 + PADDING;
    }

    // Unified Simulation Update
    function syncForces() {
        if (!simulation || width === 0 || roasters.length === 0) return;

        const query = (debouncedSearchQuery || "").trim().toLowerCase();
        const currentWidth = width;
        const currentHeight = height;

        console.debug("[StickerWall] syncForces", {
            query,
            nodes: roasters.length,
        });

        // 1. Sync Nodes
        const existingNodes = new Map(internalNodes.map((n) => [n.id, n]));
        const cachedPositions = loadCachedPositions();
        const cachedMap = cachedPositions
            ? new Map(cachedPositions.map((p: any) => [p.id, p]))
            : null;

        internalNodes = roasters.map((r) => {
            const existing = existingNodes.get(r.id);
            const cached = cachedMap?.get(r.id);

            const x =
                existing?.x ??
                cached?.x ??
                currentWidth / 2 + (Math.random() - 0.5) * currentWidth * 0.5;
            const y =
                existing?.y ??
                cached?.y ??
                currentHeight / 2 + (Math.random() - 0.5) * currentHeight * 0.5;

            return {
                ...r,
                x: isNaN(x) ? currentWidth / 2 : x,
                y: isNaN(y) ? currentHeight / 2 : y,
                vx: existing?.vx ?? 0,
                vy: existing?.vy ?? 0,
            };
        });

        simulation.nodes(internalNodes);

        // 2. Configure Forces
        const boundaryPadding = STICKER_SIZE / 2 + 20;
        simulation.force(
            "boundary",
            forceBoundary(
                boundaryPadding,
                boundaryPadding,
                currentWidth - boundaryPadding,
                currentHeight - boundaryPadding,
            ),
        );
        // Coordinate roasters horizontally
        simulation.force(
            "x",
            d3
                .forceX()
                .x((d: any) => {
                    if (query && isMatch(d)) {
                        // Spread matched nodes out across a 70% wide center band instead of a single point
                        // We use the ID to create a stable but distributed horizontal target
                        const spread = currentWidth * 0.7;
                        const start = (currentWidth - spread) / 2;
                        const seed = (d.id * 17) % 100; // Consistent pseudo-random distribution
                        return start + (spread * seed) / 100;
                    }
                    return currentWidth / 2;
                })
                .strength(query ? 0.15 : 0.05),
        );

        if (query) {
            searchCollisionDisabled = true;
            if (searchTimeout) clearTimeout(searchTimeout);

            const matchedCount = matchedIds.size;
            const cols = Math.max(
                2,
                Math.floor(currentWidth / (STICKER_SIZE + PADDING)),
            );
            const matchRows = Math.ceil(matchedCount / cols);
            const matchAreaHeight = matchRows * (STICKER_SIZE + PADDING);

            simulation.force(
                "y",
                d3
                    .forceY()
                    .y((d: any) => {
                        if (isMatch(d)) {
                            return STICKER_SIZE / 2 + 20;
                        }
                        // Push non-matches much lower down (at least 40% down or below the match area)
                        return Math.max(
                            currentHeight * 0.4,
                            matchAreaHeight + STICKER_SIZE * 2,
                        );
                    })
                    .strength((d: any) => (isMatch(d) ? 0.8 : 0.4)),
            );

            simulation.force(
                "charge",
                d3
                    .forceManyBody()
                    .strength((d: any) => (isMatch(d) ? -30 : -200)),
            );
            simulation.alphaDecay(0.015).alphaTarget(0);

            // Give them longer to float through each other before collision kicks back in
            searchTimeout = setTimeout(() => {
                searchCollisionDisabled = false;
                const c = simulation.force("collide") as d3.ForceCollide<any>;
                if (c) c.radius((d: any) => getCollisionRadius(d));
                simulation.alpha(0.3).restart();
            }, 1000);
        } else {
            if (searchTimeout) clearTimeout(searchTimeout);
            searchCollisionDisabled = false;
            const targetY =
                currentHeight > 1000
                    ? Math.min(currentHeight / 2, 600)
                    : currentHeight / 2;
            simulation.force("y", d3.forceY(targetY).strength(0.05));
            simulation.force("charge", d3.forceManyBody().strength(-400));
            simulation
                .alphaDecay(currentWidth < 640 ? 0.03 : 0.0228)
                .alphaTarget(0);
        }

        const collide = simulation.force("collide") as d3.ForceCollide<any>;
        if (collide) collide.radius((d: any) => getCollisionRadius(d));

        // 3. Kickoff
        if (cachedPositions && !query) {
            // Apply cached positions directly to ensure we snap back to the saved state
            internalNodes.forEach((node) => {
                const cached = cachedMap?.get(node.id);
                if (cached) {
                    node.x = cached.x;
                    node.y = cached.y;
                    node.vx = 0;
                    node.vy = 0;
                }
            });
            renderingNodes = internalNodes.map((n) => ({ ...n }));
            simulation.stop();
        } else {
            renderingNodes = internalNodes.map((n) => ({ ...n }));
            simulation.alpha(0.8).restart();
        }
    }

    $effect(() => {
        // Track these, but run syncForces untracked to avoid loops
        debouncedSearchQuery;
        roasters;
        width;
        height;

        untrack(() => syncForces());
    });

    function generateCoffeeRings() {
        if (width === 0 || height === 0) return;

        const ringCount = Math.floor(Math.random() * 5) + 2; // 8-12 rings
        const rings: CoffeeRing[] = [];

        for (let i = 0; i < ringCount; i++) {
            rings.push({
                x: Math.random() * width,
                y: Math.random() * height,
                size: Math.random() * 100 + 80, // 80-180px
                rotation: Math.random() * 360,
                opacity: Math.random() * 0.15 + 0.05, // 0.05-0.2
                image: Math.random() > 0.5 ? 1 : 2,
            });
        }

        coffeeRings = rings;
    }

    function calculateHeight(containerWidth: number) {
        const isMobile = containerWidth < 640;
        const estimatedColumns = Math.max(
            2,
            Math.floor(containerWidth / (isMobile ? 70 : 120)),
        );
        const estimatedRows = Math.ceil(roasters.length / estimatedColumns);
        const rowHeight = isMobile ? 70 : 160;

        let h = estimatedRows * rowHeight + 100;
        h = isMobile ? Math.min(h, 4000) : h;
        return Math.max(isMobile ? 500 : 700, h);
    }

    onMount(() => {
        const updateSize = () => {
            if (container) {
                const newWidth = container.clientWidth;
                const newHeight = calculateHeight(newWidth);

                // Mobile browsers fire resize on scroll (address bar toggle).
                // We only care if width changed or height changed significantly.
                const widthChanged = Math.abs(newWidth - width) > 2;
                const heightChanged = Math.abs(newHeight - height) > 20;

                if (!widthChanged && !heightChanged) return;

                width = newWidth;
                height = newHeight;

                // Generate coffee rings when size is first set or changes significantly
                generateCoffeeRings();

                if (simulation) {
                    const isMobile = width < 640;
                    simulation.alphaDecay(isMobile ? 0.03 : 0.0228);

                    // Forces will be fully synced by the reactive effect triggered by width/height change
                    simulation.alpha(0.3).restart();
                }
            }
        };

        simulation = d3
            .forceSimulation(internalNodes)
            .alphaDecay(width < 640 ? 0.03 : 0.0228)
            .force("x", d3.forceX(width / 2).strength(0.015))
            .force("y", d3.forceY(height / 2).strength(0.015))
            .force(
                "collide",
                d3
                    .forceCollide((d: any) => getCollisionRadius(d))
                    .strength(0.3),
            )
            .force("charge", d3.forceManyBody().strength(-400))
            .on("tick", () => {
                renderingNodes = internalNodes.map((n) => ({ ...n }));
            })
            .on("end", savePositions);

        updateSize();
        syncForces(); // Manual trigger for initially loaded sim
        window.addEventListener("resize", updateSize);

        return () => {
            window.removeEventListener("resize", updateSize);
            simulation?.stop();
        };
    });

    let delaunay = $derived.by(() => {
        if (renderingNodes.length === 0) return null;
        return d3.Delaunay.from(renderingNodes.map((d) => [d.x, d.y]));
    });

    function handleMouseLeave() {
        hoveredRoaster = null;
    }

    function handleSvgMouseMove(event: MouseEvent) {
        if (selectedRoaster || !delaunay || !svgElement) return;

        const rect = svgElement.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        const index = delaunay.find(mouseX, mouseY);
        if (index !== -1) {
            const node = renderingNodes[index];
            const dist = Math.sqrt(
                (mouseX - node.x) ** 2 + (mouseY - node.y) ** 2,
            );

            // If mouse is within or very close to the sticker
            if (dist < STICKER_SIZE / 2 + 10) {
                if (hoveredRoaster?.id !== node.id) {
                    hoveredRoaster = node;
                }
            } else {
                hoveredRoaster = null;
            }
        } else {
            hoveredRoaster = null;
        }
    }

    function handleStickerClick(node: any, event: MouseEvent) {
        event.stopPropagation();
        if (selectedRoaster?.id === node.id) {
            selectedRoaster = null;
        } else {
            selectedRoaster = node;
            hoveredRoaster = null;

            // Update tooltip position immediately on click
            if (svgElement) {
                const rect = svgElement.getBoundingClientRect();
                tooltipPos = {
                    x: rect.left + node.x,
                    y: rect.top + node.y,
                };
            }
        }
    }

    function closeTooltip() {
        selectedRoaster = null;
        hoveredRoaster = null;
    }

    function handleImageError(id: number) {
        imageErrors[id] = true;
    }
</script>

<svelte:window onclick={() => (selectedRoaster = null)} />

<div
    bind:this={container}
    class="relative bg-[radial-gradient(var(--color-border)_1px,transparent_2px)] bg-slate-50/20 dark:bg-slate-900/10 w-full bg-size-[40px_40px] overflow-visible transition-all"
    style="height: {height}px;"
>
    <svg
        bind:this={svgElement}
        {width}
        {height}
        role="application"
        aria-label="Roaster Sticker Wall"
        class="w-full h-full overflow-visible"
        onmousemove={handleSvgMouseMove}
        onmouseleave={handleMouseLeave}
    >
        <!-- Coffee ring background textures -->
        {#each coffeeRings as ring, i (i)}
            <image
                href="/textures/coffee_ring_{ring.image}.png"
                x={ring.x - ring.size / 2}
                y={ring.y - ring.size / 2}
                width={ring.size * 2}
                height={ring.size * 2}
                opacity={ring.opacity}
                transform="rotate({ring.rotation}, {ring.x}, {ring.y})"
                class="pointer-events-none select-none"
            />
        {/each}

        {#each [...renderingNodes].sort((a, b) => {
            // Priority: Active (Hovered/Selected) > Search Match > Others
            if (activeRoaster?.id === a.id) return 1;
            if (activeRoaster?.id === b.id) return -1;

            if (debouncedSearchQuery) {
                const aMatch = isMatch(a);
                const bMatch = isMatch(b);
                if (aMatch && !bMatch) return 1;
                if (!aMatch && bMatch) return -1;
            }
            return 0;
        }) as node (node.id)}
            {@const logoSrc = imageErrors[node.id]
                ? `/static/data/roasters/${node.slug}/logo.png`
                : `/static/data/roasters/${node.slug}/logo_sticker.png`}
            {@const isHovered = activeRoaster?.id === node.id}
            {@const isSearchMatch = !debouncedSearchQuery || isMatch(node)}
            <g
                transform="translate({node.x}, {node.y})"
                onclick={(e) => handleStickerClick(node, e)}
                onkeydown={(e) =>
                    e.key === "Enter" && handleStickerClick(node, e as any)}
                class="focus:outline-none overflow-visible cursor-default"
                role="button"
                tabindex="0"
                aria-label="Roaster sticker for {node.name}"
            >
                <!-- This circle provides the shape for hit detection -->
                <circle
                    r={STICKER_SIZE / 2}
                    fill="transparent"
                    class="pointer-events-all"
                />
                <foreignObject
                    x={-STICKER_SIZE / 2}
                    y={-STICKER_SIZE / 2}
                    width={STICKER_SIZE}
                    height={STICKER_SIZE}
                    class="transition-all duration-300 overflow-visible pointer-events-none {isHovered
                        ? 'drop-shadow-xl'
                        : 'drop-shadow-xs'}"
                >
                    <div
                        class="relative flex justify-center items-center w-full h-full transition-all duration-300 {isHovered
                            ? 'scale-110 -translate-y-1'
                            : ''}"
                    >
                        <img
                            src={logoSrc}
                            alt={node.name}
                            class="max-w-full max-h-full object-contain transition-all duration-500 select-none"
                            style="opacity: {isSearchMatch ? 1 : 0.1};
                                   transform: scale({isSearchMatch ? 1 : 0.8});"
                            onerror={() => handleImageError(node.id)}
                        />
                        <!-- Glossy Reflection Layers - Masked to the logo shape -->
                        <div
                            class="absolute inset-0 transition-all duration-500 pointer-events-none"
                            style="background: linear-gradient({isHovered
                                ? '145deg'
                                : '135deg'}, rgba(255,255,255,{isHovered
                                ? '0.4'
                                : '0.3'}) 0%, rgba(255,255,255,0) 45%, rgba(255,255,255,0.15) 100%);
                                   opacity: {isSearchMatch ? (isHovered ? 0.95 : 0.85) : 0.1};
                                   transform: scale({isSearchMatch ? 1 : 0.8});
                                   mask-image: url({logoSrc}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;
                                   -webkit-mask-image: url({logoSrc}); -webkit-mask-size: contain; -webkit-mask-repeat: no-repeat; -webkit-mask-position: center;"
                        ></div>
                        <div
                            class="absolute inset-0 transition-all duration-500 pointer-events-none"
                            style="background: radial-gradient(circle at {isHovered
                                ? '25% 25%'
                                : '30% 30%'}, rgba(255,255,255,{isHovered
                                ? '0.3'
                                : '0.2'}) 0%, transparent 60%);
                                   opacity: {isSearchMatch ? (isHovered ? 0.85 : 0.7) : 0.1};
                                   transform: scale({isSearchMatch ? 1 : 0.8});
                                   mask-image: url({logoSrc}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;
                                   -webkit-mask-image: url({logoSrc}); -webkit-mask-size: contain; -webkit-mask-repeat: no-repeat; -webkit-mask-position: center;"
                        ></div>
                        <!-- Sharp specular highlight -->
                        <div
                            class="absolute inset-0 transition-all duration-500 pointer-events-none"
                            style="background: radial-gradient(circle at {isHovered
                                ? '10% 15%'
                                : '15% 20%'}, rgba(255,255,255,{isHovered
                                ? '0.6'
                                : '0.4'}) 0%, transparent 40%);
                                   opacity: {isSearchMatch ? (isHovered ? 0.8 : 0.6) : 0.1};
                                   transform: scale({isSearchMatch ? 1 : 0.8});
                                   mask-image: url({logoSrc}); mask-size: contain; mask-repeat: no-repeat; mask-position: center;
                                   -webkit-mask-image: url({logoSrc}); -webkit-mask-size: contain; -webkit-mask-repeat: no-repeat; -webkit-mask-position: center;"
                        ></div>
                    </div>
                </foreignObject>
            </g>
        {/each}
    </svg>

    {#if activeRoaster}
        <div
            class="z-50 fixed transition-all duration-200 ease-out pointer-events-none"
            style="left: {tooltipPos.x}px; top: {tooltipPos.y}px; transform: translate(-50%, -110%);"
            transition:fade={{ duration: 150 }}
        >
            <div
                class="bg-white/98 dark:bg-slate-800/98 shadow-2xl backdrop-blur-xl p-4 border border-slate-200 dark:border-slate-700 rounded-lg w-72 pointer-events-auto"
                onclick={(e) => e.stopPropagation()}
                role="tooltip"
            >
                {#if selectedRoaster}
                    <button
                        class="top-2 right-2 absolute hover:bg-slate-100 dark:hover:bg-slate-700 p-1 rounded-full text-slate-400 transition-colors"
                        onclick={closeTooltip}
                    >
                        <X size={16} />
                    </button>
                {/if}

                <div class="flex items-center gap-4 mb-5">
                    <div class="flex-1 min-w-0">
                        <h3
                            class="font-bold text-slate-900 dark:text-white text-lg line-clamp-2 leading-tight"
                        >
                            {activeRoaster.name}
                        </h3>
                        {#if activeRoaster.location}
                            <p
                                class="flex items-center gap-1 mt-1 text-slate-500 dark:text-slate-400 text-sm"
                            >
                                <MapPin
                                    size={14}
                                    class="text-orange-500 shrink-0"
                                />
                                <span class="truncate"
                                    >{activeRoaster.location}</span
                                >
                            </p>
                        {/if}
                    </div>
                </div>

                <div class="gap-2.5 grid grid-cols-1">
                    <Button
                        class="px-4 w-full h-10 text-sm"
                        variant="outline"
                        href={`/search?roaster=${encodeURIComponent(activeRoaster.name)}`}
                    >
                        <Coffee class="mr-2 w-4 h-4" />
                        Explore {activeRoaster.current_beans_count.toLocaleString()}
                        Bean{activeRoaster.current_beans_count === 1 ? "" : "s"}
                    </Button>

                    {#if activeRoaster.website}
                        <Button
                            variant="outline"
                            class="px-4 w-full h-10 text-sm"
                            target="_blank"
                            href={addUtmParams(activeRoaster.website, {
                                source: "kissaten.app",
                                medium: "referral",
                                campaign: "roaster_sticker_wall",
                            })}
                        >
                            <Globe size={16} class="mr-2 text-cyan-500" />
                            Visit Website
                            <ExternalLink
                                size={14}
                                class="opacity-30 ml-auto"
                            />
                        </Button>
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    svg {
        user-select: none;
    }
    g {
        pointer-events: all;
    }
</style>
