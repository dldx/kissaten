<script lang="ts">
	import "../../app.css";
	import "../../placeholder.css";
	import { page, navigating } from "$app/state";
	import { ModeWatcher, toggleMode } from "mode-watcher";
	import SunIcon from "lucide-svelte/icons/sun";
	import MoonIcon from "lucide-svelte/icons/moon";
	import {
		Citrus,
		Coffee,
		Droplets,
		Leaf,
		MapPin,
		Search,
	} from "lucide-svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import HamburgerMenu from "$lib/components/HamburgerMenu.svelte";
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
	import DownloadIcon from "lucide-svelte/icons/download";
	import { onNavigate } from "$app/navigation";

	let mobileMenuOpen = $state(false);
	let showPwaPrompt = $state(false);

	let { children } = $props();

	// Shared navigation items
	const navigationItems = [
		{ href: "/search", label: "Coffee Beans", icon: Search },
		{ href: "/countries", label: "Origins", icon: MapPin },
		{ href: "/varietals", label: "Varietals", icon: Leaf },
		{ href: "/processes", label: "Processes", icon: Droplets },
		{ href: "/roasters", label: "Roasters", icon: Coffee },
		{ href: "/flavours", label: "Flavours", icon: Citrus },
	];

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
	}

	// onNavigate((navigation) => {
	// 	if (!document.startViewTransition) return;
	// 	// disable if page route remains the same
	// 	if (
	// 		navigation?.from?.route?.id === navigation?.to?.route?.id &&
	// 		navigation?.from?.route?.id?.includes("/search")
	// 	)
	// 		return;

	// 	return new Promise((resolve) => {
	// 		document.startViewTransition(async () => {
	// 			resolve();
	// 			await navigation.complete;
	// 		});
	// 	});
	// });

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

<svelte:head>
	{#if mode.current == "dark"}
		<meta name="theme-color" content="#000012" />
	{:else}
		<meta name="theme-color" content="#fcf5f1" />
	{/if}
</svelte:head>
<ModeWatcher />
<Toaster />
<div class="relative flex flex-col min-h-screen">
	<header
		class="top-0 z-50 sticky bg-background/95 supports-[backdrop-filter]:bg-background/80 backdrop-blur border-b w-full"
		style="view-transition-name: header"
	>
		<div class="flex justify-between items-center h-14 container">
			<div class="flex items-center">
				<!-- Mobile Hamburger Menu Button -->
				<div class="sm:hidden">
					<HamburgerMenu
						isActive={mobileMenuOpen}
						onClick={toggleMobileMenu}
						ariaLabel="Toggle mobile menu"
					/>
				</div>
				<a
					class="flex items-center space-x-2 sm:mx-6"
					href="/"
					onclick={closeMobileMenu}
				>
					<h1
						class="flex flex-1 items-center gap-2 font-bold text-xl"
					>
						<span class="w-8">{@html Logo}</span>
						<span class="relative">
							Kissaten
							<span
								class="top-0 -right-3 absolute rotate-12 transform border-1 border-red-500/50 px-1 rounded-lg font-black text-[0.4rem] text-red-500/80 tracking-widest uppercase"
							>
								Beta
							</span>
						</span>
					</h1>
				</a>
				<!-- Desktop Navigation -->
				<nav
					class="hidden sm:flex items-center space-x-6 font-medium text-sm"
				>
					{#each navigationItems as { href, label, icon: Icon }}
						<a
							class={"flex items-center gap-1.5 hover:text-foreground/80 transition-colors group" +
								(page.url.pathname.includes(href)
									? " font-bold dark:text-cyan-500 text-foreground/80"
									: " text-foreground/60")}
							{href}
						>
							<Icon
								class="hidden lg:block w-4 h-4 group-hover:text-cyan-500 transition-colors"
							/>
							{label}
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

		<!-- Mobile Navigation Menu -->
		{#if mobileMenuOpen}
			<div
				class="sm:hidden bg-background/95 supports-[backdrop-filter]:bg-background/60 backdrop-blur border-t"
			>
				<nav class="py-4 container">
					<div class="flex flex-col space-y-2 px-4">
						{#each navigationItems as { href, label, icon: Icon }}
							<a
								class="group flex items-center gap-2 font-medium text-foreground/60 hover:text-foreground/80 text-sm transition-colors"
								{href}
								onclick={closeMobileMenu}
							>
								<Icon
									class="w-4 h-4 group-hover:text-cyan-500 transition-colors"
								/>
								{label}
							</a>
						{/each}

						{#if pwaState.isInstallable}
							<button
								class="group flex items-center gap-2 font-medium text-foreground/60 hover:text-foreground/80 text-sm transition-colors text-left"
								onclick={() => {
									pwaState.install();
									closeMobileMenu();
								}}
							>
								<DownloadIcon
									class="w-4 h-4 group-hover:text-cyan-500 transition-colors"
								/>
								Install App
							</button>
						{/if}
					</div>
				</nav>
			</div>
		{/if}
	</header>
	<main class="flex-1">
		{@render children()}
	</main>
	<footer class="md:px-8 py-6 md:py-0 border-t">
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
</div>

{#if showPwaPrompt}
	<PWAInstallPrompt onDismiss={() => (showPwaPrompt = false)} />
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
</style>
