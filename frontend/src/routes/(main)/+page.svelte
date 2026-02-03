<script lang="ts">
	import { Coffee, MapPin, Bean, Droplets, Flame, Search, Leaf, ArrowRight, Sparkles, SlidersHorizontal, ArrowDown } from "lucide-svelte";
	import { onMount } from "svelte";
	import SmartSearch from "$lib/components/search/SmartSearch.svelte";
	import CoffeeJourney from "$lib/components/home/CoffeeJourney.svelte";
	import { searchStore } from "$lib/stores/search";
	import type { PageProps } from "./$types";
	import MagnifyingGlass from "virtual:icons/emojione-monotone/magnifying-glass-tilted-left";
	import Logo from "$lib/static/logo.svg?raw";
	import Lenis from 'lenis';
	import HeroCoffeeCup from "$lib/static/hero-coffee-cup.svg?raw";
	import HeroCoffeeBean from "$lib/static/hero-coffee-bean.svg?raw";
	import HeroCoffeeCherry from "$lib/static/hero-coffee-cherry.svg?raw";
	import HeroSteamWisps from "$lib/static/hero-steam-wisps.svg?raw";
	import StatsBean from "$lib/static/stats-bean.svg?raw";
	import StatsRoaster from "$lib/static/stats-roaster.svg?raw";
	import StatsOrigins from "$lib/static/stats-origins.svg?raw";
	import StatsFlavours from "$lib/static/stats-flavours.svg?raw";
	import CoffeeBag from "$lib/static/coffee-bag.svg?raw";
	import FloatingCoffeeBean from "$lib/static/floating-coffee-bean.svg?raw";
	import SolutionIcon from "$lib/static/solution-icon.svg?raw";
	import TraceBeansIcon from "$lib/static/trace-beans-icon.svg?raw";
	import ProcessingMethodsIcon from "$lib/static/processing-methods-icon.svg?raw";
	import VarietalExplorerIcon from "$lib/static/varietal-explorer-icon.svg?raw";
	import Fire from "virtual:icons/mdi/fire";
	import { Button } from "$lib/components/ui/button";

	let { data }: PageProps = $props();

	// Scroll progress
	let scrollProgress = $state(0);

	// Section visibility
	let section1Visible = $state(false);
	let section2Visible = $state(false);
	let section3Visible = $state(false);
	let section4Visible = $state(false);
	let statsVisible = $state(false);

	// Stats counters
	let beansCounted = $state(0);
	let roastersCounted = $state(0);
	let originsCounted = $state(0);
	let flavoursCounted = $state(0);

	// Mouse position for 3D perspective effects
	let mouseX = $state(0);
	let mouseY = $state(0);

	// Animation states
	let heroParallaxY = $state(0);
	let heroRotateX = $state(0);
	let heroRotateY = $state(0);

	// Magnifying glass state
	let magnifierVisible = $state(false);
	let magnifierX = $state(0);
	let magnifierY = $state(0);

	let lenis: Lenis | null = null;

	async function performSmartSearch(query: string) {
		await searchStore.performSmartSearch(query, {
			roasterLocations: data.userDefaults.roasterLocations || [],
		}, {scrollToTop: true});
	}

	async function performImageSearch(image: File) {
		await searchStore.performImageSearch(image, {
			roasterLocations: data.userDefaults.roasterLocations || [],
		});
	}

	onMount(() => {
		searchStore.set({
			...$searchStore,
			smartSearchQuery: "",
		});
		// Initialize Lenis
		lenis = new Lenis({
			duration: 1.2,
			easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
			orientation: "vertical",
			gestureOrientation: "vertical",
			smoothWheel: true,
			wheelMultiplier: 1,
			touchMultiplier: 2,
			infinite: false,
		});

		let rafId: number;
		function raf(time: number) {
			lenis?.raf(time);
			rafId = requestAnimationFrame(raf);
		}
		rafId = requestAnimationFrame(raf);

		// Update vehicle positions based on animation progress
		const updateScrollProgress = () => {
			const scrollTop = window.pageYOffset;
			const docHeight = document.body.scrollHeight - window.innerHeight;
			scrollProgress = Math.min(scrollTop / docHeight, 1);

			// Parallax effect for hero
			heroParallaxY = scrollTop * 0.3;
		};

		const handleMouseMove = (e: MouseEvent) => {
			mouseX = e.clientX;
			mouseY = e.clientY;

			// Calculate rotation based on mouse position relative to center
			const centerX = window.innerWidth / 2;
			const centerY = window.innerHeight / 2;
			heroRotateY = ((e.clientX - centerX) / centerX) * 5;
			heroRotateX = -((e.clientY - centerY) / centerY) * 5;
		};

		const scrollHandler = () => {
			updateScrollProgress();
		};

		// Use Lenis for smooth scroll sync if available, fallback to native scroll
		if (lenis) {
			lenis.on('scroll', scrollHandler);
		} else {
			window.addEventListener("scroll", scrollHandler, { passive: true });
		}
		window.addEventListener("mousemove", handleMouseMove, { passive: true });
		updateScrollProgress();

		const animateCounters = () => {
			const targets = [5000, 150, 45, 200];
			const startTime = performance.now();
			const duration = 2000;

			const animate = (currentTime: number) => {
				const elapsed = currentTime - startTime;
				const progress = Math.min(elapsed / duration, 1);

				beansCounted = Math.floor(targets[0] * progress);
				roastersCounted = Math.floor(targets[1] * progress);
				originsCounted = Math.floor(targets[2] * progress);
				flavoursCounted = Math.floor(targets[3] * progress);

				if (progress < 1) {
					requestAnimationFrame(animate);
				}
			};

			requestAnimationFrame(animate);
		};

		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach(entry => {
					if (entry.isIntersecting) {
						if (entry.target.id === "section-1") section1Visible = true;
						if (entry.target.id === "section-2") section2Visible = true;
						if (entry.target.id === "section-3") section3Visible = true;
						if (entry.target.id === "section-4") section4Visible = true;
						if (entry.target.id === "stats-section") {
							statsVisible = true;
							animateCounters();
						}
					}
				});
			},
			{ threshold: 0.2 }
		);

		document.querySelectorAll(".animate-section").forEach(el => {
			observer.observe(el);
		});

		return () => {
			if (lenis) {
				lenis.off('scroll', scrollHandler);
				lenis.destroy();
			} else {
				window.removeEventListener("scroll", scrollHandler);
			}
			cancelAnimationFrame(rafId);
			window.removeEventListener("mousemove", handleMouseMove);
			observer.disconnect();
		};
	});
