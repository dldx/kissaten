<script lang="ts">
	import "../../app.css";
	import "../../placeholder.css";
	import { page, navigating } from "$app/state";
	import { ModeWatcher, toggleMode } from "mode-watcher";
	import SunIcon from "lucide-svelte/icons/sun";
	import MoonIcon from "lucide-svelte/icons/moon";
	import { Citrus, Droplets, Leaf, MapPin, Search } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import Logo from "$lib/static/logo.svg?raw";
	import "@fontsource/knewave";
	import "@fontsource-variable/quicksand";
	import "@fontsource-variable/cabin";
	import CurrencySelector from "$lib/components/CurrencySelector.svelte";
	import AuthStatusButton from "$lib/components/AuthStatusButton.svelte";
	import "iconify-icon";
	import { Toaster } from "$lib/components/ui/sonner/index.js";
	import { pwaState } from "$lib/pwa-install.svelte";
	import PWAInstallPrompt from "$lib/components/PWAInstallPrompt.svelte";
	import LoadingSpinner from "$lib/components/LoadingSpinner.svelte";
	import Fire from "virtual:icons/mdi/fire";
	import { onNavigate } from "$app/navigation";
	import { smartSearchLoader } from "$lib/stores/smartSearchLoader.svelte";
	import { browser } from "$app/environment";
	import { cn } from "$lib/utils.js";

	let showPwaPrompt = $state(false);
	let scrollY = $state(0);
	let lastScrollY = 0;
	let headerVisible = $state(true);
	let showLoader = $state(false);
	let loadingMessage = $state("");

	const coffeeLoadingMessages = [
		"Planting the seedlings...",
		"Sorting out the quakers...",
		"Picking the cherries...",
		"Grinding the beans...",
		"Milking the oats...",
		"Frothing the milk...",
		"Brewing some soup...",
	];

	// Global error handler for unhandled promise rejections
	if (browser) {
		window.addEventListener("unhandledrejection", (event) => {
			console.error("Unhandled Promise Rejection:", event.reason);
		});
	}

	// Show loader with delay for navigation or immediately for SmartSearch
	$effect(() => {
		if (navigating?.to) {
			loadingMessage =
				coffeeLoadingMessages[
					Math.floor(Math.random() * coffeeLoadingMessages.length)
				];

			const timer = setTimeout(() => {
				showLoader = true;
			}, 500);

			return () => {
				clearTimeout(timer);
				showLoader = false;
			};
		} else if (smartSearchLoader.isLoading) {
			loadingMessage =
				coffeeLoadingMessages[
					Math.floor(Math.random() * coffeeLoadingMessages.length)
				];
			showLoader = true;
		} else {
			showLoader = false;
		}
	});

	$effect(() => {
		const currentScrollY = scrollY;
		if (currentScrollY > 50) {
			if (currentScrollY > lastScrollY) {
				// Scrolling down
				headerVisible = false;
			} else {
				// Scrolling up
				headerVisible = true;
			}
		} else {
			headerVisible = true;
		}
		lastScrollY = currentScrollY;
	});

	let { children } = $props();

	// Shared navigation items
	const navigationItems = [
		{ href: "/search", label: "Beans", icon: Search },
		{ href: "/origins", label: "Origins", icon: MapPin },
		{ href: "/varietals", label: "Varietals", icon: Leaf },
		{ href: "/processes", label: "Processes", icon: Droplets },
		{ href: "/roasters", label: "Roasters", icon: Fire },
		{ href: "/flavours", label: "Flavours", icon: Citrus },
	];

	onNavigate((navigation) => {
		if (!document.startViewTransition) return;
		// disable if page route remains the same
		if (
			navigation?.from?.route?.id === navigation?.to?.route?.id &&
			navigation?.from?.route?.id?.includes("/search")
		)
			return;

		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});

	$effect(() => {
		if (pwaState.isInstallable && !pwaState.isRejected) {
			showPwaPrompt = true;
		}
	});

	import { mode } from "mode-watcher";

	import { loadIcons } from "iconify-icon";
	// Preload country flag icons
	loadIcons([
		"circle-flags:co",
		"circle-flags:et",
		"circle-flags:pa",
		"circle-flags:ke",
		"circle-flags:br",
		"circle-flags:cr",
		"circle-flags:gt",
		"circle-flags:in",
		"circle-flags:pe",
		"circle-flags:hn",
		"circle-flags:ec",
		"circle-flags:sv",
		"circle-flags:id",
		"circle-flags:rw",
		"circle-flags:mx",
		"circle-flags:ni",
		"circle-flags:ug",
		"circle-flags:cn",
		"circle-flags:tz",
		"circle-flags:bi",
		"circle-flags:bo",
		"circle-flags:ye",
		"circle-flags:vn",
		"circle-flags:mm",
		"circle-flags:pg",
		"circle-flags:tw",
		"circle-flags:jp",
		"circle-flags:gb",
		"circle-flags:us",
		"circle-flags:zm",
		"circle-flags:de",
		"circle-flags:cd",
		"circle-flags:tl",
		"circle-flags:th",
		"circle-flags:my",
		"circle-flags:do",
		"circle-flags:mg",
		"circle-flags:fj",
		"circle-flags:la",
		"circle-flags:ph",
		"circle-flags:cl",
		"circle-flags:za",
		"circle-flags:jm",
		"circle-flags:es",
	]);
