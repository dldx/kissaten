<script lang="ts">
	import { loginOrSignup } from '$lib/api/auth.remote'
	import { page } from '$app/state';
	import LoginForm from '$lib/components/login-form.svelte';

	const error = $derived(page.url.searchParams.get('error'));

	const errorMessages: Record<string, string> = {
		verification_failed: 'Magic link verification failed. Please try again.',
		expired: 'The magic link has expired. Please request a new one.',
		invalid: 'Invalid magic link. Please request a new one.'
	};

	const errorMessage = $derived(error ? errorMessages[error] || 'An error occurred. Please try again.' : null);
</script>

<div class="flex flex-col justify-center items-center gap-6 bg-background p-6 md:p-10 min-h-svh">
	<div class="w-full max-w-sm">
		<LoginForm form={loginOrSignup} {errorMessage} />
	</div>
</div>