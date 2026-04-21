import { Tooltip as TooltipPrimitive } from "bits-ui";
import Content from "./tooltip-content.svelte";
import Trigger from "./tooltip-trigger.svelte";

const Root = TooltipPrimitive.Root;
const Provider = TooltipPrimitive.Provider;
const Arrow = TooltipPrimitive.Arrow;

export {
	Root,
	Trigger,
	Content,
	Provider,
	Arrow,
	//
	Root as Tooltip,
	Trigger as TooltipTrigger,
	Content as TooltipContent,
	Provider as TooltipProvider,
	Arrow as TooltipArrow,
};