</script>

<svelte:window bind:scrollY />
<svelte:head>
	{#if mode.current == "dark"}
		<meta name="theme-color" content="#0a0b1f" />
	{:else}
		<meta name="theme-color" content="#faf6f3" />
	{/if}
</svelte:head>
<ModeWatcher />
<Toaster />
<div class="relative flex flex-col min-h-screen">
	<header
		class={"top-0 z-50 sticky bg-background/95 supports-[backdrop-filter]:bg-background/80 backdrop-blur border-b w-full transition-transform duration-300 " +
			(headerVisible
				? "translate-y-0"
				: "-translate-y-full sm:translate-y-0")}
		style="view-transition-name: header"
	>
		<div class="flex justify-between items-center h-14 container">
			<div class="flex items-center">
				<a class="flex items-center space-x-2 sm:mx-6" href="/">
					<h1
						class="flex flex-1 items-center gap-2 font-bold text-xl"
					>
						<span class="w-8">{@html Logo}</span>
						<span class="relative">
							Kissaten
							<span
								class="top-0 -right-3 absolute px-1 border border-red-500/50 rounded-lg font-black text-[0.4rem] text-red-500/80 uppercase tracking-widest rotate-12 transform"
							>
								Beta
							</span>
						</span>
					</h1>
				</a>
				<!-- Desktop Navigation -->
				<nav
					class="hidden sm:flex relative items-center font-medium text-sm p-1"
				>
					<div class="bubble active"></div>
					<div class="bubble hover"></div>
					{#each navigationItems as { href, label, icon: Icon }}
						<a
							class={cn(
								"nav-link flex items-center gap-1.5 px-3 py-1.5 transition-all group",
								page.url.pathname.includes(href)
									? "active text-primary-foreground"
									: "text-muted-foreground hover:text-foreground",
							)}
							{href}
						>
							<Icon class="hidden lg:block w-4 h-4" />
							<span>{label}</span>
						</a>
					{/each}
				</nav>
			</div>

			<div class="flex items-center space-x-2 pr-2">
				<CurrencySelector />
				<!-- Theme Toggle Button -->
				<Button onclick={toggleMode} variant="outline" size="icon">
					<SunIcon
						class="w-[1.2rem] h-[1.2rem] rotate-0 dark:-rotate-90 scale-100 dark:scale-0 transition-all"
					/>
					<MoonIcon
						class="absolute w-[1.2rem] h-[1.2rem] rotate-90 dark:rotate-0 scale-0 dark:scale-100 transition-all"
					/>
					<span class="sr-only">Toggle theme</span>
				</Button>
				<!-- Auth Status Button -->
				<AuthStatusButton />
			</div>
		</div>
	</header>
	<main class="flex-1 pb-20 sm:pb-0">
		{#key page.url.pathname}
			{@render children()}
		{/key}
	</main>
	<footer class="mb-16 sm:mb-0 md:px-8 py-6 md:py-0 border-t">
		<div
			class="flex md:flex-row flex-col justify-center items-center gap-4 md:h-24 text-muted-foreground text-sm text-center text-balance leading-loose container"
		>
			<p class="text-center">
				Kissaten is an open data project by <a
					target="_blank"
					class="font-semibold hover:underline"
					href="https://github.com/dldx">Durand D'souza</a
				>.
			</p>
			<p>
				If you spot any errors, please file an issue on our <a
					target="_blank"
					class="hover:underline"
					href="https://github.com/dldx/kissaten/issues"
					>GitHub repository</a
				>.
			</p>
		</div>
	</footer>

	<!-- Mobile Bottom Toolbar -->
	<div
		class="sm:hidden right-0 bottom-0 left-0 z-50 fixed bg-background/95 supports-backdrop-filter:bg-background/80 backdrop-blur pb-safe border-t"
		style="view-transition-name: header-mobile"
	>
		<nav
			class="flex justify-around items-center container relative p-1 dark:p-0"
		>
			<div class="bubble active"></div>
			<div class="bubble hover"></div>
			{#each navigationItems as { href, label, icon: Icon }}
				<a
					class={cn(
						"nav-link flex flex-col items-center justify-center p-2 rounded-md transition-all w-full relative z-10",
						page.url.pathname.includes(href)
							? "active text-primary-foreground"
							: "text-muted-foreground hover:text-foreground",
					)}
					{href}
				>
					<Icon class="mb-1 w-5 h-5" />
					<span class="font-medium text-[0.65rem] text-center"
						>{label}</span
					>
				</a>
			{/each}
		</nav>
	</div>
</div>

{#if showPwaPrompt}
	<PWAInstallPrompt onDismiss={() => (showPwaPrompt = false)} />
{/if}

{#if showLoader}
	<div
		class="z-50 fixed inset-0 flex justify-center items-center bg-background/80 backdrop-blur-sm"
	>
		<div class="flex flex-col items-center gap-4">
			<LoadingSpinner />
			<p class="text-muted-foreground text-sm">{loadingMessage}</p>
		</div>
	</div>
{/if}

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
		}
	}

	@keyframes fade-out {
		to {
			opacity: 0;
		}
	}

	@keyframes slide-from-right {
		from {
			transform: translateX(60px);
		}
	}

	@keyframes slide-to-left {
		to {
			transform: translateX(-30px);
		}
	}

	:root::view-transition-old(root) {
		animation:
			90ms cubic-bezier(0.4, 0, 1, 1) both fade-out,
			300ms cubic-bezier(0.4, 0, 0.2, 1) both slide-to-left;
	}

	:root::view-transition-new(root) {
		animation:
			210ms cubic-bezier(0, 0, 0.2, 1) 90ms both fade-in,
			300ms cubic-bezier(0.4, 0, 0.2, 1) both slide-from-right;
	}
	@media (prefers-reduced-motion) {
		::view-transition-group(*),
		::view-transition-old(*),
		::view-transition-new(*) {
			animation: none !important;
		}
	}

	.nav-link {
		position: relative;
		z-index: 10;
	}

	.nav-link:hover {
		anchor-name: --nav-hover;
	}

	.nav-link.active {
		anchor-name: --nav-active;
	}

	.bubble {
		position: absolute;
		transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
		border-radius: var(--radius-sm);
		pointer-events: none;
		inset: anchor(top) anchor(right) anchor(bottom) anchor(left);
	}

	.bubble.active {
		position-anchor: --nav-active;
		z-index: 2;
		background: var(--color-primary);
	}

	.bubble.hover {
		z-index: 1;
		background: var(--color-accent);
		position-anchor: --nav-hover;
		opacity: 0;
	}

	nav:has(.nav-link:hover) .bubble.hover {
		opacity: 0.15;
	}
</style>
