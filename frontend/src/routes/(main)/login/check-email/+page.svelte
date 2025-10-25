<script lang="ts">
	import { page } from '$app/stores';

	const email = $page.url.searchParams.get('email') || 'your email';
</script>

<div class="check-email-container">
	<div class="check-email-card">
		<div class="icon">
			<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<rect width="20" height="16" x="2" y="4" rx="2"/>
				<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
			</svg>
		</div>

		<h1>Check your email</h1>

		<p class="message">
			We've sent a magic link to <strong>{email}</strong>
		</p>

		<p class="instructions">
			Click the link in the email to sign in to your account. The link will expire in 5 minutes.
		</p>

		<div class="tips">
			<h3>Didn't receive the email?</h3>
			<ul>
				<li>Check your spam or junk folder</li>
				<li>Make sure you entered the correct email address</li>
				<li>Wait a few minutes and check again</li>
			</ul>
		</div>

		<a href="/login" class="back-link">Back to login</a>
	</div>
</div>

<style>
	.check-email-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 60vh;
		padding: 2rem;
	}

	.check-email-card {
		max-width: 500px;
		width: 100%;
		text-align: center;
		background: var(--color-surface, white);
		border-radius: 8px;
		padding: 3rem 2rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.icon {
		color: var(--color-primary, #4CAF50);
		margin-bottom: 1.5rem;
	}

	h1 {
		font-size: 2rem;
		margin-bottom: 1rem;
		color: var(--color-text, #333);
	}

	.message {
		font-size: 1.1rem;
		margin-bottom: 1rem;
		color: var(--color-text-secondary, #666);
	}

	.message strong {
		color: var(--color-text, #333);
		word-break: break-word;
	}

	.instructions {
		color: var(--color-text-secondary, #666);
		margin-bottom: 2rem;
		line-height: 1.6;
	}

	.tips {
		background: var(--color-surface-variant, #f5f5f5);
		border-radius: 8px;
		padding: 1.5rem;
		margin-bottom: 2rem;
		text-align: left;
	}

	.tips h3 {
		font-size: 1rem;
		margin-bottom: 0.75rem;
		color: var(--color-text, #333);
	}

	.tips ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.tips li {
		padding: 0.25rem 0;
		color: var(--color-text-secondary, #666);
		font-size: 0.95rem;
	}

	.tips li::before {
		content: "•";
		margin-right: 0.5rem;
		color: var(--color-primary, #4CAF50);
	}

	.back-link {
		display: inline-block;
		color: var(--color-primary, #4CAF50);
		text-decoration: none;
		font-weight: 500;
		transition: opacity 0.2s;
	}

	.back-link:hover {
		opacity: 0.8;
		text-decoration: underline;
	}
</style>
