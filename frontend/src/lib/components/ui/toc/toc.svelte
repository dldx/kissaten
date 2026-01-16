<script lang="ts" module>
	export type TocProps = {
		toc: Heading[];
		class?: string;
		/** Indicates whether this is a child component or root component */
		isChild?: boolean;
	};
</script>

<script lang="ts">
	import type { Heading } from "$lib/hooks/use-toc.svelte";
	import { cn } from "$lib/utils.js";
	import Self from "./toc.svelte";

	let { toc, isChild = false, class: className }: TocProps = $props();
</script>

{#if !isChild}
	<div class="nav-wrap">
		<div class="bubble active"></div>
		<div class="bubble hover"></div>
		<ul class={cn("m-0 list-none text-sm font-medium", className)}>
			{#each toc as heading, i (i)}
				<li class="mt-0 pt-1.5 transition-all">
					{#if heading.id}
						<a
							href="#{heading.id}"
							class={cn(
								"toc-link block px-4 py-2 transition-colors",
								{
									active: heading.active,
									"text-muted-foreground": !heading.active,
									"text-foreground": heading.active,
								},
							)}
						>
							{heading.label}
						</a>
					{:else}
						<span class="block px-4 py-2 text-muted-foreground"
							>{heading.label}</span
						>
					{/if}
					{#if heading.children.length > 0}
						<Self toc={heading.children} isChild={true} />
					{/if}
				</li>
			{/each}
		</ul>
	</div>
{:else}
	<ul class={cn("m-0 list-none text-sm font-medium pl-4")}>
		{#each toc as heading, i (i)}
			<li class="mt-0 pt-0.5 transition-all">
				{#if heading.id}
					<a
						href="#{heading.id}"
						class={cn(
							"toc-link block px-4 py-2 transition-colors",
							{
								active: heading.active,
								"text-muted-foreground": !heading.active,
								"text-foreground": heading.active,
							},
						)}
					>
						{heading.label}
					</a>
				{:else}
					<span class="block px-4 py-2 text-muted-foreground"
						>{heading.label}</span
					>
				{/if}
				{#if heading.children.length > 0}
					<Self toc={heading.children} isChild={true} />
				{/if}
			</li>
		{/each}
	</ul>
{/if}

<style>
	.nav-wrap {
		border: 1px solid var(--color-border);
		width: fit-content;
		border-radius: var(--radius);
		position: relative;
		background: var(--color-card);
		padding: 4px;
	}

	.toc-link {
		z-index: 10;
		position: relative;
		text-decoration: none;
		border-radius: var(--radius-sm);
		color: var(--color-muted-foreground);
		transition: color 0.2s ease;
	}

	.toc-link:hover {
		color: var(--color-foreground);
	}

	.toc-link::before {
		content: "";
		display: block;
		position: absolute;
		inset: 0;
		opacity: 0;
	}

	.toc-link:hover::before {
		anchor-name: --toc-hover;
	}

	.toc-link.active {
		anchor-name: --toc-active;
		color: var(--color-primary-foreground) !important;
	}

	.bubble {
		position: absolute;
		transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
		border-radius: var(--radius-sm);
		pointer-events: none;
		inset: anchor(top) anchor(right) anchor(bottom) anchor(left);
	}

	.bubble.active {
		position-anchor: --toc-active;
		z-index: 2;
		background: var(--color-primary);
	}

	.bubble.hover {
		z-index: 1;
		background: var(--color-accent);
		opacity: 0.1;
		position-anchor: --toc-hover;
		opacity: 0;
	}

	.nav-wrap:has(.toc-link:hover) .bubble.hover {
		opacity: 0.15;
	}
</style>
