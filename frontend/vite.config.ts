import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [sveltekit(), tailwindcss()],
	server: {
		proxy: {
			'/api': {
                                target: `http://${process.env.VITE_BACKEND_URL || '0.0.0.0'}:8000`,
                                changeOrigin: true,
                                rewrite: (path) => path.replace(/^\/api/, '')
                        },
			'/static': {
				target: `http://${process.env.VITE_BACKEND_URL || '0.0.0.0'}:8000`,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/static/, ''),
			},
		},
	},
});
