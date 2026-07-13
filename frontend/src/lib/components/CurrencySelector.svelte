<script lang="ts">
    import { currencyState } from "$lib/stores/currency.svelte.js";
    import type { Currency } from "$lib/api.js";
    import { invalidateAll } from "$app/navigation";
    import * as Popover from "$lib/components/ui/popover/index.js";
    import * as Command from "$lib/components/ui/command/index.js";
    import { ChevronDown, Check } from "lucide-svelte";

    let open = $state(false);
    let value = $state(currencyState.selectedCurrency || "");

    // Derive the available currency list from currencyState.rates (already
    // fetched once in the CurrencyState constructor). This avoids a second
    // `api.getCurrencies()` network request from this component's onMount.
    const availableCurrencies: Currency[] = $derived(
        Object.entries(currencyState.rates).map(([code, rate_to_usd]) => ({
            code,
            rate_to_usd,
            name: code
        }))
    );
    // Use a local $state initialized to false so that the Popover.Trigger is
    // enabled during SSR and hydration. This ensures bits-ui successfully
    // binds all popover click/focus event listeners on mount. If the trigger
    // starts as disabled, bits-ui skips event binding, leaving the button
    // permanently dead even after it becomes enabled on the client.
    let currencyLoading = $state(false);

    import { onMount } from "svelte";
    onMount(() => {
        currencyLoading = !currencyState.ratesLoaded;
    });

    $effect(() => {
        currencyLoading = !currencyState.ratesLoaded;
    });

    // Create searchable currency list including "Original" option
    const currencies = $derived.by(() => {
        const allCurrencies = [
            { code: "", name: "Original" },
            ...availableCurrencies.map(c => ({ code: c.code, name: c.code }))
        ];

        // Sort to put selected currency first
        return allCurrencies.sort((a, b) => {
            if (a.code === value) return -1;
            if (b.code === value) return 1;
            return 0;
        });
    });

    // Get display value for the selected currency
    const selectedCurrency = $derived(currencies.find(c => c.code === value));
    const displayValue = $derived(selectedCurrency ? selectedCurrency.name : "Select currency...");

    // Handle currency selection
    function handleCurrencySelect(selectedCode: string) {
        value = selectedCode;
        currencyState.setCurrency(selectedCode);
        open = false;
        invalidateAll(); // Refresh data with new currency
    }
</script>

<!-- Currency Selector -->
    <Popover.Root bind:open>
        <Popover.Trigger
            class="flex justify-between items-center bg-background disabled:opacity-50 shadow-sm px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring ring-offset-background w-fit min-w-[80px] h-9 placeholder:text-muted-foreground text-sm [&>span]:line-clamp-1 whitespace-nowrap disabled:cursor-not-allowed"
            disabled={currencyLoading}
            role="combobox"
            aria-expanded={open}
        >
            <span class="truncate">{displayValue}</span>
            <ChevronDown class="opacity-50 ml-2 w-4 h-4 shrink-0" />
        </Popover.Trigger>
        <Popover.Content class="p-0 w-[120px]" align="start">
            <Command.Root>
                <Command.Input placeholder="Search..." class="h-9" />
                <Command.Empty>No currency found.</Command.Empty>
                <Command.List class="max-h-[240px] overflow-y-scroll no-scrollbar">
                    <Command.Group>
                        {#each currencies as currency}
                            <Command.Item
                                value={currency.code}
                                onSelect={() => handleCurrencySelect(currency.code)}
                                class="flex justify-between items-center group"
                            >
                                <span class="text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black">{currency.name}</span>
                                {#if value === currency.code}
                                    <Check class="ml-2 w-4 h-4 text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black" />
                                {/if}
                            </Command.Item>
                        {/each}
                    </Command.Group>
                </Command.List>
            </Command.Root>
        </Popover.Content>
    </Popover.Root>