</script>

<svelte:head>
	<title>Kissaten - Your Coffee Journey Starts Here</title>
	<meta name="description" content="Discover extraordinary coffee beans from around the world. From farm to cup, explore origins, flavours, and roasters with intelligent search." />
</svelte:head>

<!-- Scroll progress indicator -->
<div
	class="top-0 left-0 z-50 fixed bg-gradient-to-r from-green-600 to-emerald-500 h-1 transition-all duration-300"
	style="width: {scrollProgress * 100}%"
></div>

<!-- Hero Section with 3D perspective -->
<section
	class="relative flex justify-center items-center bg-gradient-to-br from-slate-50 dark:from-slate-900 to-green-50 dark:to-slate-800 min-h-[90vh] md:min-h-screen overflow-hidden"
	style="perspective: 1000px;"
>
	<!-- Animated floating coffee elements with 3D -->
	<div class="absolute inset-0 overflow-hidden pointer-events-none" style="transform: translateY({heroParallaxY}px);">
		<!-- Floating coffee cup -->
		<div
			class="top-20 left-10 absolute opacity-10 transition-transform duration-300"
			style="transform: translateZ(-100px) rotateY({heroRotateY * 0.5}deg) rotateX({heroRotateX * 0.5}deg);"
		>
			{@html HeroCoffeeCup}
		</div>

		<!-- Floating coffee beans -->
		<div
			class="right-20 bottom-32 absolute opacity-10 transition-transform duration-300"
			style="transform: translateZ(-50px) rotateY({-heroRotateY * 0.3}deg) rotateX({-heroRotateX * 0.3}deg);"
		>
			{@html HeroCoffeeBean}
		</div>

		<!-- Floating coffee cherry -->
		<div
			class="top-1/3 right-1/4 absolute opacity-10 transition-transform duration-300"
			style="transform: translateZ(-150px) rotateY({heroRotateY * 0.4}deg) rotateX({heroRotateX * 0.4}deg);"
		>
			{@html HeroCoffeeCherry}
		</div>

		<!-- Floating steam wisps -->
		<div
			class="top-40 right-20 absolute opacity-10 transition-transform duration-300"
			style="transform: translateZ(-80px) rotateY({heroRotateY * 0.2}deg);"
		>
			{@html HeroSteamWisps}
		</div>
	</div>

	<div class="-top-5 z-10 relative mx-auto px-6 container">
		<div
			class="mx-auto max-w-4xl text-center"
			style="transform: rotateY({heroRotateY}deg) rotateX({heroRotateX}deg); transition: transform 0.1s ease-out;"
		>
			<!-- Original logo preserved -->
				<div class="flex items-center mx-auto">
					<h1
						class="flex flex-1 justify-center items-center gap-2 mb-6 font-bold text-4xl md:text-7xl"
					>
						<span class="w-16 md:w-20">{@html Logo}</span>
						<span class="relative">
							Kissaten
							<span
								class="top-0 -right-3 absolute px-1 border border-red-500/50 rounded-lg font-black text-[0.6rem] text-red-500/80 md:text-[1.2rem] uppercase tracking-widest rotate-12 transform"
							>
								Beta
							</span>
						</span>
					</h1>
				</div>
			<p class="mx-auto mb-8 max-w-2xl text-muted-foreground text-lg md:text-2xl">
				Your Coffee Journey Starts Here
			</p>
			<p class="mx-auto max-w-2xl text-md text-slate-500 dark:text-slate-400 md:text-xl">
				Discover extraordinary coffee beans from passionate roasters worldwide
			</p>

			<!-- Smart Search -->
			<div class="my-12">
				<SmartSearch
					bind:value={$searchStore.smartSearchQuery}
					loading={$searchStore.smartSearchLoading}
					available={true}
					onSearch={performSmartSearch}
					onImageSearch={performImageSearch}
					autofocus={true}
					showFilterToggleButton={false}
					userDefaults={data.userDefaults}
					placeholder="Search by origin, flavour, roaster..."
					class="backdrop-blur mx-auto rounded-lg max-w-2xl"
				/>
				<Button variant="link" href="/search#advanced-search">
					<SlidersHorizontal class="mr-2 w-4 h-4" />
					Advanced Search
				</Button>
			</div>

			<!-- CTA Buttons -->
			<div class="flex flex-wrap justify-center gap-4 mt-12">
				<button
					onclick={() => document.getElementById("stats-section")?.scrollIntoView({ behavior: "smooth" })}
					class="flex items-center gap-2 bg-green-600 hover:bg-green-700 shadow-lg hover:shadow-xl px-8 py-3 rounded-full font-medium text-white hover:scale-105 transition-all transition-colors transform"
				>
					Explore the Journey
					<ArrowRight class="w-5 h-5" />
				</button>
				<a
					href="/search"
					class="hover:bg-green-600 shadow hover:shadow-lg px-8 py-3 border-2 border-green-600 rounded-full font-medium text-green-600 hover:text-white dark:text-green-400 hover:scale-105 transition-all transition-all transform"
				>
					Browse All Beans
				</a>
			</div>
		</div>
	</div>

	<!-- Scroll indicator -->
	<div class="bottom-16 left-1/2 absolute -translate-x-1/2 animate-bounce transform">
		<div class="flex justify-center items-center border-2 border-slate-400 dark:border-slate-600 rounded-full w-6 h-10">
			<ArrowDown class="mt-3 w-4 h-4 text-slate-400 dark:text-slate-600" />
		</div>
	</div>
