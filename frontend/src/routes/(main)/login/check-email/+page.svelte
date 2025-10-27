<script lang="ts">
	import { page } from '$app/stores';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import { Alert, AlertDescription } from "$lib/components/ui/alert/index.js";
	import { Mail } from "lucide-svelte";
	import Logo from "$lib/static/logo-alt.svg?raw";

	const email = $page.url.searchParams.get('email') || 'your email';
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
				<Mail class="w-16 h-16" />
			</div>
			<CardTitle class="text-2xl">Check your email</CardTitle>
			<CardDescription class="text-base">
				We've sent a magic link to <strong class="text-foreground break-words">{email}</strong>
			</CardDescription>
		</CardHeader>
		<CardContent class="space-y-6">
			<p class="text-muted-foreground text-center">
				Click the link in the email to sign in to your account. The link will expire in 5 minutes.
			</p>

			<Alert>
				<AlertDescription>
					<p class="mb-2 font-medium">Didn't receive the email?</p>
					<ul class="space-y-1 text-sm">
						<li>• Check your spam or junk folder</li>
						<li>• Make sure you entered the correct email address</li>
						<li>• Wait a few minutes and check again</li>
					</ul>
				</AlertDescription>
			</Alert>

			<Button variant="outline" class="w-full" href="/login">
				Back to login
			</Button>
		</CardContent>
	</Card>
</div>
