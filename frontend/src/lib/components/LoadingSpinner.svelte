<script lang="ts">
	import CoffeeBean from "virtual:icons/streamline-plump/coffee-bean-solid";

	type Props = {
		size?: string;
		duration?: string;
		pause?: boolean;
	};

	let { size = '24', duration = '1s', pause = false }: Props = $props();

	const beans = [0, 1, 2];
	const durationUnitRegex = /[a-zA-Z]+/;
	const durationUnit = duration.match(durationUnitRegex)?.[0] ?? 's';
	const durationNum = parseFloat(duration.replace(durationUnitRegex, ''));
</script>

<div class="wrapper" style="--size: {size}px; --duration: {duration};">
	{#each beans as index}
		<div
			class="bean-container"
			class:pause-animation={pause}
			style="left: {index * (parseInt(size) * 1.2)}px; animation-delay: {index * (durationNum / 3)}{durationUnit};"
		>
			<CoffeeBean class="bean-icon" />
		</div>
	{/each}
</div>

<style>
	.wrapper {
		position: relative;
		display: flex;
		justify-content: center;
		align-items: center;
		width: calc(var(--size) * 3.6);
		height: calc(var(--size) * 2.5);
		overflow: visible;
	}

	.bean-container {
		position: absolute;
		width: var(--size);
		height: var(--size);
		display: flex;
		align-items: flex-end;
		animation: juggle var(--duration) ease-in-out infinite;
	}

	.bean-icon {
		width: 100%;
		height: 100%;
		color: rgb(217 119 6);
	}

	:global(.dark) .bean-icon {
		color: rgb(251 191 36);
	}

	.pause-animation {
		animation-play-state: paused;
	}

	@keyframes juggle {
		0%, 100% {
			transform: translateY(0) rotate(0deg);
		}
		25% {
			transform: translateY(-10%) rotate(45deg);
		}
		50% {
			transform: translateY(-100%) rotate(180deg);
		}
		75% {
			transform: translateY(-10%) rotate(315deg);
		}
	}
</style>
