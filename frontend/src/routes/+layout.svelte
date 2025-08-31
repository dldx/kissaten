<script lang="ts">
	import "../app.css";
	import { ModeWatcher, toggleMode } from "mode-watcher";
	import SunIcon from "lucide-svelte/icons/sun";
	import MoonIcon from "lucide-svelte/icons/moon";
	import { Button } from "$lib/components/ui/button/index.js";
	import "@fontsource/knewave";
	import "@fontsource-variable/quicksand";
	import "@fontsource-variable/cabin";
</script>

<ModeWatcher />
<div class="relative flex flex-col min-h-screen">
	<header class="top-0 z-50 sticky bg-background/95 supports-[backdrop-filter]:bg-background/60 backdrop-blur border-b w-full">
		<div class="flex justify-between items-center h-14 container">
			<div class="flex items-center">
				<a class="flex items-center space-x-2 mr-6" href="/">
					<h1 class="font-bold text-xl">☕ Kissaten</h1>
				</a>
				<nav class="hidden md:flex items-center space-x-6 font-medium text-sm">
					<a class="text-foreground/60 hover:text-foreground/80 transition-colors" href="/search">
						Search
					</a>
					<a class="text-foreground/60 hover:text-foreground/80 transition-colors" href="/process">
						Process
					</a>
					<a class="text-foreground/60 hover:text-foreground/80 transition-colors" href="/roasters">
						Roasters
					</a>
					<a class="text-foreground/60 hover:text-foreground/80 transition-colors" href="/countries">
						Countries
					</a>
				</nav>
			</div>
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
