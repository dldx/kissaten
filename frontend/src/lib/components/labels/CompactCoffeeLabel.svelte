<script lang="ts">
	import type { CoffeeBean } from "$lib/api";
	import { api } from "$lib/api";
	import "iconify-icon";
	import { MapPin, Droplets, Thermometer, User } from "lucide-svelte";

	interface Props {
		bean: CoffeeBean;
		width?: string;
		height?: string;
	}

	let { bean, width = "100%", height = "100%" }: Props = $props();

	const originDisplay = $derived(api.getOriginDisplayString(bean));
	const processes = $derived(api.getBeanProcesses(bean));
	const roaster = $derived(bean.roaster);
    const name = $derived(bean.name);
</script>

<div
    class="flex flex-col justify-between bg-white p-2 overflow-hidden text-black label-container"
    style:width={width}
    style:height={height}
>
    <div>
        <div class="mb-0.5 font-bold text-[10px] text-gray-500 uppercase tracking-wider">{roaster}</div>
        <div class="font-bold text-xs line-clamp-2 leading-tight">{name}</div>
    </div>

    <div class="space-y-0.5 mt-1">
        {#if originDisplay}
            <div class="flex items-center gap-1 text-[9px]">
                <MapPin size={8} class="flex-shrink-0" />
                <span class="truncate">{originDisplay}</span>
            </div>
        {/if}

        {#if processes && processes.length > 0}
            <div class="flex items-center gap-1 text-[9px]">
                <Droplets size={8} class="flex-shrink-0" />
                <span class="truncate">{processes.join(", ")}</span>
            </div>
        {/if}

        {#if bean.roast_level}
             <div class="flex items-center gap-1 text-[9px]">
                <Thermometer size={8} class="flex-shrink-0" />
                <span class="truncate">{bean.roast_level}</span>
            </div>
        {/if}
    </div>
</div>

<style>
    .label-container {
        font-family: 'Inter', sans-serif;
        box-sizing: border-box;
    }
</style>
