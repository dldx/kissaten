<script lang="ts">
	import { Button } from "$lib/components/ui/button";
	import * as Popover from "$lib/components/ui/popover";
	import * as Command from "$lib/components/ui/command";
	import { goto } from "$app/navigation";
	import { Coffee, ClipboardList, QrCode, ChevronDown, Check } from "lucide-svelte";
	import BeanConquerorShareButton from "./BeanConquerorShareButton.svelte";
	import { userSettings } from "$lib/stores/userSettings.svelte";

	interface Props {
		bean: any;
		class?: string;
	}

	let { bean, class: className = "" }: Props = $props();

	type Action = "brew" | "taste" | "beanconqueror";

	const betaEnabled = $derived(userSettings.betaEnabled);

	let selectedAction = $state<Action>("brew");
	let popoverOpen = $state(false);
	let shareBtn = $state<ReturnType<typeof BeanConquerorShareButton> | null>(null);

	const path = $derived(bean?.bean_url_path || "");

	function goBrew() {
		if (path) goto(`/brew-assistant?bean_url_path=${encodeURIComponent(path)}`);
	}
	function goTaste() {
		if (path) goto(`/tasting?bean=${encodeURIComponent(path)}`);
	}
	function openBeanConqueror() {
		shareBtn?.openShareDialog();
	}

	function handlePrimary(e: MouseEvent) {
		e.stopPropagation();
		if (selectedAction === "brew") goBrew();
		else if (selectedAction === "taste") goTaste();
		else openBeanConqueror();
	}

	function choose(action: Action) {
		selectedAction = action;
		popoverOpen = false;
		if (action === "brew") goBrew();
		else if (action === "taste") goTaste();
		else openBeanConqueror();
	}
</script>

{#if betaEnabled}
	<!-- Hidden share button drives its dialog imperatively from this menu -->
	<div class="hidden">
		<BeanConquerorShareButton bind:this={shareBtn} {bean} variant="ghost" size="sm" />
	</div>

	<div
		class="inline-flex items-stretch rounded-md overflow-hidden"
		onclick={(e) => e.stopPropagation()}
	>
		<Button
			variant="ghost"
			size="sm"
			onclick={handlePrimary}
			class="py-1.5 h-7 text-center leading-tight whitespace-normal rounded-r-none {className}"
		>
			{#if selectedAction === "brew"}
				<Coffee class="mr-1 w-3 h-3 shrink-0" />
				<span>Brew</span>
			{:else if selectedAction === "taste"}
				<ClipboardList class="mr-1 w-3 h-3 shrink-0" />
				<span>Taste</span>
			{:else}
				<QrCode class="mr-1 w-3 h-3 shrink-0" />
				<span>BeanConqueror</span>
			{/if}
		</Button>
		<Popover.Root bind:open={popoverOpen}>
			<Popover.Trigger
				class="inline-flex justify-center items-center h-7 px-1.5 rounded-none border-l border-border text-foreground hover:bg-accent dark:hover:bg-cyan-900/20 dark:text-cyan-400 dark:hover:text-cyan-300 transition-colors"
				aria-label="Select action"
				onclick={(e) => e.stopPropagation()}
			>
				<ChevronDown class="opacity-50 w-3 h-3" />
			</Popover.Trigger>
			<Popover.Content class="p-0 w-[200px]" align="end">
				<Command.Root>
					<Command.List class="max-h-[240px] overflow-y-scroll no-scrollbar">
						<Command.Group>
							<Command.Item
								value="brew"
								onSelect={() => choose("brew")}
								class="flex items-center gap-2 group"
							>
								<Coffee
									class="w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black"
								/>
								<span>Brew</span>
								{#if selectedAction === "brew"}
									<Check
										class="ml-auto w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black"
									/>
								{/if}
							</Command.Item>
							<Command.Item
								value="taste"
								onSelect={() => choose("taste")}
								class="flex items-center gap-2 group"
							>
								<ClipboardList
									class="w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black"
								/>
								<span>Taste</span>
								{#if selectedAction === "taste"}
									<Check
										class="ml-auto w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black"
									/>
								{/if}
							</Command.Item>
							<Command.Item
								value="beanconqueror"
								onSelect={() => choose("beanconqueror")}
								class="flex items-center gap-2 group"
							>
								<QrCode
									class="w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black"
								/>
								<span>BeanConqueror</span>
								{#if selectedAction === "beanconqueror"}
									<Check
										class="ml-auto w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black"
									/>
								{/if}
							</Command.Item>
						</Command.Group>
					</Command.List>
				</Command.Root>
			</Popover.Content>
		</Popover.Root>
	</div>
{:else}
	<!-- Beta disabled: only BeanConqueror is available -->
	<BeanConquerorShareButton
		{bean}
		variant="ghost"
		size="sm"
		label="BeanConqueror"
		class={className}
	/>
{/if}
