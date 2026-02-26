<script lang="ts">
    import type { Component } from "svelte";
    import "iconify-icon";

    interface InsightItem {
        label: string;
        count: number | string;
        href: string;
        icon?: Component;
        countryCode?: string;
    }

    interface Props {
        title: string;
        icon: Component;
        items: InsightItem[];
        variant?: "blue" | "orange" | "purple" | "green";
        unit?: string;
        pluralUnit?: string;
    }

    let {
        title,
        icon: Icon,
        items,
        variant = "blue",
        unit = "bean",
        pluralUnit = "beans",
    }: Props = $props();

    const variants = {
        blue: {
            card: "bg-blue-50 border-blue-200 dark:border-cyan-500/30 dark:bg-slate-800/60 dark:shadow-[0_0_10px_rgba(34,211,238,0.3)]",
            title: "text-blue-600 dark:text-cyan-400",
            titleText: "text-blue-900 dark:text-cyan-200",
            itemLabel: "text-blue-800 dark:text-cyan-300",
            itemCount: "text-blue-900 dark:text-cyan-200",
            iconShadow: "dark:drop-shadow-[0_0_6px_rgba(34,211,238,0.8)]",
        },
        orange: {
            card: "bg-orange-50 border-orange-200 dark:border-orange-500/30 dark:bg-slate-800/60 dark:shadow-[0_0_10px_rgba(249,115,22,0.3)]",
            title: "text-orange-600 dark:text-orange-400",
            titleText: "text-orange-900 dark:text-orange-200",
            itemLabel: "text-orange-800 dark:text-orange-300",
            itemCount: "text-orange-900 dark:text-orange-200",
            iconShadow: "dark:drop-shadow-[0_0_6px_rgba(249,115,22,0.8)]",
        },
        purple: {
            card: "bg-purple-50 border-purple-200 dark:border-purple-500/30 dark:bg-slate-800/60 dark:shadow-[0_0_10px_rgba(168,85,247,0.3)]",
            title: "text-purple-600 dark:text-purple-400",
            titleText: "text-purple-900 dark:text-purple-200",
            itemLabel: "text-purple-800 dark:text-purple-300",
            itemCount: "text-purple-900 dark:text-purple-200",
            iconShadow: "dark:drop-shadow-[0_0_6px_rgba(168,85,247,0.8)]",
        },
        green: {
            card: "bg-green-50 border-green-200 dark:border-emerald-500/30 dark:bg-slate-800/60 dark:shadow-[0_0_10px_rgba(16,185,129,0.3)]",
            title: "text-green-600 dark:text-emerald-400",
            titleText: "text-green-900 dark:text-emerald-200",
            itemLabel: "text-green-800 dark:text-emerald-300",
            itemCount: "text-green-900 dark:text-emerald-200",
            iconShadow: "dark:drop-shadow-[0_0_6px_rgba(16,185,129,0.8)]",
        },
    };

    const style = $derived(variants[variant]);
</script>

<div class={`p-6 border rounded-lg transition-all ${style.card}`}>
    <div class={`flex items-center gap-2 mb-4 ${style.title}`}>
        <Icon class={`w-5 h-5 ${style.iconShadow}`} />
        <h3 class={`font-semibold ${style.titleText}`}>
            {title}
        </h3>
    </div>
    <div class="space-y-1">
        {#each items as item}
            <a
                href={item.href}
                class="flex justify-between items-center gap-3 hover:bg-accent p-1 px-2 rounded text-sm transition-colors"
                title={item.label}
            >
                <span
                    class={`flex-1 flex items-center gap-2 ${style.itemLabel} min-w-0`}
                >
                    {#if item.icon}
                        <item.icon class="shrink-0 w-3.5 h-3.5" />
                    {/if}
                    {#if item.countryCode}
                        <iconify-icon
                            icon={`circle-flags:${item.countryCode.toLowerCase()}`}
                            class="shrink-0 text-base"
                        ></iconify-icon>
                    {/if}
                    <span class="truncate">{item.label}</span>
                </span>
                <span class={`shrink-0 font-medium ${style.itemCount}`}>
                    {item.count}
                    {item.count === 1 ? unit : pluralUnit}
                </span>
            </a>
        {/each}
    </div>
</div>