</section>
<!-- Stats Section - MOVED UP -->
<section id="stats-section" class="relative bg-white dark:bg-slate-900 py-20 overflow-hidden animate-section">
	<!-- Background pattern -->
	<div class="absolute inset-0 opacity-5">
		<svg width="100%" height="100%">
			<defs>
				<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
					<circle cx="20" cy="20" r="1" fill="currentColor" class="text-green-600"/>
				</pattern>
			</defs>
			<rect width="100%" height="100%" fill="url(#grid)"/>
		</svg>
	</div>

	<div class="z-10 relative flex flex-col justify-center mx-auto px-6 h-fit min-h-[90vh] md:min-h-screen container">
		<div class={`text-center mb-16 transition-all duration-1000 ${statsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}`}>
			<div class="flex justify-center mb-4">
				<div class="flex justify-center items-center bg-gradient-to-br from-green-100 dark:from-green-900 to-emerald-100 dark:to-emerald-900 rounded-lg w-16 h-16">
					<Sparkles class="w-8 h-8 text-green-600 dark:text-green-400" />
				</div>
			</div>
			<h2 class="mb-4 font-bold text-slate-900 dark:text-white text-4xl md:text-5xl">
				Powered by <span class="bg-clip-text bg-gradient-to-r from-green-600 to-emerald-600 text-transparent">real data</span>
			</h2>
			<p class="mx-auto max-w-2xl text-slate-600 dark:text-slate-300 text-xl">
				We're building the world's most comprehensive coffee bean database
			</p>
		</div>

		<div class="relative mx-auto max-w-6xl">
			<div class="gap-8 grid md:grid-cols-2 lg:grid-cols-4 mb-16">
				<div class={`text-center p-8 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900 dark:to-emerald-900 rounded-lg transition-all duration-1000 ${statsVisible ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-50 translate-y-12'}`} style="transition-delay: 0ms;">
					<div class="relative flex justify-center items-center mx-auto mb-4 w-20 h-20">
						{@html StatsBean}
						<div class="font-bold text-green-700 dark:text-green-400 text-4xl">
							{beansCounted.toLocaleString()}+
						</div>
					</div>
					<div class="mb-1 font-semibold text-slate-800 dark:text-slate-200 text-lg">Coffee Beans</div>
					<div class="text-slate-500 dark:text-slate-400 text-sm">From specialty roasters</div>
				</div>

				<div class={`text-center p-8 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900 dark:to-indigo-900 rounded-lg transition-all duration-1000 ${statsVisible ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-50 translate-y-12'}`} style="transition-delay: 100ms;">
					<div class="relative flex justify-center items-center mx-auto mb-4 w-20 h-20">
						{@html StatsRoaster}
						<div class="font-bold text-blue-700 dark:text-blue-400 text-4xl">
							{roastersCounted.toLocaleString()}+
						</div>
					</div>
					<div class="mb-1 font-semibold text-slate-800 dark:text-slate-200 text-lg">Roasters</div>
					<div class="text-slate-500 dark:text-slate-400 text-sm">Across 20+ countries</div>
				</div>

				<div class={`text-center p-8 bg-gradient-to-br from-emerald-50 to-green-50 dark:from-emerald-900 dark:to-green-900 rounded-lg transition-all duration-1000 ${statsVisible ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-50 translate-y-12'}`} style="transition-delay: 200ms;">
					<div class="relative flex justify-center items-center mx-auto mb-4 w-20 h-20">
						{@html StatsOrigins}
						<div class="font-bold text-emerald-700 dark:text-emerald-400 text-4xl">
							{originsCounted.toLocaleString()}+
						</div>
					</div>
					<div class="mb-1 font-semibold text-slate-800 dark:text-slate-200 text-lg">Origins</div>
					<div class="text-slate-500 dark:text-slate-400 text-sm">Coffee-growing regions</div>
				</div>

				<div class={`text-center p-8 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900 dark:to-pink-900 rounded-lg transition-all duration-1000 ${statsVisible ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-50 translate-y-12'}`} style="transition-delay: 300ms;">
					<div class="relative flex justify-center items-center mx-auto mb-4 w-20 h-20">
						{@html StatsFlavours}
						<div class="font-bold text-purple-700 dark:text-purple-400 text-4xl">
							{flavoursCounted.toLocaleString()}+
						</div>
					</div>
					<div class="mb-1 font-semibold text-slate-800 dark:text-slate-200 text-lg">Flavour Notes</div>
					<div class="text-slate-500 dark:text-slate-400 text-sm">Unique descriptors</div>
				</div>
			</div>
		</div>
	</div>
