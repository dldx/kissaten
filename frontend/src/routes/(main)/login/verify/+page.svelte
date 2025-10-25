<div class="verify-container">
	<div class="verify-card">
		<div class="spinner"></div>
		<h1>Verifying your magic link...</h1>
		<p>Please wait while we sign you in.</p>
	</div>
</div>

<style>
	.verify-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 60vh;
		padding: 2rem;
	}

	.verify-card {
		max-width: 400px;
		width: 100%;
		text-align: center;
		background: var(--color-surface, white);
		border-radius: 8px;
		padding: 3rem 2rem;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.spinner {
		width: 48px;
		height: 48px;
		border: 4px solid var(--color-surface-variant, #f0f0f0);
		border-top-color: var(--color-primary, #4CAF50);
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin: 0 auto 1.5rem;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	h1 {
		font-size: 1.5rem;
		margin-bottom: 0.5rem;
		color: var(--color-text, #333);
	}

	p {
		color: var(--color-text-secondary, #666);
	}
</style>
