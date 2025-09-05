<script lang="ts">
    import { onMount, tick } from "svelte";
    import { currencyState } from "$lib/stores/currency.svelte.js";
    import { api, type Currency } from "$lib/api.js";
    import { invalidateAll } from "$app/navigation";
    import * as Popover from "$lib/components/ui/popover/index.js";
    import * as Command from "$lib/components/ui/command/index.js";
    import { ChevronDown, Check } from "lucide-svelte";
    // Currency conversion state
    let availableCurrencies: Currency[] = $state([]);
    let currencyLoading = $state(false);
    let open = $state(false);
    let value = $state(currencyState.selectedCurrency || "");

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
    // Load currencies and user preference on mount
    onMount(async () => {
        // Load available currencies
        try {
            currencyLoading = true;
            const response = await api.getCurrencies();
            if (response.success && response.data) {
                availableCurrencies = response.data;
                // If no saved preference, default to EUR if available
                if (
                    !currencyState.selectedCurrency &&
                    availableCurrencies.some((c) => c.code === "EUR")
                ) {
                    currencyState.setCurrency("EUR");
                    value = "EUR";
                } else {
                    value = currencyState.selectedCurrency || "";
                }
            }
        } catch (error) {
            console.error("Failed to load currencies:", error);
        } finally {
            currencyLoading = false;
        }
    });

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
                                class="flex justify-between items-center"
                            >
                                <span>{currency.name}</span>
                                {#if value === currency.code}
                                    <Check class="ml-2 w-4 h-4" />
                                {/if}
                            </Command.Item>
                        {/each}
                    </Command.Group>
                </Command.List>
            </Command.Root>
        </Popover.Content>
    </Popover.Root>