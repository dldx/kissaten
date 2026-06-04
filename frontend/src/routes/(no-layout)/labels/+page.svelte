<script lang="ts">
	import "../../../app.css";
	import { onMount } from "svelte";
	import { type CoffeeBean, api } from "$lib/api";
	import { cn } from "$lib/utils";
	import { type LabelTemplate, PRESET_TEMPLATES } from "$lib/types/labels";
	import CoffeeBeanTile from "$lib/components/tasting/CoffeeBeanTile.svelte";
	import BeanSearchCombobox from "$lib/components/tasting/BeanSearchCombobox.svelte";
	import { Button } from "$lib/components/ui/button";
	import * as Card from "$lib/components/ui/card";
	import { Label } from "$lib/components/ui/label";
	import { Input } from "$lib/components/ui/input";
	import * as Select from "$lib/components/ui/select/index.js";
	import { Printer, Settings2, Download, Search, LayoutGrid, Layout, Plus, Save, Trash2, ArrowLeft, X, ChevronDown, ChevronRight } from "lucide-svelte";
	import Logo from "$lib/static/logo.svg?raw";

	let { data } = $props();

	const MM_TO_PX = 3.78; // 96 DPI approximation for layout

	// Settings
	let currentTemplate = $state<LabelTemplate>({...PRESET_TEMPLATES[1]}); // Default A4 3x8
	let selectedBeans = $state<(CoffeeBean | null)[]>([]);
	let beanNotes = $state<string[]>([]);
	let userTemplates = $state<LabelTemplate[]>([]);
	interface LabelSettings {
		slim: boolean;
		showTastingNotes: boolean;
		showOrigin: boolean;
		showTags: boolean;
		showName: boolean;
		showFarm: boolean;
		showRegion: boolean;
		showVarietal: boolean;
		showProcess: boolean;
		showRoastProfile: boolean;
		showRoastLevel: boolean;
		showElevation: boolean;
		wrapName: boolean;
		maxTastingNotes: number;
	}

	let settings = $state<LabelSettings>({
		slim: false,
		showTastingNotes: true,
		showOrigin: true,
		showTags: true,
		showName: true,
		showFarm: true,
		showRegion: true,
		showVarietal: true,
		showProcess: true,
		showRoastProfile: true,
		showRoastLevel: true,
		showElevation: true,
		wrapName: false,
		maxTastingNotes: 10
	});

	// Persistence
	onMount(() => {
		// Load User Templates
		const savedTemplates = localStorage.getItem("kissaten-user-label-templates");
		if (savedTemplates) {
			try {
				userTemplates = JSON.parse(savedTemplates);
			} catch (e) {
				console.error("Failed to load user templates", e);
			}
		}

		// Load Session State
		const savedState = localStorage.getItem("kissaten-label-studio-state");
		if (savedState) {
			try {
				const state = JSON.parse(savedState);
				if (state.settings) settings = { ...settings, ...state.settings };
				if (state.currentTemplate) currentTemplate = state.currentTemplate;
				if (state.selectedBeans) selectedBeans = state.selectedBeans;
				if (state.beanNotes) beanNotes = state.beanNotes;
			} catch (e) {
				console.error("Failed to load session state", e);
			}
		}
	});

	// Auto-save session state
	$effect(() => {
		const state = {
			settings,
			currentTemplate,
			selectedBeans,
			beanNotes
		};
		localStorage.setItem("kissaten-label-studio-state", JSON.stringify(state));
	});

	function saveCurrentAsTemplate() {
		const name = prompt("Enter a name for this template", currentTemplate.name);
		if (!name) return;

		const newTemplate = {
			...currentTemplate,
			id: `user-${Date.now()}`,
			name
		};
		userTemplates = [...userTemplates, newTemplate];
		localStorage.setItem("kissaten-user-label-templates", JSON.stringify(userTemplates));
		currentTemplate = newTemplate;
	}

	function updateCurrentTemplate() {
		if (!currentTemplate.id.startsWith('user-')) return;

		userTemplates = userTemplates.map(t =>
			t.id === currentTemplate.id ? { ...currentTemplate } : t
		);
		localStorage.setItem("kissaten-user-label-templates", JSON.stringify(userTemplates));
	}

	function deleteTemplate(id: string) {
		if (confirm("Are you sure you want to delete this template?")) {
			userTemplates = userTemplates.filter(t => t.id !== id);
			localStorage.setItem("kissaten-user-label-templates", JSON.stringify(userTemplates));
			currentTemplate = { ...PRESET_TEMPLATES[1] };
		}
	}

	// Bean Selection State
	let currentBeanPath = $state<string | null>(null);
	let currentBeanData = $state<CoffeeBean | null>(null);
	let showDimensions = $state(false);
	let isSupported = $state(true);

	// Pre-process beans based on visibility settings to avoid logic bloat in the Tile component
	const processedBeans = $derived(selectedBeans.map((bean, i) => {
		if (!bean) return null;

		return {
			...bean,
			_customNote: beanNotes[i] || "", // Attach the note to the derived object
			name: settings.showName ? bean.name : "",
			origins: bean.origins?.map(o => {
				const filteredOrigin = { ...o };
				if (!settings.showFarm) filteredOrigin.farm = "";
				if (!settings.showRegion) filteredOrigin.region = "";
				if (!settings.showVarietal) filteredOrigin.variety_canonical = [];
				if (!settings.showProcess) filteredOrigin.process = "";
				if (!settings.showElevation) {
					filteredOrigin.elevation_min = undefined as any;
					filteredOrigin.elevation_max = undefined as any;
				}
				return filteredOrigin;
			}),
			tasting_notes: settings.showTastingNotes
				? (bean.tasting_notes?.slice(0, settings.maxTastingNotes) || [])
				: [],
			roast_level: settings.showRoastLevel ? bean.roast_level : "",
			roast_profile: settings.showRoastProfile ? bean.roast_profile : "",
		};
	}));

	// Print Image state
	let printImage = $state<string | null>(null);

	// Canvas for preview
	let canvas = $state<HTMLCanvasElement | null>(null);
	let previewContainer = $state<HTMLDivElement | null>(null);
	let labelRefs = $state<HTMLDivElement[]>([]);

	// Derived metrics for dimension verification
	let calcWidth = $derived(currentTemplate.marginLeft + currentTemplate.marginRight + (currentTemplate.cols * currentTemplate.labelWidth) + ((currentTemplate.cols - 1) * currentTemplate.colGap));
	let calcHeight = $derived(currentTemplate.marginTop + currentTemplate.marginBottom + (currentTemplate.rows * currentTemplate.labelHeight) + ((currentTemplate.rows - 1) * currentTemplate.rowGap));
	let widthDiff = $derived(Math.abs(calcWidth - (currentTemplate.width || 0)));
	let heightDiff = $derived(Math.abs(calcHeight - (currentTemplate.height || 0)));

	$effect(() => {
		const total = currentTemplate.rows * currentTemplate.cols;
		if (selectedBeans.length !== total) {
			const newBeanArr = new Array(total).fill(null);
			const newNoteArr = new Array(total).fill("");
			for (let i = 0; i < Math.min(selectedBeans.length, total); i++) {
				newBeanArr[i] = selectedBeans[i];
				newNoteArr[i] = beanNotes[i] || "";
			}
			selectedBeans = newBeanArr;
			beanNotes = newNoteArr;
		}
		// DO NOT reset labelRefs here - it would clear bind:this references
		// labelRefs is sized via the each block and bind:this assignments
	});

	function assignBean(bean: CoffeeBean, index: number) {
		selectedBeans[index] = bean;
		selectedBeans = [...selectedBeans];
		// Force labelRefs to be perceived as changed even if bind:this hasn't finished yet
		// The effect will run now, skip the missing ref, then run again once bind:this completes
		labelRefs = [...labelRefs];
	}

	function fillAll() {
		if (currentBeanData) {
			const bean = currentBeanData as CoffeeBean;
			selectedBeans = selectedBeans.map(() => ({...bean})); // Create new refs
		}
	}

	function clearAll() {
		selectedBeans = selectedBeans.map(() => null);
		beanNotes = beanNotes.map(() => "");
	}

	function handlePrint() {
		if (canvas) {
			// 1. Render without guides for the print snapshot
			renderCanvas({ skipGuides: true });

			printImage = canvas.toDataURL('image/png', 1.0);

			// 2. Restore guides for the on-screen preview
			renderCanvas({ skipGuides: false });

			// Small delay to ensure the image is swapped in the DOM
			setTimeout(() => {
				window.print();
			}, 50);
		}
	}

	// HTML-in-Canvas Rendering Logic
	function renderCanvas(options = { skipGuides: false }) {
		if (!canvas) {
			console.log('[LabelStudio] renderCanvas: No canvas element');
			return;
		}
		const ctx = canvas.getContext("2d");
		if (!ctx) {
			console.log('[LabelStudio] renderCanvas: No 2D context');
			return;
		}

		// @ts-ignore - Flag check for experimental API
		if (typeof ctx.drawElementImage !== "function") {
			if (isSupported) console.warn("[LabelStudio] drawElementImage NOT supported");
			isSupported = false;
			return;
		}
		isSupported = true;

		console.log('[LabelStudio] Starting render...', {
			template: currentTemplate?.name,
			labelsCount: labelRefs.filter(Boolean).length,
			skipGuides: options.skipGuides
		});

		const dpr = window.devicePixelRatio || 1;
		const width = Math.round(currentTemplate.width * MM_TO_PX);
		const height = Math.round(currentTemplate.height * MM_TO_PX);

		const bufW = Math.round(width * dpr);
		const bufH = Math.round(height * dpr);

		if (canvas.width !== bufW || canvas.height !== bufH) {
			console.log(`[LabelStudio] Resizing buffer: ${canvas.width}x${canvas.height} -> ${bufW}x${bufH}`);
			canvas.width = bufW;
			canvas.height = bufH;
		}

		ctx.clearRect(0, 0, bufW, bufH);

		if (!options.skipGuides) {
			// Draw Margin Guides (Experimental visibility)
			ctx.setLineDash([5, 5]);
			ctx.strokeStyle = "rgba(0,0,0,0.15)";
			ctx.lineWidth = 1;

			// Right margin guide
			const rightX = (currentTemplate.width - currentTemplate.marginRight) * MM_TO_PX * dpr;
			ctx.beginPath();
			ctx.moveTo(rightX, 0);
			ctx.lineTo(rightX, bufH);
			ctx.stroke();

			// Left margin guide
			const leftX = currentTemplate.marginLeft * MM_TO_PX * dpr;
			ctx.beginPath();
			ctx.moveTo(leftX, 0);
			ctx.lineTo(leftX, bufH);
			ctx.stroke();

			// Top margin guide
			const topY = currentTemplate.marginTop * MM_TO_PX * dpr;
			ctx.beginPath();
			ctx.moveTo(0, topY);
			ctx.lineTo(bufW, topY);
			ctx.stroke();

			// Bottom margin guide
			const bottomY = (currentTemplate.height - currentTemplate.marginBottom) * MM_TO_PX * dpr;
			ctx.beginPath();
			ctx.moveTo(0, bottomY);
			ctx.lineTo(bufW, bottomY);
			ctx.stroke();

			ctx.setLineDash([]);
		}

		labelRefs.forEach((el, i) => {
			if (!el || el.classList.contains('hidden')) return;

			const col = i % currentTemplate.cols;
			const row = Math.floor(i / currentTemplate.cols);

			const pxX = currentTemplate.marginLeft + col * (currentTemplate.labelWidth + currentTemplate.colGap);
			const pxY = currentTemplate.marginTop + row * (currentTemplate.labelHeight + currentTemplate.rowGap);

			const x = pxX * MM_TO_PX * dpr;
			const y = pxY * MM_TO_PX * dpr;

			try {
				// @ts-ignore
				ctx.drawElementImage(el, x, y);
			} catch (e) {
				console.warn(`[LabelStudio] Failed to draw label ${i}:`, e);
				// If we hit a "No cached paint record" error, a retry is often the only fix
				// as the browser finishes its layout pass.
			}
		});
		console.log('[LabelStudio] Render complete');
	}

	// Trigger render on changes
	$effect(() => {
		// Log dependencies triggering the effect
		const beanCount = selectedBeans.length;
		const refCount = labelRefs.filter(Boolean).length;

		console.log('[LabelStudio] Effect checking dependencies...', {
			templateId: currentTemplate?.id,
			beans: beanCount,
			refs: labelRefs.length,
			validRefs: refCount,
			settings: $state.snapshot(settings)
		});

		// Explicit dependency tracking
		// Access all template properties to trigger re-render on any dimension change
		currentTemplate.id;
		currentTemplate.width;
		currentTemplate.height;
		currentTemplate.labelWidth;
		currentTemplate.labelHeight;
		currentTemplate.labelPadding;
		currentTemplate.cols;
		currentTemplate.rows;
		currentTemplate.marginTop;
		currentTemplate.marginLeft;
		currentTemplate.marginRight;
		currentTemplate.marginBottom;
		currentTemplate.colGap;
		currentTemplate.rowGap;

		processedBeans; // Tracking the derived array
		labelRefs;
		settings.slim;
		settings.showName;
		settings.wrapName;
		settings.showOrigin;
		settings.showTags;
		settings.showTastingNotes;
		settings.showFarm;
		settings.showRegion;
		settings.showVarietal;
		settings.showProcess;
		settings.showRoastProfile;
		settings.showRoastLevel;
		settings.showElevation;
		settings.maxTastingNotes;

		// Deep tracking of bean data and notes
		for (const bean of processedBeans) {
			if (bean) {
				bean.name;
				bean._customNote; // Specifically watch the note
			}
		}
		for (const ref of labelRefs) { ref; }

		// Re-get context to check availability
		const ctx = canvas?.getContext("2d");

		if (canvas && ctx) {
			// If we expect labels but have none, we MUST wait.
			// The bind:this syntax is asynchronous in Svelte 5 during component destruction/creation.
			if (beanCount > 0 && refCount === 0) {
				console.log('[LabelStudio] No valid refs yet, waiting for bind:this...');
				return;
			}

			console.log('[LabelStudio] Scheduling render frame with refs:', refCount);
			// We use a small timeout + double rAF to give the browser time
			// to finish its internal layout/paint cache for the new elements.
			const timeout = setTimeout(() => {
				requestAnimationFrame(() => {
					requestAnimationFrame(renderCanvas);
				});
			}, 30);

			return () => {
				clearTimeout(timeout);
			};
		} else {
			console.log('[LabelStudio] Effect skipped: canvas/ctx missing', { canvas: !!canvas, ctx: !!ctx });
		}
	});

	// Force an update when the window changes (DPR might change if moving between screens)
	onMount(() => {
		const handleResize = () => {
			if (canvas) {
				const dpr = window.devicePixelRatio || 1;
				canvas.width = Math.round(currentTemplate.width * MM_TO_PX * dpr);
				canvas.height = Math.round(currentTemplate.height * MM_TO_PX * dpr);
			}
			renderCanvas();
		};
		window.addEventListener('resize', handleResize);
		return () => window.removeEventListener('resize', handleResize);
	});
