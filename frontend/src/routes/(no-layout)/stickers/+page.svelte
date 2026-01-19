<script lang="ts">
    import "../../../app.css";
    import "../../../placeholder.css";
    import { onMount } from "svelte";
    import { writable } from "svelte/store";
    import { ModeWatcher, toggleMode, mode } from "mode-watcher";
    import SunIcon from "lucide-svelte/icons/sun";
    import MoonIcon from "lucide-svelte/icons/moon";
    import * as Card from "$lib/components/ui/card/index.js";
    import { Button } from "$lib/components/ui/button/index.js";
    import { Label } from "$lib/components/ui/label/index.js";
    import { Separator } from "$lib/components/ui/separator/index.js";
    import Badge from "$lib/components/ui/badge/badge.svelte";
    import Logo from "$lib/static/logo.svg?raw";
    import "@fontsource/knewave";
    import "@fontsource-variable/quicksand";
    import "@fontsource-variable/cabin";
    import "iconify-icon";
    import Dropzone from "svelte-file-dropzone";
    import {
        LucideImage,
        LucideUpload,
        LucideDownload,
        LucideSettings2,
        LucideMaximize,
        LucideMinus,
        LucidePlus,
        LucideSparkles,
        LucideAnvil,
        LucideArrowLeft,
        LucideContrast,
        LucideCircle,
        LucideSquare,
        LucideSpline,
        LucideRectangleHorizontal,
    } from "lucide-svelte";
    import { Switch } from "$lib/components/ui/switch/index.js";

    let canvas = $state<HTMLCanvasElement | null>(null);
    let thickness = $state(25);
    let padding = $state(20);
    let scale = $state(1.0);
    let baseWidth = $state(500);
    let imageUrl = $state<string | null>(null);
    let isProcessing = $state(false);
    let imgElement = $state<HTMLImageElement | null>(null);
    let fileType = $state<string>("");
    let fileName = $state<string>("");
    let invertColors = $state(false);
    let shapeMode = $state<"contour" | "circle" | "square" | "rectangle">(
        "contour",
    );
    let cornerRadius = $state(0);

    // Handle re-rendering when parameters change
    $effect(() => {
        const _t = thickness;
        const _p = padding;
        const _s = scale;
        const _bw = baseWidth;
        const _img = imgElement;
        const _i = invertColors;
        const _sm = shapeMode;
        const _cr = cornerRadius;

        if (_img && canvas) {
            render();
        }
    });

    function handleFilesSelect(e: any) {
        const { acceptedFiles } = e.detail;
        if (acceptedFiles.length > 0) {
            const file = acceptedFiles[0];
            fileType = file.type;
            fileName = file.name;
            if (imageUrl) URL.revokeObjectURL(imageUrl);
            imageUrl = URL.createObjectURL(file);
            loadImage();
        }
    }

    async function loadImage() {
        if (!imageUrl) return;
        isProcessing = true;
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.src = imageUrl;
        await new Promise((resolve) => {
            // @ts-ignore
            img.onload = () => {
                imgElement = img;
                baseWidth = 500; // Efficient default for initial preview
                resolve(null);
            };
        });
        isProcessing = false;
    }

    function render() {
        if (!imgElement || !canvas) return;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (!ctx) return;

        const aspectRatio = imgElement.naturalHeight / imgElement.naturalWidth;
        const targetW = baseWidth * scale;
        const targetH = targetW * aspectRatio;

        // Resolution Agnotsic Scaling (relative to 1000px reference)
        const t = (thickness * baseWidth) / 1000;
        const p = (padding * baseWidth) / 1000;

        if (shapeMode === "contour" || shapeMode === "rectangle") {
            canvas.width = Math.ceil(targetW + (t + p) * 2);
            canvas.height = Math.ceil(targetH + (t + p) * 2);
        } else {
            const size = Math.max(targetW, targetH) + (t + p) * 2;
            canvas.width = size;
            canvas.height = size;
        }

        const w = canvas.width;
        const h = canvas.height;
        const imgX = (w - targetW) / 2;
        const imgY = (h - targetH) / 2;

        if (shapeMode === "contour") {
            const buffer = document.createElement("canvas");
            buffer.width = w;
            buffer.height = h;
            const bctx = buffer.getContext("2d", { willReadFrequently: true })!;
            bctx.drawImage(imgElement, imgX, imgY, targetW, targetH);
            bctx.globalCompositeOperation = "source-in";
            bctx.fillStyle = "black";
            bctx.fillRect(0, 0, w, h);

            const bufData = bctx.getImageData(0, 0, w, h);
            const pixels = bufData.data;
            const isSolid = new Uint8Array(w * h);
            const visited = new Uint8Array(w * h);

            const stack: [number, number][] = [[0, 0]];
            visited[0] = 1;
            while (stack.length > 0) {
                const [cx, cy] = stack.pop()!;
                const neighbors = [
                    [cx + 1, cy],
                    [cx - 1, cy],
                    [cx, cy + 1],
                    [cx, cy - 1],
                ];
                for (const [nx, ny] of neighbors) {
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        const idx = ny * w + nx;
                        if (visited[idx] === 0 && pixels[idx * 4 + 3] < 128) {
                            visited[idx] = 1;
                            stack.push([nx, ny]);
                        }
                    }
                }
            }

            for (let i = 0; i < w * h; i++) {
                if (visited[i] === 0) isSolid[i] = 1;
            }

            const g = new Float32Array(w * h);
            for (let x = 0; x < w; x++) {
                let dist = 1e9;
                for (let y = 0; y < h; y++) {
                    if (isSolid[y * w + x]) dist = 0;
                    else dist++;
                    g[y * w + x] = dist * dist;
                }
                dist = 1e9;
                for (let y = h - 1; y >= 0; y--) {
                    if (isSolid[y * w + x]) dist = 0;
                    else dist++;
                    g[y * w + x] = Math.min(g[y * w + x], dist * dist);
                }
            }

            const distSq = new Float32Array(w * h);
            const windowSize = Math.ceil(t) + 1;
            for (let y = 0; y < h; y++) {
                for (let x = 0; x < w; x++) {
                    let minD = 1e9;
                    const startX = Math.max(0, x - windowSize);
                    const endX = Math.min(w - 1, x + windowSize);
                    for (let ix = startX; ix <= endX; ix++) {
                        const dx = x - ix;
                        const d = g[y * w + ix] + dx * dx;
                        if (d < minD) minD = d;
                    }
                    distSq[y * w + x] = minD;
                }
            }

            const outData = ctx.createImageData(w, h);
            const outPixels = outData.data;
            const tSq = t * t;
            for (let i = 0; i < w * h; i++) {
                if (distSq[i] <= tSq) {
                    outPixels[i * 4] = 255;
                    outPixels[i * 4 + 1] = 255;
                    outPixels[i * 4 + 2] = 255;
                    outPixels[i * 4 + 3] = 255;
                } else {
                    outPixels[i * 4 + 3] = 0;
                }
            }

            ctx.clearRect(0, 0, w, h);
            ctx.putImageData(outData, 0, 0);
        } else {
            ctx.clearRect(0, 0, w, h);
            ctx.fillStyle = "white";
            if (shapeMode === "circle") {
                const radius = Math.max(targetW, targetH) / 2 + t;
                ctx.beginPath();
                ctx.arc(w / 2, h / 2, radius, 0, Math.PI * 2);
                ctx.fill();
            } else if (shapeMode === "square") {
                const side = Math.max(targetW, targetH) + t * 2;
                ctx.fillRect((w - side) / 2, (h - side) / 2, side, side);
            } else if (shapeMode === "rectangle") {
                const rectW = targetW + t * 2;
                const rectH = targetH + t * 2;
                const rectX = (w - rectW) / 2;
                const rectY = (h - rectH) / 2;
                const r = (cornerRadius * baseWidth) / 1000;

                if (r > 0) {
                    ctx.beginPath();
                    ctx.moveTo(rectX + r, rectY);
                    ctx.lineTo(rectX + rectW - r, rectY);
                    ctx.arcTo(
                        rectX + rectW,
                        rectY,
                        rectX + rectW,
                        rectY + r,
                        r,
                    );
                    ctx.lineTo(rectX + rectW, rectY + rectH - r);
                    ctx.arcTo(
                        rectX + rectW,
                        rectY + rectH,
                        rectX + rectW - r,
                        rectY + rectH,
                        r,
                    );
                    ctx.lineTo(rectX + r, rectY + rectH);
                    ctx.arcTo(
                        rectX,
                        rectY + rectH,
                        rectX,
                        rectY + rectH - r,
                        r,
                    );
                    ctx.lineTo(rectX, rectY + r);
                    ctx.arcTo(rectX, rectY, rectX + r, rectY, r);
                    ctx.closePath();
                    ctx.fill();
                } else {
                    ctx.fillRect(rectX, rectY, rectW, rectH);
                }
            }
        }

        if (invertColors) {
            ctx.filter = "invert(1)";
        }
        ctx.drawImage(imgElement, imgX, imgY, targetW, targetH);
        ctx.filter = "none";
    }

    async function downloadSticker() {
        if (!canvas) return;
        const suggestedName = fileName
            ? `${fileName.split(".")[0]}_sticker.png`
            : `${Date.now()}_sticker.png`;

        // Modern "Save As" using File System Access API
        if (typeof window !== "undefined" && "showSaveFilePicker" in window) {
            try {
                // @ts-ignore
                const handle = await window.showSaveFilePicker({
                    suggestedName,
                    types: [
                        {
                            description: "PNG Image",
                            accept: { "image/png": [".png"] },
                        },
                    ],
                });

                const blob = await new Promise<Blob | null>((resolve) =>
                    canvas!.toBlob(resolve, "image/png"),
                );
                if (!blob) return;

                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                return;
            } catch (err: any) {
                // If user cancels, we do nothing. Otherwise log and fallback
                if (err.name === "AbortError") return;
                console.error("Save As failed, using fallback:", err);
            }
        }

        // Fallback to standard automatic download
        const link = document.createElement("a");
        link.download = suggestedName;
        link.href = canvas.toDataURL("image/png");
        link.click();
    }
