<script lang="ts">
	import { onMount } from "svelte";
	import { fade } from "svelte/transition";
	import { browser } from "$app/environment";
	import { Button } from "$lib/components/ui/button/index.js";
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { userSettings } from "$lib/stores/userSettings.svelte";
	import { db, getTastingHistory, type TastingSession } from "$lib/db/localdb";
	import { getBrewToken } from "$lib/api/brew.remote";
	import { api, type CoffeeBean } from "$lib/api";
	import BeanSearchCombobox from "$lib/components/tasting/BeanSearchCombobox.svelte";
	import {
		Play,
		Pause,
		RotateCcw,
		Video,
		CheckCircle,
		Volume2,
		VolumeX,
		Thermometer,
		Scale,
		Settings,
		ChevronLeft,
		Zap,
		User,
		Info,
		Coffee,
		CheckCircle2,
		AlertCircle
	} from "lucide-svelte";
	import LoadingIcon from "virtual:icons/line-md/loading-twotone-loop";

	let { data } = $props();

	// App State
	let savedBeansList = $state<{ label: string; urlPath: string; data: CoffeeBean; notes?: string }[]>([]);
	let savedBeanPaths = $state<string[]>([]);
	let selectedBeanUrlPath = $state<string | null | undefined>("");
	let selectedBeanDetails = $state<CoffeeBean | null>(null);
	let isCustomDose = $state(false);
	let doseG = $state<number>(15.0);
	let selectedBrewer = $state<string>("V60");
	let customBrewer = $state<string>("");
	let selectedGrinder = $state<string>("Comandante C40");
	let customGrinder = $state<string>("");
	let soundEnabled = $state<boolean>(true);
	let additionalGuidance = $state<string>("");

	// Fetch status
	let isLoadingBeans = $state(true);
	let isGenerating = $state(false);
	let errorMsg = $state("");

	// Loaded Recipe
	interface GeneratedStep {
		id: number;
		title: string;
		time_range: string;
		water_pour_g: number | null;
		accumulated_water_g: number;
		description: string;
	}
	interface GeneratedRecipe {
		introduction: string;
		parameters: {
			coffee_dose_g: number;
			water_ratio: string;
			total_water_g: number;
			grind_size_recommendation: string;
			water_temp_c: string;
			filter_paper: string;
		};
		steps: GeneratedStep[];
		adjustments: { condition: string; action: string }[];
	}

	let recipe = $state<GeneratedRecipe | null>(null);

	// Brewing Live State
	let isTimerRunning = $state(false);
	let elapsedTime = $state(0); // in seconds
	let timerInterval: any = null;
	let currentStepId = $state<number | null>(null);

	// Re-hydrated Selected Bean Fields
	let currentBeanInfo = $derived.by(() => {
		if (!selectedBeanUrlPath || selectedBeanUrlPath === "custom") {
			return {
				name: "Custom Coffee Bean",
				roaster: "Custom Roaster",
				process: "Washed",
				variety: "Arabica",
				roast_level: "Medium-Light",
				roast_profile: "Filter",
				description: "",
				tasting_notes: [],
				personal_notes: ""
			};
		}
		if (selectedBeanDetails) {
			const b = selectedBeanDetails;
			const varieties = b.origins ? b.origins.map(o => o.variety).filter(Boolean).join(", ") : "";
			const processes = b.origins ? b.origins.map(o => o.process).filter(Boolean).join(", ") : "";
			const found = savedBeansList.find(item => item.urlPath === selectedBeanUrlPath);
			return {
				name: b.name,
				roaster: b.roaster,
				process: processes || b.roast_profile || "Unknown Process",
				variety: varieties || "Unknown Variety",
				roast_level: b.roast_level || "Medium-Light",
				roast_profile: b.roast_profile || "Filter",
				description: b.description || "",
				tasting_notes: b.tasting_notes ? b.tasting_notes.map((n: any) => typeof n === "string" ? n : n.note) : [],
				personal_notes: found?.notes || ""
			};
		}
		const found = savedBeansList.find(b => b.urlPath === selectedBeanUrlPath);
		if (found) {
			const b = found.data;
			const varieties = b.origins ? b.origins.map(o => o.variety).filter(Boolean).join(", ") : "";
			const processes = b.origins ? b.origins.map(o => o.process).filter(Boolean).join(", ") : "";
			return {
				name: b.name,
				roaster: b.roaster,
				process: processes || b.roast_profile || "Unknown Process",
				variety: varieties || "Unknown Variety",
				roast_level: b.roast_level || "Medium-Light",
				roast_profile: b.roast_profile || "Filter",
				description: b.description || "",
				tasting_notes: b.tasting_notes ? b.tasting_notes.map((n: any) => typeof n === "string" ? n : n.note) : [],
				personal_notes: found.notes || ""
			};
		}
		return null;
	});

	// Save brew configurations to localStorage
	$effect(() => {
		if (browser) {
			localStorage.setItem("brew_dose_g", String(doseG));
		}
	});
	$effect(() => {
		if (browser) {
			localStorage.setItem("brew_selected_brewer", selectedBrewer);
			localStorage.setItem("brew_custom_brewer", customBrewer);
		}
	});
	$effect(() => {
		if (browser) {
			localStorage.setItem("brew_selected_grinder", selectedGrinder);
			localStorage.setItem("brew_custom_grinder", customGrinder);
		}
	});

	// Sound oscillator helper to play clean browser alerts without file links
	function playSound(type: 'start' | 'next' | 'complete' = 'next') {
		if (!soundEnabled || typeof window === 'undefined') return;
		try {
			const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
			const osc = ctx.createOscillator();
			const gain = ctx.createGain();
			osc.connect(gain);
			gain.connect(ctx.destination);

			if (type === 'start') {
				osc.type = 'sine';
				osc.frequency.setValueAtTime(523.25, ctx.currentTime); // C5
				osc.frequency.setValueAtTime(659.25, ctx.currentTime + 0.12); // E5
				gain.gain.setValueAtTime(0.08, ctx.currentTime);
				gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
				osc.start();
				osc.stop(ctx.currentTime + 0.35);
			} else if (type === 'next') {
				osc.type = 'sine';
				osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
				osc.frequency.setValueAtTime(880.00, ctx.currentTime + 0.1); // A5
				gain.gain.setValueAtTime(0.08, ctx.currentTime);
				gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
				osc.start();
				osc.stop(ctx.currentTime + 0.25);
			} else if (type === 'complete') {
				osc.type = 'triangle';
				osc.frequency.setValueAtTime(261.63, ctx.currentTime); // C4
				osc.frequency.setValueAtTime(329.63, ctx.currentTime + 0.15); // E4
				osc.frequency.setValueAtTime(392.00, ctx.currentTime + 0.3); // G4
				osc.frequency.setValueAtTime(523.25, ctx.currentTime + 0.45); // C5
				gain.gain.setValueAtTime(0.12, ctx.currentTime);
				gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.82);
				osc.start();
				osc.stop(ctx.currentTime + 0.82);
			}
		} catch (e) {
			console.warn("Audio Context beep failed", e);
		}
	}

	onMount(async () => {
		if (browser) {
			// Restore saved brew preferences
			const storedDose = localStorage.getItem("brew_dose_g");
			if (storedDose !== null) {
				const parsed = parseFloat(storedDose);
				if (!isNaN(parsed)) {
					doseG = parsed;
					isCustomDose = true;
				}
			}

			const storedSelectedBrewer = localStorage.getItem("brew_selected_brewer");
			if (storedSelectedBrewer !== null) selectedBrewer = storedSelectedBrewer;

			const storedCustomBrewer = localStorage.getItem("brew_custom_brewer");
			if (storedCustomBrewer !== null) customBrewer = storedCustomBrewer;

			const storedSelectedGrinder = localStorage.getItem("brew_selected_grinder");
			if (storedSelectedGrinder !== null) selectedGrinder = storedSelectedGrinder;

			const storedCustomGrinder = localStorage.getItem("brew_custom_grinder");
			if (storedCustomGrinder !== null) customGrinder = storedCustomGrinder;

			try {
				const [savedLocal, customLocal] = await Promise.all([
					db.savedBeans.filter(b => !b.deletedAt).toArray(),
					db.customBeans.filter(b => !b.deletedAt).toArray()
				]);

				const list: typeof savedBeansList = [];

				for (const s of savedLocal) {
					if (s.beanData) {
						list.push({
							label: `${s.beanData.name} (${s.beanData.roaster})`,
							urlPath: s.beanUrlPath,
							data: s.beanData,
							notes: s.notes || ""
						});
					}
				}

				for (const c of customLocal) {
					if (c.beanData) {
						list.push({
							label: `${c.beanData.name} — Custom (${c.beanData.roaster})`,
							urlPath: c.beanUrlPath,
							data: c.beanData,
							notes: ""
						});
					}
				}

				savedBeansList = list;
				savedBeanPaths = [
					...savedLocal.map(b => b.beanUrlPath),
					...customLocal.map(b => b.beanUrlPath)
				];

				// Preload from context if provided
				if (data.beanUrlPath) {
					const hasBean = list.find(b => b.urlPath === data.beanUrlPath);
					if (hasBean) {
						selectedBeanUrlPath = data.beanUrlPath;
						selectedBeanDetails = hasBean.data;
					} else {
						// Download bean metadata from core catalog
						await fetchBeanInfoFromAPI(data.beanUrlPath);
					}
				} else {
					selectedBeanUrlPath = "";
				}
			} catch (e) {
				console.error("Failed to list saved beans", e);
				selectedBeanUrlPath = "";
			} finally {
				isLoadingBeans = false;
			}
		}
	});

	async function fetchBeanInfoFromAPI(urlPath: string) {
		try {
			// Url starts with /roasters/some_roaster/some_bean
			const parts = urlPath.split("/").filter(Boolean);
			if (parts.length >= 3 && parts[0] === "roasters") {
				const roasterSlug = parts[1];
				const beanSlug = parts[2];
				const response = await fetch(`/api/v1/beans/${roasterSlug}/${beanSlug}`);
				if (response.ok) {
					const res = await response.json();
					if (res?.data) {
						const apiBean = res.data;
						savedBeansList = [{
							label: `${apiBean.name} (${apiBean.roaster})`,
							urlPath,
							data: apiBean,
							notes: ""
						}, ...savedBeansList];
						selectedBeanUrlPath = urlPath;
						selectedBeanDetails = apiBean;
					}
				}
			}
		} catch (err) {
			console.error("Could not fetch remote bean from API catalog", err);
			selectedBeanUrlPath = "";
		}
	}

	async function generateRecipe() {
		if (!currentBeanInfo) return;
		isGenerating = true;
		errorMsg = "";
		recipe = null;

		// Stop any ticking timer
		resetBrewTracker();

		try {
			// Phase 1: Retrieve signed JWT Authorization token from SvelteKit query endpoint
			const token = await getBrewToken();

			const activeBrewer = selectedBrewer === "custom" ? customBrewer : selectedBrewer;
			const activeGrinder = selectedGrinder === "custom" ? customGrinder : selectedGrinder;

			// Fetch all tasting sessions with brewing notes
			const tastings = await getTastingHistory();
			const previousBrewingNotes = tastings
				.filter(t => t.brewingNotes && t.brewingNotes.trim().length > 4)
				.map(t => {
					const notes = t.brewingNotes!.trim();
					const beanLabel = t.beanName || t.sourceBean || "Unknown Bean";
					const roasterLabel = t.roasterName || "Unknown Roaster";

					// Build a comprehensive, rich description of this historical session:
					let beanDetails: string[] = [];
					if (t.beanData) {
						if (t.beanData.roast_level) beanDetails.push(`Roast Level: ${t.beanData.roast_level}`);
						if (t.beanData.roast_profile) beanDetails.push(`Roast Profile: ${t.beanData.roast_profile}`);

						if (t.beanData.origins && t.beanData.origins.length > 0) {
							const origins = t.beanData.origins;
							const originsProps = origins.map((org, idx) => {
								const detail = [];
								if (org.country_full_name || org.country) detail.push(`Origin: ${org.country_full_name || org.country}`);
								if (org.region) detail.push(`Region: ${org.region}`);
								if (org.process) detail.push(`Process: ${org.process}`);
								if (org.variety) detail.push(`Variety: ${org.variety}`);
								if (org.elevation_min || org.elevation_max) {
									const elev = org.elevation_min === org.elevation_max
										? `${org.elevation_min}m`
										: `${org.elevation_min}-${org.elevation_max}m`;
									detail.push(`Elevation: ${elev}`);
								}
								return `Origin-${idx + 1}[${detail.join(", ")}]`;
							}).join(" ");
							if (originsProps) beanDetails.push(originsProps);
						}
					}

					let sessionRatings: string[] = [];
					if (t.basics) {
						const basicsList = Object.entries(t.basics)
							.filter(([_, val]) => val)
							.map(([key, val]) => `${key}: ${val}`);
						if (basicsList.length > 0) {
							sessionRatings.push(`Basics(${basicsList.join(", ")})`);
						}
					}
					if (t.mouthfeel) {
						const mouthfeelList = Object.entries(t.mouthfeel)
							.filter(([_, val]) => val)
							.map(([key, val]) => `${key}: ${val}`);
						if (mouthfeelList.length > 0) {
							sessionRatings.push(`Mouthfeel(${mouthfeelList.join(", ")})`);
						}
					}
					if (t.intensity) {
						const intensityList = Object.entries(t.intensity)
							.filter(([_, val]) => typeof val === "number" || val)
							.map(([key, val]) => `${key}: ${val}`);
						if (intensityList.length > 0) {
							sessionRatings.push(`Intensity(${intensityList.join(", ")})`);
						}
					}
					if (t.selectedNotes && t.selectedNotes.length > 0) {
						sessionRatings.push(`Flavor Notes: ${t.selectedNotes.join(", ")}`);
					}

					const formattedDate = t.date ? new Date(t.date).toLocaleDateString() : "Unknown Date";
					const beanInfoStr = beanDetails.length > 0 ? ` {${beanDetails.join(" | ")}}` : "";
					const ratingsStr = sessionRatings.length > 0 ? ` [Profile: ${sessionRatings.join(" | ")}]` : "";

					return `On ${formattedDate}, brewed ${beanLabel} by ${roasterLabel}${beanInfoStr}${ratingsStr} -> Note: "${notes}"`;
				});

			// Phase 2: Call secured FastAPI backend recipe generator
			const requestPayload = {
				bean_name: currentBeanInfo.name,
				roaster_name: currentBeanInfo.roaster,
				process: currentBeanInfo.process,
				variety: currentBeanInfo.variety,
				roast_level: currentBeanInfo.roast_level,
				roast_profile: currentBeanInfo.roast_profile,
				description: currentBeanInfo.description,
				tasting_notes: currentBeanInfo.tasting_notes,
				personal_notes: currentBeanInfo.personal_notes,
				additional_guidance: additionalGuidance,
				previous_brewing_notes: previousBrewingNotes,
				parameters: {
					dose_g: doseG,
					brewer: activeBrewer || "Brewer",
					grinder: activeGrinder || "Grinder"
				}
			};

			const response = await fetch("/api/v1/brew-assistant/recipe", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
					"Authorization": `Bearer ${token}`
				},
				body: JSON.stringify(requestPayload)
			});

			if (!response.ok) {
				const errBody = await response.json();
				throw new Error(errBody.detail || "Server failed to analyze coffee data.");
			}

			recipe = await response.json();

			// Hydrate the visual tracking status for the new recipe
			if (recipe) {
				currentStepId = recipe.steps.length > 0 ? recipe.steps[0].id : null;
			}
		} catch (e: any) {
			console.error("Failed to generate custom brew recipe:", e);
			errorMsg = e.message || "Network request failed. Please check internet connection.";
		} finally {
			isGenerating = false;
		}
	}

	// Live Brewing Timer Engine
	function toggleTimer() {
		if (isTimerRunning) {
			clearInterval(timerInterval);
			isTimerRunning = false;
		} else {
			if (elapsedTime === 0) {
				playSound('start');
			}
			isTimerRunning = true;
			timerInterval = setInterval(() => {
				elapsedTime += 1;
				analyzeCurrentActiveStep();
			}, 1000);
		}
	}

	function resetBrewTracker() {
		clearInterval(timerInterval);
		isTimerRunning = false;
		elapsedTime = 0;
		currentStepId = recipe ? (recipe.steps.length > 0 ? recipe.steps[0].id : null) : null;
	}

	function formatClock(totalSeconds: number): string {
		const mins = Math.floor(totalSeconds / 60);
		const secs = totalSeconds % 60;
		return `${mins}:${secs.toString().padStart(2, "0")}`;
	}

	// Evaluates the active step based on time ranges returned from Gemini
	// Example time_range string formats: "0:00 - 0:30", "0:30 - 1:15", "1:15 - 2:00", "2:00 to 2:15"
	function analyzeCurrentActiveStep() {
		if (!recipe) return;

		let foundActive = false;

		for (const step of recipe.steps) {
			const timeRange = step.time_range.replace(/\s+/g, "").toLowerCase();
			if (!timeRange) continue;

			// Extract digits, translating words like "to" or "-" to start/end delimiters
			// Handles "0:00-0:30", "0:30to1:15" or singular "2:00"
			const delim = timeRange.includes("to") ? "to" : (timeRange.includes("-") ? "-" : null);

			if (delim) {
				const parts = timeRange.split(delim);
				const startSec = timeToSeconds(parts[0]);
				const endSec = timeToSeconds(parts[1]);

				if (elapsedTime >= startSec && elapsedTime < endSec) {
					if (currentStepId !== step.id) {
						currentStepId = step.id;
						playSound('next');
					}
					foundActive = true;
					break;
				}
			} else {
				// Single exact or trailing step representation
				const startSec = timeToSeconds(timeRange);
				if (elapsedTime >= startSec) {
					if (currentStepId !== step.id) {
						currentStepId = step.id;
						playSound('next');
					}
					foundActive = true;
					break;
				}
			}
		}

		// Check if timer exceeds the cumulative drawdown time range
		if (recipe.steps.length > 0) {
			const lastStep = recipe.steps[recipe.steps.length - 1];
			const lastTimeParts = lastStep.time_range.replace(/\s+/g, "").toLowerCase().split(/[-to]/);
			const endCap = lastTimeParts.length > 1 ? timeToSeconds(lastTimeParts[1]) : timeToSeconds(lastTimeParts[0]) + 30;

			if (elapsedTime >= endCap && isTimerRunning) {
				clearInterval(timerInterval);
				isTimerRunning = false;
				playSound('complete');
				// Mark all checked
				currentStepId = null;
			}
		}
	}

	function timeToSeconds(timeStr: string): number {
		const parts = timeStr.trim().split(":");
		if (parts.length === 2) {
			return parseInt(parts[0]) * 60 + parseInt(parts[1]);
		}
		const parsed = parseInt(timeStr);
		return isNaN(parsed) ? 0 : parsed;
	}