</script>

<div class="flex flex-col bg-muted/30 print:bg-white min-h-screen">
	<!-- Header - Hidden on Print -->
	<header class="print:hidden flex justify-between items-center bg-white px-4 border-b h-14">
		<div class="flex items-center gap-4">
			<Button variant="ghost" size="icon" href="/" class="rounded-full">
				<ArrowLeft class="w-5 h-5" />
			</Button>
			<div class="flex items-center gap-2">
				<span class="w-8">{@html Logo}</span>
				<h1 class="font-bold text-xl">Label Studio</h1>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<Button variant="outline" onclick={handlePrint}>
				<Printer size={16} class="mr-2" />
				Print Labels
			</Button>
		</div>
	</header>

	<main class="print:block flex flex-1 print:p-0 overflow-hidden">
		<!-- Sidebar - Hidden on Print -->
		<aside class="print:hidden flex flex-col bg-white border-r w-80">
			<div class="flex-1 space-y-6 p-4 overflow-y-auto">
				<!-- Section 1: Search & Manage -->
				<section>
					<h3 class="flex items-center gap-2 mb-3 font-semibold text-sm">
						<Search size={14} class="text-primary" />
						Coffee Bean Search
					</h3>
					<div class="space-y-4">
						<BeanSearchCombobox
							bind:value={currentBeanPath}
							bind:selectedBean={currentBeanData}
							savedBeanPaths={data?.savedBeanPaths || []}
							originOptions={data?.originOptions || []}
						/>

						{#if currentBeanData}
							<div class="bg-primary/5 slide-in-from-top-1 p-3 border border-primary/20 rounded-lg animate-in fade-in">
								<div class="font-bold text-sm truncate">{currentBeanData.name}</div>
								<div class="mb-3 text-[10px] text-muted-foreground">{currentBeanData.roaster}</div>

								<div class="gap-2 grid grid-cols-1">
									<Button size="sm" class="w-full h-8 text-xs" onclick={fillAll}>
										Fill All {selectedBeans.length} Labels
									</Button>
									<p class="text-[10px] text-muted-foreground text-center italic">
										Or click a label slot in the preview to assign individually
									</p>
								</div>
							</div>
						{/if}

						<div class="flex gap-2">
							{#if selectedBeans.some(b => b !== null)}
								<Button variant="outline" size="sm" class="flex-1 hover:bg-destructive/5 border-destructive/20 h-8 text-destructive hover:text-destructive text-xs" onclick={clearAll}>
									<Trash2 class="mr-2 w-3 h-3" />
									Clear All
								</Button>
							{/if}
						</div>
					</div>
				</section>

				<!-- Section 2: Label Content -->
				<section class="pt-4 border-t">
					<h3 class="flex items-center gap-2 mb-4 font-semibold text-primary text-sm">
						<Settings2 size={14} />
						Label Content
					</h3>

					<div class="space-y-5">
						<!-- Presentation Style -->
						<div class="space-y-2">
							<button
								type="button"
								class="group flex justify-between items-center w-full text-left cursor-pointer"
								onclick={() => settings.slim = !settings.slim}
							>
								<Label class="font-bold text-[10px] uppercase tracking-wider cursor-pointer">Slim Visual Style</Label>
								<input type="checkbox" bind:checked={settings.slim} class="border-primary/30 rounded focus:ring-primary w-4 h-4 text-primary" onclick={(e: MouseEvent) => e.stopPropagation()} />
							</button>
							<p class="text-[10px] text-muted-foreground leading-tight">
								Uses a more compact layout with centered text and subtle separators.
							</p>
						</div>

						<!-- Core Fields -->
						<div class="space-y-2">
							<span class="block opacity-70 font-bold text-[9px] text-muted-foreground uppercase">Core</span>
							<div class="gap-x-4 gap-y-2 grid grid-cols-2">
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showName} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Bean Name</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.wrapName} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Wrap Name</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showOrigin} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Origin</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showFarm} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Farm/Estate</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showTags} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Tags</span>
								</label>
							</div>
						</div>

						<!-- Technical Details -->
						<div class="space-y-2">
							<span class="block opacity-70 font-bold text-[9px] text-muted-foreground uppercase">Bean Details</span>
							<div class="gap-x-4 gap-y-2 grid grid-cols-2">
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showRegion} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Region</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showElevation} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Elevation</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showVarietal} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Variety</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showProcess} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Process</span>
								</label>
							</div>
						</div>

						<!-- Tasting & Roast -->
						<div class="space-y-3 pt-1">
							<span class="block opacity-70 font-bold text-[9px] text-muted-foreground uppercase">Roast</span>
							<div class="gap-x-4 gap-y-2 grid grid-cols-2">
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showRoastProfile} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Profile</span>
								</label>
								<label class="group flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={settings.showRoastLevel} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" />
									<span class="text-[10px] group-hover:text-primary transition-colors">Level</span>
								</label>
							</div>

							<div class="space-y-2">
								<button
									type="button"
									class="group flex justify-between items-center w-full text-left cursor-pointer"
									onclick={() => settings.showTastingNotes = !settings.showTastingNotes}
								>
									<span class="text-[10px] group-hover:text-primary transition-colors">Show Tasting Notes</span>
									<input type="checkbox" bind:checked={settings.showTastingNotes} class="border-primary/30 rounded focus:ring-primary w-3.5 h-3.5 text-primary" onclick={(e: MouseEvent) => e.stopPropagation()} />
								</button>
								{#if settings.showTastingNotes}
									<div class="flex items-center gap-2 slide-in-from-left-1 animate-in fade-in">
										<Label class="text-[9px] text-muted-foreground uppercase whitespace-nowrap">Max Count:</Label>
										<Input type="number" bind:value={settings.maxTastingNotes} min="0" max="20" class="h-6 text-[10px]" />
									</div>
								{/if}
							</div>
						</div>

						<div class="bg-muted p-2 border-primary border-l-2 rounded-r-md">
							<p class="text-[10px] text-muted-foreground italic leading-tight">
								<span class="font-bold text-primary not-italic">Pro-tip:</span> Hover over assigned labels in the preview to add unique notes per bean.
							</p>
						</div>
					</div>
				</section>

				<!-- Section 3: Template & Layout -->
				<section class="pt-4 border-t">
					<h3 class="flex items-center gap-2 mb-4 font-semibold text-sm">
						<Layout size={14} class="text-muted-foreground" />
						Template & Layout
					</h3>

					<div class="space-y-4">
						<div class="space-y-1">
							<Label class="text-[9px] text-muted-foreground uppercase tracking-wider">Active Template</Label>
							<div class="flex flex-col gap-2">
								<select
									class="bg-transparent shadow-sm px-3 py-1 border border-input rounded-md w-full h-8 text-xs"
									onchange={(e) => {
										const val = (e.target as HTMLSelectElement).value;
										const found = [...PRESET_TEMPLATES, ...userTemplates].find(t => t.id === val);
										if (found) {
											currentTemplate = { ...found };
											// After template swap, ensure we trigger a re-render
											// currentTemplate itself is tracked, but sometimes the refs
											// need a nudge when the grid structure changes drastically
											labelRefs = [];
										}
									}}
								>
									<optgroup label="Presets">
										{#each PRESET_TEMPLATES as template}
											<option value={template.id} selected={currentTemplate.id === template.id}>
												{template.name}
											</option>
										{/each}
									</optgroup>
									{#if userTemplates.length > 0}
										<optgroup label="Your Templates">
											{#each userTemplates as template}
												<option value={template.id} selected={currentTemplate.id === template.id}>
													{template.name}
												</option>
											{/each}
										</optgroup>
									{/if}
								</select>

								<div class="flex gap-2">
									<Button variant="outline" size="sm" class="flex-1 h-7 text-[10px]" onclick={saveCurrentAsTemplate}>
										<Save size={12} class="mr-1.5" />
										Save New
									</Button>
									{#if currentTemplate.id.startsWith('user-')}
										<Button variant="secondary" size="sm" class="flex-1 h-7 text-[10px]" onclick={updateCurrentTemplate}>
											<Plus size={12} class="mr-1.5" />
											Update
										</Button>
										<Button variant="ghost" size="icon" class="hover:bg-destructive/5 w-7 h-7 text-destructive hover:text-destructive" onclick={() => deleteTemplate(currentTemplate.id)}>
											<Trash2 size={12} />
										</Button>
									{/if}
								</div>

								{#if !currentTemplate.id.startsWith('user-')}
									<p class="opacity-70 px-1 text-[10px] text-muted-foreground italic leading-tight">
										Presets are read-only. Save as a new template to customize.
									</p>
								{/if}
							</div>
						</div>

						<!-- Dimensions Accordion -->
						<div class="border rounded-md overflow-hidden">
							<button
								type="button"
								class="group flex justify-between items-center bg-muted/30 hover:bg-muted/50 px-3 py-2 w-full transition-colors"
								onclick={() => showDimensions = !showDimensions}
							>
								<span class="font-bold text-[10px] uppercase tracking-tight">Dimensions & Margins</span>
								{#if showDimensions}
									<ChevronDown size={14} class="text-muted-foreground group-hover:text-primary transition-colors" />
								{:else}
									<ChevronRight size={14} class="text-muted-foreground group-hover:text-primary transition-colors" />
								{/if}
							</button>

							{#if showDimensions}
								<div class="gap-3 grid grid-cols-2 slide-in-from-top-1 p-3 border-t animate-in fade-in">
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Page Width (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.width}
											oninput={(e) => { currentTemplate.width = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 font-medium text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Page Height (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.height}
											oninput={(e) => { currentTemplate.height = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 font-medium text-xs"
										/>
									</div>

									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Cols</Label>
										<Input
											type="number"
											value={currentTemplate.cols}
											oninput={(e) => { currentTemplate.cols = parseInt(e.currentTarget.value) || 0; }}
											min="1"
											max="10"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Rows</Label>
										<Input
											type="number"
											value={currentTemplate.rows}
											oninput={(e) => { currentTemplate.rows = parseInt(e.currentTarget.value) || 0; }}
											min="1"
											max="30"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Label Width (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.labelWidth}
											oninput={(e) => { currentTemplate.labelWidth = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Label Height (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.labelHeight}
											oninput={(e) => { currentTemplate.labelHeight = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Top Margin (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.marginTop}
											oninput={(e) => { currentTemplate.marginTop = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Bottom Margin (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.marginBottom}
											oninput={(e) => { currentTemplate.marginBottom = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Left Margin (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.marginLeft}
											oninput={(e) => { currentTemplate.marginLeft = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Right Margin (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.marginRight}
											oninput={(e) => { currentTemplate.marginRight = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Col Gap (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.colGap}
											oninput={(e) => { currentTemplate.colGap = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1">
										<Label class="text-[10px] text-muted-foreground uppercase tracking-wider">Row Gap (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.rowGap}
											oninput={(e) => { currentTemplate.rowGap = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="h-8 text-xs"
										/>
									</div>
									<div class="space-y-1 col-span-2">
										<Label class="font-bold text-[10px] text-primary uppercase tracking-wider">Label Inner Padding (mm)</Label>
										<Input
											type="number"
											value={currentTemplate.labelPadding}
											oninput={(e) => { currentTemplate.labelPadding = parseFloat(e.currentTarget.value) || 0; }}
											step="0.1"
											class="border-primary/30 h-8 text-xs"
										/>
									</div>
								</div>
							{/if}
						</div>

						<!-- Compact Verification -->
						{#if currentTemplate}
							<div class={cn(
								"flex justify-between items-center p-2 border rounded-md font-medium text-[10px]",
								(widthDiff > 1 || heightDiff > 1) ? "bg-destructive/5 border-destructive/20 text-destructive" : "bg-emerald-50 border-emerald-100 text-emerald-700"
							)}>
								<div class="flex items-center gap-2">
									<div class={cn("rounded-full w-1.5 h-1.5", (widthDiff > 1 || heightDiff > 1) ? "bg-destructive animate-pulse" : "bg-emerald-500")}></div>
									<span>{currentTemplate.pageSize} Check</span>
								</div>
								<div class="flex gap-3">
									<span class={cn(widthDiff > 1 && "font-bold underline")}>{calcWidth.toFixed(0)}/{currentTemplate.width}w</span>
									<span class={cn(heightDiff > 1 && "font-bold underline")}>{calcHeight.toFixed(0)}/{currentTemplate.height}h</span>
								</div>
							</div>
						{/if}
					</div>
				</section>
			</div>
		</aside>

		<!-- Content Area -->
		<div class="flex flex-1 justify-center bg-muted/30 print:bg-white p-8 print:p-0 overflow-auto">
			<!-- Print View - high-res snapshot of the canvas -->
			{#if printImage}
				<img
					src={printImage}
					alt="Labels to print"
					class="hidden print:block w-full h-auto"
					style:width="{currentTemplate.width}mm"
					style:height="{currentTemplate.height}mm"
				/>
			{/if}

			<div class="print:hidden relative bg-white shadow-2xl border border-gray-200 h-fit"
				style:width="{currentTemplate.width * MM_TO_PX}px"
				style:height="{currentTemplate.height * MM_TO_PX}px"
			>
				{#if !isSupported}
					<div class="z-50 absolute inset-0 flex flex-col justify-center items-center bg-white/95 backdrop-blur-sm p-8 text-center">
						<div class="bg-amber-100 mb-6 p-4 rounded-full text-amber-600">
							<Settings2 size={40} />
						</div>
						<h2 class="mb-2 font-bold text-2xl tracking-tight">HTML in Canvas feature required!</h2>
						<p class="mb-8 max-w-md text-muted-foreground text-sm">
							We rely on a feature currently only available in beta called <a href="https://html-in-canvas.dev/" target="_blank" rel="noopener noreferrer" class="underline">HTML in Canvas</a>. You need a recent version of Chrome (or Chrome-based browser) with an experimental flag enabled to use Label Studio. Don't worry, it's easy to set up and we'll guide you through it!
						</p>

						<div class="space-y-6 w-full max-w-sm text-left">
							<div class="space-y-3">
								<div class="flex items-center gap-2">
									<div class="flex flex-shrink-0 justify-center items-center bg-primary rounded-full w-5 h-5 font-bold text-[10px] text-white">1</div>
									<span class="font-semibold text-sm">Paste this URL into your address bar</span>
								</div>
								<div class="flex flex-col gap-2 bg-muted p-2 border border-primary/20 rounded">
									<code class="font-mono text-primary text-xs select-all">chrome://flags/#canvas-draw-element</code>
									<p class="text-[10px] text-muted-foreground italic leading-tight">
										Chrome blocks direct links to chrome:// pages for security, so copy-paste is required. Brave users: brave:// also works.
									</p>
								</div>
							</div>

							<div class="space-y-3">
								<div class="flex items-center gap-2">
									<div class="flex flex-shrink-0 justify-center items-center bg-primary rounded-full w-5 h-5 font-bold text-[10px] text-white">2</div>
									<span class="font-semibold text-sm">Set "Enable the new drawElement API for Canvas" to Enabled</span>
								</div>
							</div>

							<div class="space-y-3">
								<div class="flex items-center gap-2">
									<div class="flex flex-shrink-0 justify-center items-center bg-primary rounded-full w-5 h-5 font-bold text-[10px] text-white">3</div>
									<span class="font-semibold text-sm">Relaunch the browser</span>
								</div>
								<p class="pl-7 text-[11px] text-muted-foreground leading-tight">
									Hit Relaunch at the bottom of the flags page, then reload this site.
								</p>
							</div>
						</div>

						<Button
							variant="outline"
							size="sm"
							class="mt-10"
							onclick={() => window.location.reload()}
						>
							Reload Page
						</Button>
					</div>
				{/if}

				<!-- The actual canvas - will use HTML-in-Canvas -->
				<canvas
					bind:this={canvas}
					style:width="{currentTemplate.width * MM_TO_PX}px"
					style:height="{currentTemplate.height * MM_TO_PX}px"
					class="z-10 absolute inset-0 pointer-events-none"
					{...{ layoutsubtree: "" }}
				>
					<!-- Direct children of canvas with layoutsubtree -->
					{#key currentTemplate.id + '-' + currentTemplate.rows + 'x' + currentTemplate.cols}
						{#each processedBeans as bean, i (currentTemplate.id + '-' + i)}
							<div
								bind:this={labelRefs[i]}
								style:width="{currentTemplate.labelWidth * MM_TO_PX}px"
								style:height="{currentTemplate.labelHeight * MM_TO_PX}px"
								style:padding="{currentTemplate.labelPadding * MM_TO_PX}px"
								class="box-border {bean ? '' : 'hidden'}"
							>
								{#if bean}
									<CoffeeBeanTile
										{bean}
										variant="label"
										slim={settings.slim}
										wrapName={settings.wrapName}
										customNote={bean._customNote}
										showOrigin={settings.showOrigin}
										showTags={settings.showTags}
										showTastingNotes={settings.showTastingNotes}
									/>
								{/if}
							</div>
						{/each}
					{/key}
				</canvas>

				<!-- UI Overlay for interaction -->
				<div
					class="z-20 absolute inset-0 grid pointer-events-none"
					style:grid-template-columns="repeat({currentTemplate.cols}, {currentTemplate.labelWidth * MM_TO_PX}px)"
					style:grid-template-rows="repeat({currentTemplate.rows}, {currentTemplate.labelHeight * MM_TO_PX}px)"
					style:gap="{currentTemplate.rowGap * MM_TO_PX}px {currentTemplate.colGap * MM_TO_PX}px"
					style:padding="{currentTemplate.marginTop * MM_TO_PX}px {currentTemplate.marginRight * MM_TO_PX}px {currentTemplate.marginBottom * MM_TO_PX}px {currentTemplate.marginLeft * MM_TO_PX}px"
				>
					{#each processedBeans as bean, i}
						<div class="group relative flex justify-center items-center bg-transparent hover:bg-primary/5 border border-gray-100 border-dashed transition-colors pointer-events-auto">
							<button
								type="button"
								class="absolute inset-0 w-full h-full cursor-pointer"
								onclick={() => {
									if (currentBeanData) {
										assignBean(currentBeanData, i);
									}
								}}
							>
								{#if !bean}
									<span class="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground uppercase">Assign</span>
								{/if}
							</button>

							{#if bean}
								<div class="right-2 bottom-2 left-2 z-10 absolute opacity-0 group-hover:opacity-100 transition-opacity">
									<Input
										bind:value={beanNotes[i]}
										placeholder="Add note..."
										class="bg-white/90 shadow-sm border-gray-200 h-7 text-[10px]"
										onclick={(e: MouseEvent) => e.stopPropagation()}
									/>
								</div>
								<button
									type="button"
									class="top-1 right-1 absolute opacity-0 group-hover:opacity-100 p-1 rounded-full text-gray-400 hover:text-destructive transition-opacity pointer-events-auto"
									onclick={(e: MouseEvent) => {
										e.stopPropagation();
										selectedBeans[i] = null;
										beanNotes[i] = "";
									}}
								>
									<X class="w-3 h-3" />
								</button>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		</div>
	</main>
</div>

<style>
	@media print {
		:global(body) {
			margin: 0;
			padding: 0;
			-webkit-print-color-adjust: exact !important;
			print-color-adjust: exact !important;
		}
		img {
			display: block !important;
			page-break-after: always;
		}
	}
</style>
