<script lang="ts">
	import "../app.css";
	import "../placeholder.css"
	import { page } from "$app/state";
	import { ModeWatcher, toggleMode } from "mode-watcher";
	import SunIcon from "lucide-svelte/icons/sun";
	import MoonIcon from "lucide-svelte/icons/moon";
	import { Button } from "$lib/components/ui/button/index.js";
	import HamburgerMenu from "$lib/components/HamburgerMenu.svelte";
	import Logo from "$lib/static/logo.svg?raw"
	import "@fontsource/knewave";
	import "@fontsource-variable/quicksand";
	import "@fontsource-variable/cabin";
    import CurrencySelector from "$lib/components/CurrencySelector.svelte";
	import 'iconify-icon';

	let mobileMenuOpen = $state(false);


	// Shared navigation items
	const navigationItems = [
		{ href: "/search", label: "Search" },
		{ href: "/process", label: "Process" },
		{ href: "/varietals", label: "Varietals" },
		{ href: "/roasters", label: "Roasters" },
		{ href: "/countries", label: "Countries" },
		{ href: "/flavours", label: "Flavours" }
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
	<header class="top-0 z-50 sticky bg-background/95 supports-[backdrop-filter]:bg-background/60 backdrop-blur border-b w-full">
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
				<a class="flex items-center space-x-2 sm:mx-6" href="/" onclick={closeMobileMenu}>
					<h1 class="flex flex-1 items-center gap-2 font-bold text-xl"><span class="w-12">{@html Logo}</span> Kissaten</h1>
				</a>
				<!-- Desktop Navigation -->
				<nav class="hidden sm:flex items-center space-x-6 font-medium text-sm">
					{#each navigationItems as { href, label }}
						<a class={"text-foreground/60 hover:text-foreground/80 transition-colors" + (page.url.pathname.includes(href) ? ' font-bold' : '')} {href}>
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

			</div>
		</div>

		<!-- Mobile Navigation Menu -->
		{#if mobileMenuOpen}
			<div class="sm:hidden bg-background/95 supports-[backdrop-filter]:bg-background/60 backdrop-blur border-t">
				<nav class="py-4 container">
					<div class="flex flex-col space-y-2 px-4">
						{#each navigationItems as { href, label }}
							<a
								class="font-medium text-foreground/60 hover:text-foreground/80 text-sm transition-colors"
								{href}
								onclick={closeMobileMenu}
							>
								{label}
							</a>
						{/each}
					</div>
				</nav>
			</div>
		{/if}
	</header>
	<main class="flex-1">
		<slot />
	</main>
	<footer class="md:px-8 py-6 md:py-0 border-t">
		<div class="flex md:flex-row flex-col justify-between items-center gap-4 md:h-24 container">
			<p class="text-muted-foreground text-sm md:text-left text-center text-balance leading-loose">
				Kissaten - Coffee Bean Discovery Platform
			</p>
		</div>
	</footer>
</div>