</script>

<svelte:head>
	<title>Interactive Coffee Brewing Assistant — Kissaten</title>
	<meta name="description" content="A beta hand-brewing assistant that offers tailored recipe directions, grind recommendation ticks, and step-by-step scaling stopwatch." />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-5xl container">
	<!-- Mini app layout header -->
	<div class="flex md:flex-row flex-col justify-between items-start md:items-center gap-4 mb-8 pb-6 border-b">
		<div>
			<h1 class="flex items-center gap-3 font-bold dark:text-cyan-100 text-3xl md:text-4xl tracking-tight">
				<Coffee class="w-8 h-8 text-amber-500 animate-pulse" />
				Brewing Assistant
				<span class="bg-primary/20 dark:bg-cyan-500/10 px-2 py-0.5 border border-primary/20 dark:border-cyan-500/20 rounded-md font-mono text-primary dark:text-cyan-400 text-xs uppercase leading-none tracking-widest">Beta</span>
			</h1>
			<p class="mt-1 text-muted-foreground text-sm">
				Generate custom brew recipes tailored to your saved coffee beans and historical tasting notes. Follow step-by-step brewing instructions with an integrated timer and grind recommendations.
			</p>
		</div>
		<div class="flex items-center gap-2">
			<Button variant="outline" href="/search" class="text-sm">
				<ChevronLeft class="mr-1.5 w-4 h-4" />
				Back to search
			</Button>
			<button class="bg-muted hover:opacity-80 p-2 rounded-lg transition-all" onclick={() => soundEnabled = !soundEnabled} title={soundEnabled ? "Mute sounds" : "Unmute sounds"}>
				{#if soundEnabled}
					<Volume2 class="w-5 h-5 text-muted-foreground" />
				{:else}
					<VolumeX class="w-5 h-5 text-red-400" />
				{/if}
			</button>
		</div>
	</div>

	<!-- Beta Access Gate -->
	{#if !userSettings.betaEnabled}
		<Card class="bg-amber-500/5 shadow-lg mx-auto mt-12 border-amber-500/30 max-w-xl">
			<CardHeader class="flex flex-col items-center text-center">
				<div class="bg-amber-500/10 mb-2 p-3 rounded-full">
					<Zap class="w-8 h-8 text-amber-500 animate-bounce" />
				</div>
				<CardTitle class="font-bold dark:text-amber-300 text-2xl">Beta Access Required</CardTitle>
				<CardDescription class="md:px-6 text-muted-foreground">
					The algorithmic Hand-Brewing Assistant is a restricted closed-experimental environment reserved for Kissaten Beta testers only.
				</CardDescription>
			</CardHeader>
			<CardContent class="flex flex-col items-center">
				<p class="mb-6 text-muted-foreground text-sm text-center leading-relaxed">
					To start brewing custom recipes matching Comandante/Ode settings, go to your Profile Settings, activate your developer beta privilege role, and toggle "Beta Features" on.
				</p>
				<div class="flex gap-4">
					<Button href="/profile">Configure Profile</Button>
					<Button variant="outline" href="/search">Explore Catalog</Button>
				</div>
			</CardContent>
		</Card>
	{:else}
		<!-- Main Interactive Interface -->
		<div class="gap-8 grid grid-cols-1 lg:grid-cols-3">
			<!-- Configuration Column -->
			<div class="space-y-6 lg:col-span-1">
				<Card class="dark:border-cyan-500/20">
					<CardHeader>
						<CardTitle class="flex items-center gap-2 text-md">
							<Settings class="w-4 h-4 text-cyan-500" />
							Brew Parameters
						</CardTitle>
						<CardDescription>Specify your brewer, grinder, and coffee bed weight.</CardDescription>
					</CardHeader>
					<CardContent class="space-y-4">
						<!-- Select Coffee Bean -->
						<div class="space-y-1.5">
							<span class="block font-medium text-muted-foreground text-xs uppercase tracking-wider">Select Coffee Bean</span>
							{#if isLoadingBeans}
								<div class="flex items-center gap-2 bg-muted/20 px-3 py-2 border rounded-lg text-muted-foreground text-sm">
									<LoadingIcon width="16" height="16" /> Loading saved coffees...
								</div>
							{:else}
								<BeanSearchCombobox
									bind:value={selectedBeanUrlPath}
									bind:selectedBean={selectedBeanDetails}
									savedBeanPaths={savedBeanPaths}
									originOptions={data?.originOptions || []}
								/>
							{/if}
						</div>

						<!-- Dose Selector -->
						<div class="space-y-1.5 pt-1">
							<div class="flex justify-between items-center">
								<span class="font-medium text-muted-foreground text-xs uppercase tracking-wider">Coffee Dose (grams)</span>
								<div class="flex items-center gap-1">
									<button class="bg-muted px-1.5 py-0.5 rounded-sm text-[10px] text-primary hover:underline" onclick={() => { doseG = 12.0; isCustomDose = true; }}>12g</button>
									<button class="bg-muted px-1.5 py-0.5 rounded-sm text-[10px] text-primary hover:underline" onclick={() => { doseG = 15.0; isCustomDose = false; }}>15g</button>
									<button class="bg-muted px-1.5 py-0.5 rounded-sm text-[10px] text-primary hover:underline" onclick={() => { doseG = 18.0; isCustomDose = true; }}>18g</button>
                                    <button class="bg-muted px-1.5 py-0.5 rounded-sm text-[10px] text-primary hover:underline" onclick={() => { doseG = 24.0; isCustomDose = true; }}>24g</button>
								</div>
							</div>
							<div class="flex items-center gap-2">
								<Input type="number" step="0.1" min="4" max="50" bind:value={doseG} oninput={() => isCustomDose = true} class="w-24 font-mono text-sm text-center" />
								<span class="text-muted-foreground text-xs">Dry grounds weight.</span>
							</div>
						</div>

						<!-- Brewer Model -->
						<div class="space-y-1.5 pt-1">
							<label for="brewer-select" class="block font-medium text-muted-foreground text-xs uppercase tracking-wider">Brewer Device</label>
							<select id="brewer-select" class="bg-background px-3 py-2 border rounded-lg focus-visible:outline-none w-full text-sm select-reset" bind:value={selectedBrewer}>
								<option value="V60">Hario V60</option>
								<option value="Baby Orea">Baby Orea</option>
								<option value="Orea V3/V4">Orea V3 / V4 Flat-Bottom</option>
								<option value="Aeropress">Aeropress (Immersion)</option>
								<option value="Origami">Origami Dripper (Kalita paper)</option>
                                <option value="Cafelat Robot">Cafelat Robot</option>
                                <option value="Gaggia Classic Pro">Gaggia Classic Pro</option>
								<option value="custom">✏️ Enter Custom Brewer...</option>
							</select>
							{#if selectedBrewer === "custom"}
								<Input type="text" placeholder="e.g. Hario Switch" bind:value={customBrewer} class="mt-2 text-sm" />
							{/if}
						</div>

						<!-- Grinder Model -->
						<div class="space-y-1.5 pt-1">
							<label for="grinder-select" class="block font-medium text-muted-foreground text-xs uppercase tracking-wider">Grinder Model</label>
							<select id="grinder-select" class="bg-background px-3 py-2 border rounded-lg focus-visible:outline-none w-full text-sm select-reset" bind:value={selectedGrinder}>
								<option value="Comandante C40">Comandante C40 (Clicks)</option>
								<option value="Fellow Ode Gen 2">Fellow Ode Gen 2 (Dial setting)</option>
								<option value="Fellow Ode Gen 1">Fellow Ode Gen 1</option>
								<option value="Baratza Encore">Baratza Encore (Stepped Dial)</option>
								<option value="Wilfa Svart">Wilfa Svart</option>
								<option value="Timemore C3">Timemore C3</option>
								<option value="Kingrinder K6">Kingrinder K6</option>
								<option value="custom">✏️ Enter Custom Grinder...</option>
							</select>
							{#if selectedGrinder === "custom"}
								<Input type="text" placeholder="e.g. Izpresso K-Ultra" bind:value={customGrinder} class="mt-2 text-sm" />
							{/if}
						</div>

						<!-- Additional Guidance Field -->
						<div class="space-y-1.5 pt-1">
							<label for="additional-guidance" class="block font-medium text-muted-foreground text-xs uppercase tracking-wider">Additional Guidance</label>
							<Input id="additional-guidance" type="text" placeholder="e.g. well rested, fresh roasts, lots of fines" bind:value={additionalGuidance} class="text-sm" />
						</div>

						<!-- Generate Trigger -->
						<Button class="relative mt-2 w-full overflow-hidden font-semibold" onclick={generateRecipe} disabled={isGenerating || !currentBeanInfo}>
							{#if isGenerating}
								<LoadingIcon width="16" height="16" class="mr-2" />
								Analyzing Coffee Bed...
							{:else}
								<Zap class="mr-2 w-4 h-4" />
								Formulate Recipe
							{/if}
						</Button>
						{#if errorMsg}
							<div class="flex items-center gap-1.5 bg-red-50 dark:bg-red-950/20 p-2.5 border border-red-200 dark:border-red-800/30 rounded-lg font-medium text-red-500 text-xs">
								<AlertCircle class="w-3.5 h-3.5 shrink-0" />
								<span>{errorMsg}</span>
							</div>
						{/if}
					</CardContent>
				</Card>

			</div>

			<!-- Recipe Outcomes Column -->
			<div class="space-y-6 lg:col-span-2">
				{#if !recipe && !isGenerating}
					<div class="flex flex-col justify-center items-center bg-muted/10 p-12 border border-dashed rounded-2xl h-full text-center">
						<div class="bg-primary/5 mb-3 p-4 rounded-full">
							<Coffee class="w-12 h-12 text-muted-foreground/50" />
						</div>
						<h3 class="font-bold text-muted-foreground text-lg">Ready to Brew</h3>
						<p class="mt-1 max-w-sm text-muted-foreground text-sm">
							Fill out your coffee dose, brewer, and click "Formulate Recipe" to generate a tailored extraction routine using Gemini Flash.
						</p>
					</div>
				{:else if isGenerating}
					<!-- Beautiful animated loading skeleton -->
					<div class="space-y-6 bg-muted/5 p-8 border rounded-2xl animate-pulse">
						<div class="space-y-2">
							<div class="bg-muted rounded w-1/4 h-4"></div>
							<div class="bg-muted rounded w-3/4 h-8"></div>
							<div class="bg-muted rounded w-full h-4"></div>
						</div>
						<div class="gap-4 grid grid-cols-2 md:grid-cols-4">
							{#each Array(4) as _}
								<div class="bg-muted rounded-lg h-16"></div>
							{/each}
						</div>
						<div class="space-y-3 pt-4">
							<div class="bg-muted rounded w-1/2 h-4"></div>
							<div class="bg-muted rounded-xl h-20"></div>
							<div class="bg-muted rounded-xl h-20"></div>
						</div>
					</div>
				{:else if recipe}
					<!-- Custom Generated Recipe Panel -->
					<div class="space-y-6" transition:fade={{ duration: 250 }}>
						<!-- Introduction card -->
						<div class="relative bg-linear-to-r from-emerald-500/5 to-cyan-500/5 shadow-sm p-6 border dark:border-cyan-500/20 rounded-2xl overflow-hidden">
							<div class="top-0 right-0 absolute opacity-10 p-4">
								<Coffee class="w-24 h-24 rotate-12" />
							</div>
							<h2 class="flex items-center gap-2 mb-2 font-bold dark:text-cyan-200 text-xl">
								<span class="inline-block bg-emerald-500/10 p-1.5 rounded-lg">👨‍🔬</span>
								Your Custom Brew Recipe
							</h2>
							<p class="z-10 relative text-muted-foreground text-sm leading-relaxed">
								{recipe.introduction}
							</p>
						</div>

						<!-- Parameters summary -->
						<div class="gap-4 grid grid-cols-2 md:grid-cols-3">
							<div class="bg-background/50 shadow-xs p-3 border rounded-xl">
								<span class="block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Target Dose / Ratio</span>
								<div class="flex items-baseline gap-1 mt-1">
									<span class="font-mono font-bold text-lg">{recipe.parameters.coffee_dose_g}g</span>
									<span class="text-muted-foreground text-xs">({recipe.parameters.water_ratio})</span>
								</div>
							</div>
							<div class="bg-background/50 shadow-xs p-3 border rounded-xl">
								<span class="block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Total Water Weight</span>
								<div class="mt-1 font-mono font-bold text-cyan-600 dark:text-cyan-400 text-lg">
									{recipe.parameters.total_water_g}g
								</div>
							</div>
							<div class="bg-background/50 shadow-xs p-3 border rounded-xl">
								<span class="block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Water Temperature</span>
								<div class="inline-flex items-center gap-1 mt-1 font-bold text-lg">
									<Thermometer class="w-4 h-4 text-red-400" />
									{recipe.parameters.water_temp_c}
								</div>
							</div>
							<div class="col-span-2 md:col-span-1 bg-background/50 shadow-xs p-3 border rounded-xl">
								<span class="block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Grind Click/Setting</span>
								<div class="mt-1 font-bold dark:text-amber-300 text-sm truncate" title={recipe.parameters.grind_size_recommendation}>
									🔑 {recipe.parameters.grind_size_recommendation}
								</div>
							</div>
							<div class="col-span-2 bg-background/50 shadow-xs p-3 border rounded-xl">
								<span class="block font-mono text-[10px] text-muted-foreground uppercase tracking-wider">Filter Paper recommendation</span>
								<div class="mt-1 font-medium text-sm truncate" title={recipe.parameters.filter_paper}>
									📄 {recipe.parameters.filter_paper}
								</div>
							</div>
						</div>

						<!-- Interactive Live Brewer & Timer HUD -->
						<div class="relative bg-linear-to-b from-slate-950/80 to-slate-900/90 shadow-md p-6 border dark:border-cyan-500/30 rounded-2xl text-white">
							<!-- Radial lighting glow -->
							<div class="-top-12 -left-12 absolute bg-cyan-500/10 blur-2xl rounded-full w-32 h-32"></div>

							<div class="z-10 relative flex md:flex-row flex-col justify-between items-center gap-6">
								<!-- Clock display -->
								<div class="md:text-left text-center">
									<span class="font-mono text-[10px] text-cyan-400 uppercase tracking-widest">Live Extraction Scale Timeline</span>
									<div class="mt-1 font-mono font-bold tabular-nums text-5xl tracking-tighter">
										{formatClock(elapsedTime)}
									</div>
								</div>

								<!-- Dynamic Step Status -->
								{#if currentStepId !== null}
									{@const activeStep = recipe.steps.find(s => s.id === currentStepId)}
									{#if activeStep}
										<div class="flex-1 bg-white/5 px-4 py-2.5 border border-white/10 rounded-xl max-w-xs md:text-left text-center">
											<span class="bg-cyan-400/20 px-1.5 py-0.5 rounded font-mono font-bold text-[9px] text-cyan-300 uppercase tracking-wider">Active Pour Step {activeStep.id}</span>
											<h4 class="mt-1.5 font-bold text-cyan-200 text-sm truncate">{activeStep.title}</h4>
											<div class="mt-0.5 text-gray-300 text-xs">
												{#if activeStep.water_pour_g}
													Pour <span class="font-mono font-bold text-cyan-300">{activeStep.water_pour_g}g</span> (Total: <span class="font-mono font-bold">{activeStep.accumulated_water_g}g</span>)
												{:else}
													No pour required (Total: <span class="font-mono font-bold text-cyan-300">{activeStep.accumulated_water_g}g</span>)
												{/if}
											</div>
										</div>
									{/if}
								{:else if elapsedTime > 0}
									<div class="flex flex-1 justify-center items-center gap-2 bg-emerald-500/10 px-4 py-3 border border-emerald-500/30 rounded-xl max-w-xs font-bold text-emerald-300 text-sm text-center">
										<CheckCircle class="w-5 h-5" /> Extraction Finished!
									</div>
								{:else}
									<div class="flex-1 py-2 max-w-sm text-gray-400 text-xs md:text-left text-center">
										Click "Start Brew Session" below to guide your timer flow automatically. Correct step ranges will be marked visually.
									</div>
								{/if}

								<!-- Stopwatch Actions -->
								<div class="flex items-center gap-2 shrink-0">
									<Button class="bg-cyan-500 hover:bg-cyan-400 font-bold text-slate-950" onclick={toggleTimer}>
										{#if isTimerRunning}
											<Pause class="mr-1.5 w-4 h-4" /> Pause
										{:else}
											<Play class="mr-1.5 w-4 h-4" /> Start Brew
										{/if}
									</Button>
									<Button variant="outline" class="hover:bg-white/10 border-white/10 text-white" onclick={resetBrewTracker}>
										<RotateCcw class="w-4 h-4" />
									</Button>
								</div>
							</div>
						</div>

						<!-- Step by step checklists -->
						<div class="space-y-4">
							<h3 class="flex justify-between items-center font-bold dark:text-cyan-100 text-lg">
								<span>Brewing Progression Steps</span>
							</h3>

							<div class="space-y-3">
								{#each recipe.steps as step (step.id)}
									{@const isActive = currentStepId === step.id}
									<div class="border rounded-xl transition-all duration-300 relative overflow-hidden bg-background/50 flex items-start gap-4 p-4
										{isActive ? 'border-primary dark:border-cyan-400 bg-cyan-400/5 shadow-sm scale-[1.01]' : 'border-gray-200 dark:border-gray-800'}
										">

										<!-- Highlight strip for active step -->
										{#if isActive}
											<div class="top-0 bottom-0 left-0 absolute bg-primary dark:bg-cyan-400 w-1"></div>
										{/if}

										<div class="flex-1 space-y-1">
											<div class="flex flex-wrap justify-between items-baseline gap-2">
												<h4 class="flex items-center gap-2 font-bold text-sm">
													<span class="font-mono text-muted-foreground text-xs">Step {step.id}:</span>
													<span class={isActive ? 'text-primary dark:text-cyan-400' : ''}>{step.title}</span>
												</h4>
												<span class="bg-muted px-2 py-0.5 rounded font-mono text-[10px] text-muted-foreground">⏱️ {step.time_range}</span>
											</div>
											<p class="text-muted-foreground text-xs leading-relaxed">
												{step.description}
											</p>

											<!-- Scale Helper metrics -->
											{#if step.water_pour_g || step.accumulated_water_g}
												<div class="flex items-center gap-4 pt-1 font-mono text-[10px] text-muted-foreground">
													{#if step.water_pour_g}
														<span class="flex items-center gap-1">
															<Scale class="w-3 h-3" /> Pour: <strong>+{step.water_pour_g}g</strong>
														</span>
													{/if}
													<span class="flex items-center gap-1">
														🎯 Target Scale: <strong>{step.accumulated_water_g}g</strong>
													</span>
												</div>
											{/if}
										</div>
									</div>
								{/each}
							</div>
						</div>

						<!-- Diagnostic/Troubleshooting adjustments -->
						{#if recipe.adjustments && recipe.adjustments.length > 0}
							<Card class="bg-muted/10 border-dashed">
								<CardHeader class="pb-2">
									<CardTitle class="flex items-center gap-2 font-bold text-sm">
										<Info class="w-4 h-4 text-emerald-500" />
										Interactive Extraction Tuning
									</CardTitle>
									<CardDescription class="text-xs">Adjust your grinder ticks or pacing depending on the outcome of your extraction.</CardDescription>
								</CardHeader>
								<CardContent class="gap-4 grid grid-cols-1 md:grid-cols-2 pb-4">
									{#each recipe.adjustments as adjustment}
										<div class="space-y-1.5 bg-background shadow-2xs p-3 border rounded-xl">
											<span class="inline-block bg-red-100 dark:bg-red-950/40 px-2 py-0.5 rounded-full font-medium text-[10px] text-red-700 dark:text-red-300 uppercase tracking-wider scale-90 -translate-x-1">Anomaly</span>
											<h5 class="font-bold text-xs leading-snug">{adjustment.condition}</h5>
											<p class="mt-1 pt-1.5 border-t border-dashed text-muted-foreground text-xs leading-relaxed">
												👉 {adjustment.action}
											</p>
										</div>
									{/each}
								</CardContent>
							</Card>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	/* Select standard reset styles for Tailwind border-inputs */
	.select-reset {
		appearance: none;
		background-image: url("data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2024%2024'%20fill='none'%20stroke='%23888'%20stroke-width='2'%20stroke-linecap='round'%20stroke-linejoin='round'%3E%3Cpolyline%20points='6%209%2012%2015%2018%209'%3E%3C/polyline%3E%3C/svg%3E");
		background-repeat: no-repeat;
		background-position: right 0.75rem center;
		background-size: 1rem;
		padding-right: 2.25rem;
	}
</style>
