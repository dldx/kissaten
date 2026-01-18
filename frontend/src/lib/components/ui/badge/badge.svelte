<script lang="ts">
    import { cn } from "$lib/utils.js";
    import { badgeVariants, type Variant } from "./index.js";

    let {
        class: className,
        variant = "default",
        children,
        ...restProps
    } = $props();
</script>

<div class={cn(badgeVariants({ variant }), className)} {...restProps}>
    {@render children?.()}
</div>
