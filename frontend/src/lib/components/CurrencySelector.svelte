<script lang="ts">
    import { onMount } from "svelte";
    import { currencyState } from "$lib/stores/currency.svelte.js";
    import { api, type Currency } from "$lib/api.js";
    import { invalidateAll } from "$app/navigation";
    // Currency conversion state
    let availableCurrencies: Currency[] = $state([]);
    let currencyLoading = $state(false);
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
                }
            }
        } catch (error) {
            console.error("Failed to load currencies:", error);
        } finally {
            currencyLoading = false;
        }
    });
    // Save currency preference when changed
    function handleCurrencyChange(event: Event) {
        const target = event.target as HTMLSelectElement;
        currencyState.setCurrency(target.value);
        invalidateAll(); // Refresh data with new currency
    }
</script>

<!-- Currency Selector -->
<div class="hidden sm:block">
    <select
        class="bg-background px-3 py-1 border border-input rounded-md text-sm"
        value={currencyState.selectedCurrency}
        onchange={handleCurrencyChange}
        disabled={currencyLoading}
    >
        <option value="">Original</option>
        {#each availableCurrencies as currency}
            <option value={currency.code}>{currency.code}</option>
        {/each}
    </select>
</div>