</section>
<CoffeeJourney {lenis} />

<!-- Section 3: Features -->
<section id="section-3" class="relative flex items-center bg-white dark:bg-slate-900 py-20 min-h-screen overflow-hidden animate-section">
	<!-- Animated background elements -->
	<div class="absolute inset-0 opacity-5 pointer-events-none">
		<svg width="100%" height="100%">
			<defs>
				<pattern id="circles" width="60" height="60" patternUnits="userSpaceOnUse">
					<circle cx="30" cy="30" r="15" fill="none" stroke="currentColor" stroke-width="1" class="text-green-600"/>
				</pattern>
			</defs>
			<rect width="100%" height="100%" fill="url(#circles)"/>
		</svg>
	</div>

	<div class="z-10 relative mx-auto px-6 h-fit min-h-[90vh] md:min-h-screen container">
		<div class={`text-center mb-16 transition-all duration-1000 ${section3Visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}`}>
			<h2 class="mb-4 font-bold text-slate-900 dark:text-white text-4xl md:text-5xl">
				Explore <span class="bg-clip-text bg-gradient-to-r from-green-600 to-emerald-600 text-transparent">every dimension</span>
			</h2>
			<p class="mx-auto max-w-2xl text-slate-600 dark:text-slate-300 text-xl">
				From seed to cup, dig deeper into each step of the journey
			</p>
		</div>

		<div class="relative mx-auto max-w-6xl">
			<!-- Magnifying glass that follows mouse -->
			<div
				class="z-50 fixed transition-opacity duration-200 pointer-events-none"
				class:opacity-0={!magnifierVisible}
				class:opacity-100={magnifierVisible}
				style="left: {magnifierX}px; top: {magnifierY}px; transform: translate(-50%, -50%);"
			>
				<div class="drop-shadow-lg w-16 h-16 text-green-600 dark:text-green-400">
					<MagnifyingGlass class="w-full h-full" />
				</div>
			</div>

			<div
				class={`grid md:grid-cols-3 gap-8 transition-all duration-1000 delay-300 cursor-none ${section3Visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}`}
				role="region"
				onmouseenter={() => magnifierVisible = true}
				onmouseleave={() => magnifierVisible = false}
				onmousemove={(e: MouseEvent) => {
					magnifierX = e.clientX;
					magnifierY = e.clientY;
				}}
			>
				<div
					class="group bg-slate-50 dark:bg-slate-800 hover:shadow-xl p-8 border border-green-500/10 hover:border-green-500/30 rounded-lg hover:scale-105 transition-all"
					style="transform: translateY({section3Visible ? '0' : '30px'}); transition: transform 0.6s ease-out 0ms;"
				>
				<div class="flex justify-center items-center bg-linear-to-br from-orange-100 dark:from-orange-900 to-amber-100 dark:to-amber-900 mb-6 rounded-lg w-16 h-16 group-hover:rotate-12 transition-transform">
					{@html TraceBeansIcon}
					</div>
					<h3 class="mb-3 font-bold text-slate-800 dark:text-slate-200 text-xl">Trace Your Beans</h3>
					<p class="text-slate-600 dark:text-slate-400 leading-relaxed">Explore coffee origins with detailed region information and processing methods</p>
				</div>

				<div
					class="group bg-slate-50 dark:bg-slate-800 hover:shadow-xl p-8 border border-green-500/10 hover:border-green-500/30 rounded-lg hover:scale-105 transition-all"
					style="transform: translateY({section3Visible ? '0' : '30px'}); transition: transform 0.6s ease-out 150ms;"
				>
					<div class="flex justify-center items-center bg-linear-to-br from-green-100 dark:from-green-900 to-emerald-100 dark:to-emerald-900 mb-6 rounded-lg w-16 h-16 group-hover:rotate-12 transition-transform">
					{@html ProcessingMethodsIcon}
					</div>
					<h3 class="mb-3 font-bold text-slate-800 dark:text-slate-200 text-xl">Processing Methods</h3>
					<p class="text-slate-600 dark:text-slate-400 leading-relaxed">Learn about washed, natural, honey, and experimental processing techniques that shape flavor</p>
				</div>

				<div
					class="group bg-slate-50 dark:bg-slate-800 hover:shadow-xl p-8 border border-green-500/10 hover:border-green-500/30 rounded-lg hover:scale-105 transition-all"
					style="transform: translateY({section3Visible ? '0' : '30px'}); transition: transform 0.6s ease-out 300ms;"
				>
					<div class="flex justify-center items-center bg-linear-to-br from-purple-100 dark:from-purple-900 to-pink-100 dark:to-pink-900 mb-6 rounded-lg w-16 h-16 group-hover:rotate-12 transition-transform">
					{@html VarietalExplorerIcon}
					</div>
					<h3 class="mb-3 font-bold text-slate-800 dark:text-slate-200 text-xl">Varietal Explorer</h3>
					<p class="text-slate-600 dark:text-slate-400 leading-relaxed">Discover Bourbon, Geisha, SL28, and hundreds of coffee varieties with detailed profiles</p>
				</div>
			</div>
		</div>
	</div>
