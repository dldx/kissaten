<script lang="ts">
	import type { HTMLAttributes } from "svelte/elements";
	import {
		FieldGroup,
		Field,
		FieldLabel,
		FieldDescription,
	} from "$lib/components/ui/field/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import { cn } from "$lib/utils";
	import Logo from "$lib/static/logo-alt.svg?raw";
	import { Vault } from "lucide-svelte";

	interface Props extends HTMLAttributes<HTMLDivElement> {
		form: any;
		errorMessage?: string | null;
	}

	let {
		class: className,
		form,
		errorMessage = null,
		...restProps
	}: Props = $props();

	const id = $props.id();

	import { authClient } from "$lib/auth-client";
	const session = authClient.useSession();
	console.log($session);
</script>

<div class={cn("flex flex-col gap-6", className)} {...restProps}>
	{#if $session.data}
		<div class="flex flex-col items-center gap-6 text-center">
			<div class="flex flex-col items-center gap-2">
				<div class="flex justify-center items-center rounded-md w-12 h-12">
					{@html Logo}
				</div>
				<h1 class="font-bold text-xl">Welcome back!</h1>
				<p class="text-muted-foreground">Hello
					{#if ($session.data.user.name === null) || ($session.data.user.name === '')}
						there
					{:else}
					, {$session.data.user.name}
					{/if}.
				</p>
			</div>

			<div class="flex flex-col gap-3 w-full">
				<Button href="/vault" size="lg" class="w-full">
					<Vault class="mr-2 w-5 h-5" />
					Go to your coffee vault
				</Button>
				<Button
					variant="outline"
					onclick={async () => {
						await authClient.signOut();
					}}
				>
					Sign Out
				</Button>
			</div>
		</div>
	{:else}
	<form {...form}>
		<FieldGroup>
			<div class="flex flex-col items-center gap-2 text-center">
				<a href="/" class="flex flex-col items-center gap-2 font-medium">
					<div class="flex justify-center items-center rounded-md w-12 h-12">
						{@html Logo}
					</div>
					<span class="sr-only">Kissaten</span>
				</a>
				<h1 class="font-bold text-xl">Welcome to Kissaten</h1>
				<FieldDescription>
					Don't have an account? Just enter your email to get started.
				</FieldDescription>
			</div>

			{#if errorMessage}
				<div class="bg-red-50 px-4 py-3 border border-red-200 rounded-md text-red-800">
					{errorMessage}
				</div>
			{/if}

			<Field>
				<FieldLabel for="email-{id}">Email</FieldLabel>
				<Input
					id="email-{id}"
					{...form.fields.email.as('email')}
					type="email"
					placeholder="ilovecoffee@example.com"
					required
				/>
				{#each form.fields.email.issues() ?? [] as issue}
					<p class="mt-1 text-red-600 text-sm">{issue.message}</p>
				{/each}
			</Field>

			<Field>
				<Button type="submit" class="w-full">Login/Signup</Button>
			</Field>
		</FieldGroup>
	</form>
	{/if}
</div>