</script>

<svelte:head>
    <title>Sticker Studio | Kissaten</title>
    {#if mode.current == "dark"}
        <meta name="theme-color" content="#0a0b1f" />
    {:else}
        <meta name="theme-color" content="#faf6f3" />
    {/if}
</svelte:head>

<ModeWatcher />

<div
    class="min-h-screen font-sans"
    style="background-color: var(--background); color: var(--foreground);"
>
    <!-- Header -->
    <header
        class="top-0 z-50 sticky bg-background/95 supports-[backdrop-filter]:bg-background/80 backdrop-blur border-b w-full"
    >
        <div
            class="flex justify-between items-center h-14 container mx-auto px-4"
        >
            <div class="flex items-center gap-4">
                <Button
                    variant="ghost"
                    size="icon"
                    href="/"
                    class="rounded-full"
                >
                    <LucideArrowLeft class="w-5 h-5" />
                </Button>
                <a class="flex items-center space-x-2" href="/">
                    <h1 class="flex items-center gap-2 font-bold text-xl">
                        <span class="w-8">{@html Logo}</span>
                        <span>Kissaten</span>
                    </h1>
                </a>
            </div>

            <div class="flex items-center space-x-2">
                <Button onclick={toggleMode} variant="outline" size="icon">
                    <SunIcon
                        class="w-[1.2rem] h-[1.2rem] rotate-0 dark:-rotate-90 scale-100 dark:scale-0 transition-all"
                    />
                    <MoonIcon
                        class="absolute w-[1.2rem] h-[1.2rem] rotate-90 dark:rotate-0 scale-0 dark:scale-100 transition-all"
                    />
                    <span class="sr-only">Toggle theme</span>
                </Button>
            </div>
        </div>
    </header>

    <div class="container mx-auto px-4 py-8 lg:py-12">
        <!-- Main Title Section -->
        <header class="mb-12 flex flex-col items-center text-center space-y-4">
            <div
                class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-black uppercase tracking-widest shadow-sm"
            >
                <LucideSparkles class="w-3.5 h-3.5" />
                Experimental Tool
            </div>
            <h1
                class="text-6xl md:text-7xl lg:text-8xl tracking-tighter"
                style="font-family: var(--font-fun); color: var(--primary);"
            >
                Sticker <span class="text-foreground">Studio</span>
            </h1>
            <p
                class="text-muted-foreground text-lg max-w-2xl font-medium tracking-tight"
            >
                Professional Euclidean-grade contour generator for vinyl
                stickers.
            </p>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <!-- sidebar / controls -->
            <div class="lg:col-span-4 space-y-6">
                <!-- Upload Card -->
                <Card.Root
                    class="overflow-hidden border-2 border-primary/10 shadow-xl bg-card/50 backdrop-blur-md rounded-[2rem]"
                >
                    <Card.Content class="p-0">
                        <Dropzone
                            on:drop={handleFilesSelect}
                            containerClasses="!bg-transparent !border-0 !p-8 !m-0 hover:!bg-primary/5 transition-colors cursor-pointer group"
                        >
                            <div
                                class="flex flex-col items-center justify-center space-y-4 text-center py-6"
                            >
                                <div
                                    class="w-20 h-20 rounded-[2rem] bg-primary/10 flex items-center justify-center group-hover:scale-110 transition-transform duration-500 shadow-inner"
                                >
                                    <LucideUpload
                                        class="w-8 h-8 text-primary"
                                    />
                                </div>
                                <div class="space-y-1">
                                    <p
                                        class="text-sm font-black uppercase tracking-widest"
                                    >
                                        {imageUrl
                                            ? "Swap Artwork"
                                            : "Drop Image Here"}
                                    </p>
                                    <p
                                        class="text-[10px] text-muted-foreground uppercase font-medium"
                                    >
                                        SVG, PNG, WEBP, or JPG
                                    </p>
                                </div>
                            </div>
                        </Dropzone>
                    </Card.Content>
                </Card.Root>

                <!-- Controls Card -->
                <Card.Root
                    class="border-2 border-primary/10 shadow-xl bg-card rounded-[2rem]"
                >
                    <Card.Header class="pb-2">
                        <Card.Title
                            class="flex items-center gap-2 text-sm uppercase tracking-[0.2em] font-black text-primary"
                        >
                            <LucideSettings2 class="w-4 h-4" />
                            Geometry Engine
                        </Card.Title>
                    </Card.Header>
                    <Card.Content class="space-y-8 py-6">
                        <!-- Border Thickness -->
                        <div class="space-y-4">
                            <div class="flex justify-between items-end">
                                <Label
                                    class="text-xs uppercase tracking-widest font-black opacity-80"
                                    >Border Width</Label
                                >
                                <Badge
                                    variant="secondary"
                                    class="font-black font-mono text-[10px]"
                                    >{thickness}px</Badge
                                >
                            </div>
                            <div class="relative h-6 flex items-center group">
                                <input
                                    type="range"
                                    min="0"
                                    max="250"
                                    step="1"
                                    bind:value={thickness}
                                    class="slider-kissaten w-full"
                                />
                            </div>
                        </div>

                        <!-- Base Shape -->
                        <div class="space-y-4">
                            <Label
                                class="text-xs uppercase tracking-widest font-black opacity-80"
                                >Contour Mode</Label
                            >
                            <div class="grid grid-cols-4 gap-2">
                                <Button
                                    variant={shapeMode === "contour"
                                        ? "default"
                                        : "outline"}
                                    class="h-12 rounded-2xl flex flex-col items-center justify-center gap-1 transition-all"
                                    onclick={() => (shapeMode = "contour")}
                                >
                                    <LucideSpline class="w-4 h-4" />
                                    <span
                                        class="text-[9px] font-black uppercase tracking-widest"
                                        >EDT</span
                                    >
                                </Button>
                                <Button
                                    variant={shapeMode === "circle"
                                        ? "default"
                                        : "outline"}
                                    class="h-12 rounded-2xl flex flex-col items-center justify-center gap-1 transition-all"
                                    onclick={() => (shapeMode = "circle")}
                                >
                                    <LucideCircle class="w-4 h-4" />
                                    <span
                                        class="text-[9px] font-black uppercase tracking-widest"
                                        >Circle</span
                                    >
                                </Button>
                                <Button
                                    variant={shapeMode === "square"
                                        ? "default"
                                        : "outline"}
                                    class="h-12 rounded-2xl flex flex-col items-center justify-center gap-1 transition-all"
                                    onclick={() => (shapeMode = "square")}
                                >
                                    <LucideSquare class="w-4 h-4" />
                                    <span
                                        class="text-[9px] font-black uppercase tracking-widest"
                                        >Square</span
                                    >
                                </Button>
                                <Button
                                    variant={shapeMode === "rectangle"
                                        ? "default"
                                        : "outline"}
                                    class="h-12 rounded-2xl flex flex-col items-center justify-center gap-1 transition-all"
                                    onclick={() => (shapeMode = "rectangle")}
                                >
                                    <LucideRectangleHorizontal
                                        class="w-4 h-4"
                                    />
                                    <span
                                        class="text-[9px] font-black uppercase tracking-widest"
                                        >Rect</span
                                    >
                                </Button>
                            </div>
                        </div>

                        {#if shapeMode === "rectangle"}
                            <!-- Corner Radius -->
                            <div class="space-y-4">
                                <div class="flex justify-between items-end">
                                    <Label
                                        class="text-xs uppercase tracking-widest font-black opacity-80"
                                        >Corner Radius</Label
                                    >
                                    <Badge
                                        variant="outline"
                                        class="font-black font-mono text-[10px] border-primary/20"
                                        >{cornerRadius}px</Badge
                                    >
                                </div>
                                <div
                                    class="relative h-6 flex items-center group"
                                >
                                    <input
                                        type="range"
                                        min="0"
                                        max="200"
                                        step="1"
                                        bind:value={cornerRadius}
                                        class="slider-kissaten w-full"
                                    />
                                </div>
                            </div>
                        {/if}

                        <!-- Canvas Bleed -->
                        <div class="space-y-4">
                            <div class="flex justify-between items-end">
                                <Label
                                    class="text-xs uppercase tracking-widest font-black opacity-80"
                                    >Safety Padding</Label
                                >
                                <Badge
                                    variant="outline"
                                    class="font-black font-mono text-[10px] border-primary/20"
                                    >{padding}px</Badge
                                >
                            </div>
                            <div class="relative h-6 flex items-center group">
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    step="1"
                                    bind:value={padding}
                                    class="slider-kissaten w-full"
                                />
                            </div>
                        </div>

                        <Separator class="bg-primary/5" />

                        <div class="space-y-4">
                            <div class="flex justify-between items-end">
                                <Label
                                    class="text-xs uppercase tracking-widest font-black opacity-80"
                                    >Base Resolution</Label
                                >
                                <Badge
                                    variant="secondary"
                                    class="font-black font-mono text-[10px]"
                                    >{baseWidth}px</Badge
                                >
                            </div>
                            <div class="relative h-6 flex items-center group">
                                <input
                                    type="range"
                                    min="400"
                                    max="4000"
                                    step="50"
                                    bind:value={baseWidth}
                                    class="slider-kissaten w-full"
                                />
                            </div>
                        </div>

                        <div class="space-y-4">
                            <div class="flex justify-between items-end">
                                <Label
                                    class="text-xs uppercase tracking-widest font-black opacity-80"
                                    >Internal Scale</Label
                                >
                                <Badge
                                    variant="outline"
                                    class="font-black font-mono text-[10px] border-primary/20"
                                    >x{scale.toFixed(2)}</Badge
                                >
                            </div>
                            <div class="relative h-6 flex items-center group">
                                <input
                                    type="range"
                                    min="0.1"
                                    max="2.0"
                                    step="0.01"
                                    bind:value={scale}
                                    class="slider-kissaten w-full"
                                />
                            </div>
                        </div>

                        <Separator class="bg-primary/5" />

                        <div class="space-y-4">
                            <div class="flex items-center justify-between">
                                <div class="space-y-1">
                                    <Label
                                        class="text-xs uppercase tracking-widest font-black opacity-80 flex items-center gap-2"
                                    >
                                        <LucideContrast class="w-3.5 h-3.5" />
                                        Invert Artwork
                                    </Label>
                                    <p
                                        class="text-[9px] text-muted-foreground uppercase font-medium"
                                    >
                                        Keep transparency intact
                                    </p>
                                </div>
                                <Switch bind:checked={invertColors} />
                            </div>
                        </div>
                    </Card.Content>
                    <Card.Footer class="pt-2">
                        {#if imageUrl}
                            <Button
                                onclick={downloadSticker}
                                class="w-full h-fit bg-primary hover:bg-primary/90 text-primary-foreground font-black uppercase tracking-[0.2em] rounded-2xl shadow-lg hover:shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all gap-3 overflow-hidden group"
                            >
                                <LucideDownload class="w-5 h-5" />
                                Export
                            </Button>
                        {/if}
                    </Card.Footer>
                </Card.Root>
            </div>

            <!-- Preview Viewport -->
            <div class="lg:col-span-8 sticky top-8">
                <Card.Root
                    class="border-2 border-primary/10 shadow-2xl bg-white rounded-[3rem] overflow-hidden min-h-[700px] flex flex-col relative group"
                >
                    <!-- Top Toolbar -->
                    <div
                        class="absolute top-8 left-8 right-8 flex justify-between items-center z-10 pointer-events-none"
                    >
                        <div
                            class="flex gap-2 p-1.5 rounded-full bg-slate-100/80 backdrop-blur-md pointer-events-auto shadow-sm"
                        >
                            <div class="w-3 h-3 rounded-full bg-red-400"></div>
                            <div
                                class="w-3 h-3 rounded-full bg-yellow-400"
                            ></div>
                            <div
                                class="w-3 h-3 rounded-full bg-green-400"
                            ></div>
                        </div>

                        {#if imageUrl}
                            <div
                                class="p-2 rounded-2xl bg-white/80 backdrop-blur-md shadow-lg border border-primary/5 pointer-events-auto flex items-center gap-4"
                            >
                                <div class="flex flex-col items-end px-2">
                                    <span
                                        class="text-[9px] font-black uppercase text-muted-foreground tracking-widest"
                                        >Est. Die Cut</span
                                    >
                                    <span
                                        class="text-[11px] font-mono font-bold text-primary"
                                        >{thickness * 2}mm Shell</span
                                    >
                                </div>
                                <Button
                                    size="icon"
                                    variant="ghost"
                                    class="rounded-xl"
                                    onclick={downloadSticker}
                                >
                                    <LucideMaximize class="w-4 h-4" />
                                </Button>
                            </div>
                        {/if}
                    </div>

                    <Card.Content
                        class="flex-1 flex items-center justify-center p-12 relative overflow-hidden bg-[radial-gradient(var(--color-border)_1px,transparent_1px)] [background-size:40px_40px]"
                    >
                        {#if !imageUrl}
                            <div
                                class="text-center space-y-6 max-w-sm animate-in fade-in zoom-in duration-700"
                            >
                                <div class="relative inline-block">
                                    <div
                                        class="absolute inset-0 bg-primary/20 blur-3xl rounded-full"
                                    ></div>
                                    <div
                                        class="relative w-32 h-32 rounded-[2.5rem] bg-card border-2 border-primary/20 flex items-center justify-center shadow-xl"
                                    >
                                        <LucideAnvil
                                            class="w-12 h-12 text-primary opacity-30 animate-spin-slow"
                                        />
                                    </div>
                                </div>
                                <div class="space-y-2">
                                    <h3
                                        class="text-xl font-bold tracking-tight"
                                    >
                                        Studio Ready
                                    </h3>
                                    <p
                                        class="text-sm text-muted-foreground leading-relaxed"
                                    >
                                        Upload or drag a logo into the left
                                        panel to begin your vinyl simulation.
                                    </p>
                                </div>
                            </div>
                        {:else}
                            <div
                                class="relative flex items-center justify-center w-full h-full animate-in fade-in duration-500"
                            >
                                {#if isProcessing}
                                    <div
                                        class="absolute inset-0 flex items-center justify-center bg-white/60 backdrop-blur-md z-20"
                                    >
                                        <div
                                            class="flex flex-col items-center gap-4"
                                        >
                                            <div
                                                class="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin"
                                            ></div>
                                            <span
                                                class="text-xs font-black uppercase tracking-widest text-primary animate-pulse"
                                                >Calculating Distance Field...</span
                                            >
                                        </div>
                                    </div>
                                {/if}

                                <div
                                    class="max-w-full max-h-[70vh] overflow-auto no-scrollbar flex items-center justify-center p-8"
                                >
                                    <canvas
                                        bind:this={canvas}
                                        class="max-w-full h-auto drop-shadow-[0_60px_100px_rgba(0,0,0,0.15)] transition-all duration-300 hover:scale-[1.01] active:scale-[0.99] cursor-grab active:cursor-grabbing"
                                    ></canvas>
                                </div>
                            </div>
                        {/if}
                    </Card.Content>

                    <!-- Footer Indicators -->
                    <div class="p-8 flex justify-between items-end">
                        <div class="space-y-1">
                            <p
                                class="text-[9px] font-black uppercase text-primary tracking-widest"
                            >
                                Kissaten Sticker Engine v2.0
                            </p>
                            <p
                                class="text-[10px] text-muted-foreground italic tracking-tight"
                            >
                                Powered by Euclidean Distance Transform
                            </p>
                        </div>
                        {#if imageUrl}
                            <div class="flex gap-2">
                                <Badge
                                    variant="outline"
                                    class="text-[9px] font-bold py-0"
                                    >{fileType
                                        .split("/")[1]
                                        .toUpperCase()}</Badge
                                >
                                <Badge
                                    variant="outline"
                                    class="text-[9px] font-bold py-0"
                                    >{canvas?.width} x {canvas?.height}</Badge
                                >
                            </div>
                        {/if}
                    </div>
                </Card.Root>
            </div>
        </div>
    </div>
</div>

<style>
    :global(body) {
        margin: 0;
        overflow-x: hidden;
    }

    .no-scrollbar::-webkit-scrollbar {
        display: none;
    }

    @keyframes spin-slow {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
    .animate-spin-slow {
        animation: spin-slow 12s linear infinite;
    }

    /* Custom Range Slider for Kissaten Theme */
    .slider-kissaten {
        -webkit-appearance: none;
        width: 100%;
        background: transparent;
        cursor: pointer;
    }

    .slider-kissaten:focus {
        outline: none;
    }

    .slider-kissaten::-webkit-slider-runnable-track {
        width: 100%;
        height: 6px;
        background: var(--secondary);
        border-radius: 99px;
        transition: background 0.2s;
    }

    .slider-kissaten:hover::-webkit-slider-runnable-track {
        background: oklch(0.85 0.1 300 / 0.2);
    }

    .slider-kissaten::-webkit-slider-thumb {
        height: 22px;
        width: 22px;
        border-radius: 50%;
        background: #ffffff;
        border: 4px solid var(--primary);
        box-shadow: 0 4px 12px rgba(var(--primary), 0.2);
        -webkit-appearance: none;
        margin-top: -8px;
        transition:
            transform 0.2s,
            box-shadow 0.2s;
    }

    .slider-kissaten:active::-webkit-slider-thumb {
        transform: scale(1.2);
        box-shadow: 0 0 20px oklch(0.7 0.15 65 / 0.4);
    }

    /* Global custom styles to match app.css feel */
    :global(.lucide) {
        stroke-width: 2.5px;
    }
</style>