</section>



<!-- Section 1: The Problem -->
<section id="section-1" class="relative flex items-center bg-gradient-to-br from-slate-50 dark:from-slate-800 to-red-50 dark:to-slate-900 py-20 min-h-screen overflow-hidden animate-section">
	<!-- 3D perspective container -->
	<div class="absolute inset-0" style="perspective: 1000px;">
		<!-- Floating coffee bag -->
		<div
			class="top-20 right-10 absolute opacity-10 transition-all duration-700"
			class:translate-z-0={section1Visible}
			class:translate-z-neg-100={!section1Visible}
			style="transform: translateZ({section1Visible ? '0px' : '-100px'}) rotateY({section1Visible ? '0deg' : '45deg'});"
		>
			{@html CoffeeBag}
		</div>
	</div>

	<div class="z-10 relative mx-auto px-6 container">
		<div class="items-center gap-16 grid md:grid-cols-2 mx-auto max-w-6xl">
			<div class={`transition-all duration-1000 ${section1Visible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-12'}`}>
				<div class="flex items-center gap-4 mb-6">
					<div class="relative flex justify-center items-center bg-red-100 dark:bg-red-900 rounded-2xl w-16 h-16 overflow-hidden">
						<div class="absolute inset-0 bg-gradient-to-br from-red-500 to-orange-500 opacity-20"></div>
						<Search class="relative w-8 h-8 text-red-600 dark:text-red-400" />
					</div>
					<span class="font-semibold text-red-600 dark:text-red-400 text-lg">The Challenge</span>
				</div>
				<h2 class="mb-6 font-bold text-slate-900 dark:text-white text-4xl md:text-5xl">
					Lost in a sea<br/>
					<span class="bg-clip-text bg-gradient-to-r from-red-500 to-orange-500 text-transparent">of coffee choices?</span>
				</h2>
				<p class="mb-6 text-slate-600 dark:text-slate-300 text-xl leading-relaxed">
					Every day, 2.25 billion cups of coffee are consumed worldwide. With thousands of roasters and varietals, finding your perfect bean feels overwhelming.
				</p>
				<p class="mb-8 text-slate-500 dark:text-slate-400 text-lg leading-relaxed">
					You shouldn't need a degree in coffee to find what you love.
				</p>
			</div>
			<div class={`order-2 md:order-2 transition-all duration-1000 delay-300 ${section1Visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`} style="perspective: 1000px;">
				<div class="relative" style="transform: rotateY({section1Visible ? '0deg' : '15deg'}) rotateX({section1Visible ? '0deg' : '5deg'}); transition: transform 0.8s ease-out;">
					<div class="top-10 left-10 -z-10 absolute bg-gradient-to-br from-red-100 dark:from-red-900 to-orange-100 dark:to-orange-900 opacity-50 rounded-lg w-full h-full rotate-3 transform"></div>
					<div class="bg-white dark:bg-slate-800 shadow-xl p-8 border border-green-500/10 rounded-lg">
						<div class="flex flex-row flex-wrap gap-4">
							{#each ['Ethiopian Heirloom', 'Colombian Pink Bourbon', 'Panama Geisha', 'Kenyan SL34', 'Peruvian Inca Geisha', 'Brazilian Red Catuai', 'Sudan Rume'] as coffee, i}
							<button
							class="cursor-pointer"
											onclick={() => performSmartSearch(coffee)}>
								<div
									class="flex justify-between items-center bg-gradient-to-r from-slate-50 dark:from-slate-700 to-orange-50 dark:to-orange-900 p-3 rounded-lg transition-all hover:translate-x-2"
									style="transform: translateX({section1Visible ? '0' : `${(i % 2 === 0 ? -1 : 1) * 20}px`}); transition: transform 0.5s ease-out {i * 50}ms;"
								>
									<div class="flex items-center gap-3">
										<div class="flex justify-center items-center bg-gradient-to-br from-red-400 to-orange-500 rounded-full w-8 h-8 font-bold text-white text-xs">
											{i + 1}
										</div>
										<div
											class="bg-transparent m-0 p-0 border-none rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-green-500 font-medium text-slate-800 dark:text-slate-200"
										>
											{coffee}
										</div>
									</div>
								</div>
								</button>
							{/each}
						</div>
						<div class="mt-6 pt-6 border-slate-200 dark:border-slate-600 border-t">
							<div class="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
								<div class="flex justify-center items-center bg-gradient-to-r from-orange-400 to-red-500 rounded-full w-6 h-6 text-white text-xs">+</div>
								<span>And 5000+ more options...</span>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</section>

<!-- Section 2: The Solution -->
<section id="section-2" class="relative flex items-center bg-gradient-to-br from-green-50 dark:from-slate-900 to-emerald-50 dark:to-slate-800 py-20 min-h-screen overflow-hidden animate-section">
	<!-- 3D floating elements -->
	<div class="absolute inset-0 pointer-events-none" style="perspective: 1000px;">
		{#each [0, 1, 2, 3] as index}
			<div
				class="absolute transition-all duration-1000"
				class:opacity-50={section2Visible}
				class:opacity-0={!section2Visible}
				style="top: {index * 25}%; left: {index * 20 + 10}%; transform: translateZ({section2Visible ? '0' : '-200'}px) rotateY({section2Visible ? '0' : '90'}deg) rotate({index * 45}deg); transition: all 1s ease-out {index * 200}ms;"
			>
			{@html FloatingCoffeeBean}
			</div>
		{/each}
	</div>

	<div class="z-10 relative mx-auto px-6 container">
		<div class="items-center gap-16 grid md:grid-cols-2 mx-auto max-w-6xl">
			<div class={`order-2 md:order-1 transition-all duration-1000 delay-300 ${section2Visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`} style="perspective: 1000px;">
				<div class="gap-4 grid grid-cols-2" style="transform: rotateY({section2Visible ? '0deg' : '-10deg'}) rotateX({section2Visible ? '0deg' : '5deg'}); transition: transform 0.8s ease-out;">
					<div class="space-y-4">
						<a href="#smart-search-input">
						<div
							class="bg-white dark:bg-slate-800 shadow-lg my-2 p-4 border border-green-500/10 rounded-lg hover:scale-105 transition-transform transform"
							style="transform: translateY({section2Visible ? '0' : '20px'}); transition: transform 0.6s ease-out 0ms;"
						>
							<div class="flex justify-center items-center bg-gradient-to-r from-blue-500 to-purple-600 mb-2 rounded-lg w-10 h-10 text-white">
								<Sparkles class="w-5 h-5" />
							</div>
							<p class="font-semibold text-slate-800 dark:text-slate-200 text-sm">Smart Search</p>
						</div>
						</a>
						<a href="/origins">
						<div
							class="bg-white dark:bg-slate-800 shadow-lg p-4 border border-green-500/10 rounded-lg hover:scale-105 transition-transform transform"
							style="transform: translateY({section2Visible ? '0' : '30px'}); transition: transform 0.6s ease-out 100ms;"
						>
							<div class="flex justify-center items-center bg-gradient-to-r from-green-500 to-emerald-600 mb-2 rounded-lg w-10 h-10 text-white">
								<MapPin class="w-5 h-5" />
							</div>
							<p class="font-semibold text-slate-800 dark:text-slate-200 text-sm">Origin Explorer</p>
						</div>
						</a>
					</div>
					<div class="space-y-4 mt-8">
						<a
							href="/roasters">
						<div
							class="bg-white dark:bg-slate-800 shadow-lg my-2 p-4 border border-green-500/10 rounded-lg hover:scale-105 transition-transform transform"
							style="transform: translateY({section2Visible ? '0' : '40px'}); transition: transform 0.6s ease-out 200ms;"
						>
							<div class="flex justify-center items-center bg-gradient-to-r from-orange-500 to-red-600 mb-2 rounded-lg w-10 h-10 text-white">
								<Fire class="w-5 h-5" />
							</div>
							<p class="font-semibold text-slate-800 dark:text-slate-200 text-sm">Roaster Discovery</p>
						</div>
						</a>
						<a
							href="/varietals">
							<div
							class="bg-white dark:bg-slate-800 shadow-lg p-4 border border-green-500/10 rounded-lg hover:scale-105 transition-transform transform"
							style="transform: translateY({section2Visible ? '0' : '50px'}); transition: transform 0.6s ease-out 300ms;"
						>
							<div class="flex justify-center items-center bg-gradient-to-r from-purple-500 to-pink-600 mb-2 rounded-lg w-10 h-10 text-white">
								<Leaf class="w-5 h-5" />
							</div>
							<p class="font-semibold text-slate-800 dark:text-slate-200 text-sm">Varietal Insights</p>
							</div>
						</a>
					</div>
				</div>
			</div>
			<div class={`order-1 md:order-2 transition-all duration-1000 ${section2Visible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-12'}`}>
				<div class="mb-6">
					<div class="flex items-center gap-4">
						<div class="relative flex justify-center items-center bg-blue-100 dark:bg-blue-900 rounded-2xl w-16 h-16 overflow-hidden">
							<div class="absolute inset-0 bg-gradient-to-br from-blue-500 to-purple-600 opacity-20"></div>
							{@html SolutionIcon}
						</div>
						<span class="font-semibold text-blue-600 dark:text-blue-400 text-lg">The Solution</span>
					</div>
				</div>
				<h2 class="mb-6 font-bold text-slate-900 dark:text-white text-4xl md:text-5xl">
					Intelligent Coffee<br/>
					<span class="bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 text-transparent">Discovery</span>
				</h2>
				<p class="mb-6 text-slate-600 dark:text-slate-300 text-xl leading-relaxed">
					Kissaten transforms how you discover coffee. Our smart search understands natural language, so you can search like you think.
				</p>
				<p class="bg-white/50 dark:bg-slate-800/50 mb-8 p-4 border-green-500 border-l-4 rounded-lg text-slate-500 dark:text-slate-400 text-lg leading-relaxed">
					"I want a bright, fruity Ethiopian with floral notes" <Button class="mt-2" onclick={() => performSmartSearch("I want a bright, fruity Ethiopian with floral notes")} >Find it instantly.</Button>
				</p>
			</div>
		</div>
	</div>
</section>



<!-- Section 4: Call to Action -->
<section id="section-4" class="relative flex justify-center items-center bg-gradient-to-br from-green-50 dark:from-slate-800 to-emerald-50 dark:to-slate-900 py-20 min-h-screen overflow-hidden animate-section">

	<div class="z-10 relative mx-auto px-6 container">
		<div class={`max-w-3xl mx-auto text-center transition-all duration-1000 ${section4Visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}>
			<div
				class="flex justify-center items-center bg-gradient-to-r from-green-500 to-emerald-600 mx-auto mb-8 rounded-lg w-24 h-24 hover:rotate-12 transition-all duration-500 transform"
				style="transform: scale({section4Visible ? '1' : '0.8'}) rotate({section4Visible ? '0' : '-10'}deg); transition: transform 0.8s ease-out;"
			>
			<Coffee class="w-12 h-12 text-white" />
			</div>
			<h2 class="mb-6 font-bold text-slate-900 dark:text-white text-4xl md:text-6xl">
				Ready to discover<br/>
				<span class="bg-clip-text bg-gradient-to-r from-green-600 to-emerald-600 text-transparent">your next cup?</span>
			</h2>

			<div class="flex flex-wrap justify-center gap-4 mb-8">
				<a
					href="/search"
					class="flex items-center gap-2 bg-green-600 hover:bg-green-700 shadow-lg hover:shadow-xl px-10 py-4 rounded-full font-semibold text-white text-lg hover:scale-105 transition-all transform"
				>
					<span class="hidden sm:inline">Start Your </span>Journey
					<ArrowRight class="w-5 h-5" />
				</a>
				<a
					href="/origins"
					class="hover:bg-green-600 shadow hover:shadow-lg px-10 py-4 border-2 border-green-600 rounded-full font-semibold text-green-600 hover:text-white dark:text-green-400 text-lg transition-all"
				>
					Explore Origins
				</a>
			</div>

			<p class="flex justify-center items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
				<span class="bg-green-500 rounded-full w-2 h-2 animate-pulse"></span>
				Free to use • Open data • Growing daily
			</p>
		</div>
	</div>
</section>

<style>
	.animate-section {
		scroll-margin-top: 2rem;
	}

	@media (prefers-reduced-motion: reduce) {
		* {
			animation-duration: 0.01ms !important;
			animation-iteration-count: 1 !important;
			transition-duration: 0.01ms !important;
		}
	}
</style>
