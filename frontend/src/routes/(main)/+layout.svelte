<script lang="ts">
	import "../../app.css";
	import "../../placeholder.css";
	import { page } from "$app/state";
	import { ModeWatcher, toggleMode } from "mode-watcher";
	import SunIcon from "lucide-svelte/icons/sun";
	import MoonIcon from "lucide-svelte/icons/moon";
	import { Citrus, Coffee, Droplets, Leaf, MapPin, Search } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import HamburgerMenu from "$lib/components/HamburgerMenu.svelte";
	import Logo from "$lib/static/logo-alt.svg?raw";
	import "@fontsource/knewave";
	import "@fontsource-variable/quicksand";
	import "@fontsource-variable/cabin";
	import CurrencySelector from "$lib/components/CurrencySelector.svelte";
	import AuthStatusButton from "$lib/components/AuthStatusButton.svelte";
	import "iconify-icon";
	import { CheckIcon } from "lucide-svelte";

	let mobileMenuOpen = $state(false);

	let { children } = $props();

	// Shared navigation items
	const navigationItems = [
		{ href: "/search", label: "Coffee Beans", icon: Search },
		{ href: "/countries", label: "Origins", icon: MapPin },
		{ href: "/varietals", label: "Varietals", icon: Leaf },
		{ href: "/process", label: "Processes", icon: Droplets },
		{ href: "/roasters", label: "Roasters", icon: Coffee },
		{ href: "/flavours", label: "Flavours", icon: Citrus },
	];

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
	}
</script>

<ModeWatcher />
<div class="relative flex flex-col min-h-screen">
	<header
		class="top-0 z-50 sticky bg-background/95 supports-[backdrop-filter]:bg-background/60 backdrop-blur border-b w-full"
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
						<span class="w-8">{@html Logo}</span> Kissaten
					</h1>
				</a>
				<!-- Desktop Navigation -->
				<nav
					class="hidden sm:flex items-center space-x-6 font-medium text-sm"
				>
					{#each navigationItems as { href, label, icon: Icon }}
						<a
							class={"flex items-center gap-1.5 text-foreground/60 hover:text-foreground/80 transition-colors group" +
								(page.url.pathname.includes(href)
									? " font-bold"
									: "")}
							{href}
						>
							<Icon class="hidden lg:block w-4 h-4 group-hover:text-cyan-500 transition-colors" />
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
								<Icon class="w-4 h-4 group-hover:text-cyan-500 transition-colors" />
								{label}
							</a>
						{/each}
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
