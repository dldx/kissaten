<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import { Search, Coffee, Globe, TrendingUp } from "lucide-svelte";
	import { goto } from "$app/navigation";

	let searchQuery = $state("");

	function handleSearch() {
		if (searchQuery.trim()) {
			goto(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSearch();
		}
	}
</script>

<svelte:head>
	<title>Kissaten - Coffee Bean Discovery Platform</title>
	<meta name="description" content="Discover and explore coffee beans from roasters worldwide" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Hero Section -->
	<section class="py-16 text-center">
		<h1 class="mb-6 font-bold text-4xl md:text-6xl">
			☕ Kissaten
		</h1>
		<p class="mx-auto mb-8 max-w-2xl text-muted-foreground text-xl md:text-2xl">
			Coffee Bean Discovery Platform
		</p>
		<p class="mx-auto mb-12 max-w-3xl text-muted-foreground text-lg">
			Discover and explore coffee beans from roasters worldwide. Search by origin, tasting notes, processing methods, and more.
		</p>

		<!-- Search Bar -->
		<div class="mx-auto mb-8 max-w-2xl">
			<div class="flex gap-2">
				<div class="relative flex-1">
					<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
					<Input
						bind:value={searchQuery}
						placeholder="Search for beans, roasters, origins, tasting notes..."
						class="pl-10"
						onkeypress={handleKeyPress}
					/>
				</div>
				<Button onclick={handleSearch} size="default">Search</Button>
			</div>
		</div>

		<!-- Quick Actions -->
		<div class="flex flex-wrap justify-center gap-4">
			<Button variant="outline" onclick={() => goto('/roasters')}>
				<Coffee class="mr-2 w-4 h-4" />
				Browse Roasters
			</Button>
			<Button variant="outline" onclick={() => goto('/countries')}>
				<Globe class="mr-2 w-4 h-4" />
				Browse by Country
			</Button>
			<Button variant="outline" onclick={() => goto('/search')}>
				<TrendingUp class="mr-2 w-4 h-4" />
				Advanced Search
			</Button>
		</div>
	</section>

	<!-- Features Section -->
	<section class="py-16">
		<h2 class="mb-12 font-[family-name:var(--font-fun)] font-normal text-3xl text-center">Explore Coffee Beans</h2>
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			<Card>
				<CardHeader>
					<CardTitle class="flex items-center font-[family-name:var(--font-fun)] font-normal">
						<Coffee class="mr-2 w-5 h-5" />
						Browse by Roaster
					</CardTitle>
					<CardDescription>
						Discover coffee beans from your favorite roasters around the world
					</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="mb-4 text-muted-foreground text-sm">
						Explore beans from specialty roasters including A.M.O.C., Cartwheel Coffee, Drop Coffee, and many more.
					</p>
					<Button variant="outline" class="w-full" onclick={() => goto('/roasters')}>
						View All Roasters
					</Button>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle class="flex items-center font-[family-name:var(--font-fun)] font-normal">
						<Globe class="mr-2 w-5 h-5" />
						Browse by Origin
					</CardTitle>
					<CardDescription>
						Find beans from specific countries and regions
					</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="mb-4 text-muted-foreground text-sm">
						Search for beans from Brazil, Colombia, Ethiopia, Guatemala, and other coffee-growing regions.
					</p>
					<Button variant="outline" class="w-full" onclick={() => goto('/countries')}>
						Explore Origins
					</Button>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle class="flex items-center font-[family-name:var(--font-fun)] font-normal">
						<Search class="mr-2 w-5 h-5" />
						Unified Search
					</CardTitle>
					<CardDescription>
						Search across beans, roasters, and tasting notes
					</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="mb-4 text-muted-foreground text-sm">
						Find exactly what you're looking for with our powerful search that covers all aspects of coffee beans.
					</p>
					<Button variant="outline" class="w-full" onclick={() => goto('/search')}>
						Advanced Search
					</Button>
				</CardContent>
			</Card>
		</div>
	</section>
</div>
