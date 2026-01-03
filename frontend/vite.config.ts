import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import Icons from 'unplugin-icons/vite'

export default defineConfig({
	plugins: [
		sveltekit(),
		tailwindcss(),
		Icons({
			compiler: 'svelte',
		})
	],
	ssr: { noExternal: ['postprocessing'] },
	server: {
		proxy: {
			'/api': {
				target: `http://${process.env.VITE_BACKEND_URL || '0.0.0.0'}:8000`,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, ''),
				bypass: (req) => {
					if (req.url?.startsWith('/api/auth')) {
						return req.url;
					}
				}
			},
			'/static': {
				target: `http://${process.env.VITE_BACKEND_URL || '0.0.0.0'}:8000`,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/static/, ''),
			},
		},
	},
});
