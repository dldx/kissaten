// import adapter from '@sveltejs/adapter-auto';
import adapter from "svelte-adapter-bun";
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://kit.svelte.dev/docs/integrations#preprocessors
	// for more information about preprocessors
	preprocess: vitePreprocess(),
	compilerOptions: {
		experimental: {
			async: true
		}
	},

	kit: {
		// adapter-auto only supports some environments, see https://svelte.dev/docs/kit/adapter-auto for a list.
		// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
		// See https://svelte.dev/docs/kit/adapters for more information about adapters.
		adapter: adapter(),
		// Keep secondary processes (vitest, checks, verification servers) out of
		// the running dev server's generated files: `.svelte-kit` is rewritten by
		// every SvelteKit process that starts, and a rewrite while `bun run dev`
		// is running desyncs its in-memory node manifest from the client node
		// files (wrong-component hydration on random pages).
		outDir: process.env.SVELTEKIT_OUT_DIR ?? '.svelte-kit',
		experimental: {
			remoteFunctions: true,

			tracing: {
				server: true,
			},

			instrumentation: {
				server: true,
			},
		},
	},
	trustedOrigins: ["http://192.168.1.163:3000"],
	vitePlugin: {
		inspector: true,
	},
};

export default config;