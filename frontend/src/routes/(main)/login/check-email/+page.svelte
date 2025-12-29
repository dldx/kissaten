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
	import { Input } from "$lib/components/ui/input/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import { Mail, Loader2, KeyRound } from "lucide-svelte";
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

	function handleInput(e: any) {
		const value = e.target.value.replace(/[^0-9]/g, "");
		otp = value.slice(0, 6);
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
			<div class="space-y-4">
				<div class="space-y-2">
					<Label for="otp" class="text-sm font-medium"
						>Verification Code</Label
					>
					<div class="relative">
						<KeyRound
							class="top-3 left-3 absolute w-5 h-5 text-muted-foreground"
						/>
						<Input
							id="otp"
							type="text"
							placeholder="Enter 6-digit code"
							class="py-6 pl-10 text-center text-2xl font-bold tracking-[0.5em]"
							maxlength={6}
							bind:value={otp}
							oninput={handleInput}
							disabled={isLoading}
						/>
					</div>
					{#if errorMessage}
						<p class="text-sm text-destructive font-medium">
							{errorMessage}
						</p>
					{/if}
				</div>

				<Button
					class="w-full py-6 text-lg"
					onclick={handleVerify}
					disabled={isLoading || otp.length !== 6}
				>
					{#if isLoading}
						<Loader2 class="mr-2 w-5 h-5 animate-spin" />
						Verifying...
					{:else}
						Verify & Sign In
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
