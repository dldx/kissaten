<script lang="ts">
	import { page } from "$app/state";
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import { Alert, AlertDescription } from "$lib/components/ui/alert/index.js";
	import * as InputOTP from "$lib/components/ui/input-otp/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import { Mail, Loader2 } from "lucide-svelte";
	import { REGEXP_ONLY_DIGITS } from "bits-ui";
	import Logo from "$lib/static/logo.svg?raw";
	import { authClient } from "$lib/auth-client";
	import { goto } from "$app/navigation";

	const email = page.url.searchParams.get("email") || "";
	let otp = $state("");
	let isLoading = $state(false);
	let errorMessage = $state("");

	async function handleVerify() {
		if (otp.length !== 6) {
			errorMessage = "Please enter a 6-digit code.";
			return;
		}

		isLoading = true;
		errorMessage = "";

		await authClient.signIn.emailOtp(
			{
				email,
				otp,
				callbackURL: "/vault",
			},
			{
				onSuccess: () => {
					goto("/vault");
				},
				onError: (ctx) => {
					errorMessage =
						ctx.error.message || "Invalid or expired code.";
					isLoading = false;
				},
			},
		);
	}
</script>

<div class="flex justify-center items-center px-4 py-8 min-h-[60vh]">
	<Card class="w-full max-w-md">
		<CardHeader class="space-y-4 text-center">
			<div class="flex justify-center">
				<div class="w-12 h-12">
					{@html Logo}
				</div>
			</div>
			<div class="flex justify-center text-primary">
				<Mail class="w-20 h-20" />
			</div>
			<CardTitle class="text-3xl font-bold">Check your email</CardTitle>
			<CardDescription class="text-base">
				We've sent a magic link and a verification code to <br />
				<strong class="text-foreground break-words"
					>{email || "your email"}</strong
				>
			</CardDescription>
		</CardHeader>
		<CardContent class="space-y-8">
			<div class="space-y-4 flex flex-col justify-center">
				<div class="space-y-2">
					<Label for="otp" class="justify-center font-bold"
						>Verification code</Label
					>
					<div class="flex justify-center">
						<InputOTP.Root
							maxlength={6}
							pattern={REGEXP_ONLY_DIGITS}
							bind:value={otp}
							disabled={isLoading}
						>
							{#snippet children({ cells })}
								<InputOTP.Group>
									{#each cells as cell (cell)}
										<InputOTP.Slot
											{cell}
											class="dark:bg-primary/20 bg-white/40"
										/>
									{/each}
								</InputOTP.Group>
							{/snippet}
						</InputOTP.Root>
					</div>
					{#if errorMessage}
						<p
							class="text-sm text-destructive font-medium text-center"
						>
							{errorMessage}
						</p>
					{/if}
				</div>

				<Button
					class="w-fit py-6 text-lg align-center self-center justify-center"
					onclick={handleVerify}
					disabled={isLoading || otp.length !== 6}
				>
					{#if isLoading}
						<Loader2 class="mr-2 w-5 h-5 animate-spin" />
						Verifying...
					{:else}
						Sign In
					{/if}
				</Button>
			</div>

			<div class="relative">
				<div class="absolute inset-0 flex items-center">
					<span class="w-full border-t"></span>
				</div>
				<div class="relative flex justify-center text-xs uppercase">
					<span class="bg-card px-2 text-muted-foreground">Or</span>
				</div>
			</div>

			<p class="text-muted-foreground text-center text-sm">
				Click the link in the email to sign in automatically.<br />
				The link and code will expire in 5 minutes.
			</p>

			<Alert>
				<AlertDescription>
					<p class="mb-2 font-medium">Didn't receive the email?</p>
					<ul class="space-y-1 text-sm">
						<li>• Check your spam or junk folder</li>
						<li>
							• Make sure you entered the correct email address
						</li>
						<li>• Wait a few minutes and check again</li>
					</ul>
				</AlertDescription>
			</Alert>

			<Button variant="ghost" class="w-full" href="/login">
				Back to login
			</Button>
		</CardContent>
	</Card>
</div>
