import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import Icons from "unplugin-icons/vite";

export default defineConfig({
  plugins: [
    sveltekit(),
    tailwindcss(),
    Icons({
      compiler: "svelte",
    }),
  ],
  ssr: { noExternal: ["postprocessing"] },
  optimizeDeps: {
    exclude: ["@libsql/client", "libsql", "@neon-rs/load", "detect-libc"],
  },
  build: {
    commonjsOptions: {
      ignore: [
        "path",
        "fs",
        "child_process",
        "os",
        "crypto",
        "stream",
        "util",
        "events",
        "http",
        "https",
        "net",
        "tls",
        "zlib",
        "url",
        "querystring",
        "punycode",
        "dgram",
        "dns",
        "cluster",
        "module",
        "vm",
        "async_hooks",
        "perf_hooks",
        "worker_threads",
        "child_process",
        "repl",
        "readline",
        "string_decoder",
        "timers",
        "trace_events",
        "tty",
        "v8",
        "wasi",
        "inspector",
      ],
    },
  },
  server: {
    proxy: {
      "/api": {
        target: `http://${process.env.VITE_BACKEND_URL || "0.0.0.0"}:8000`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
        bypass: (req) => {
          if (req.url?.startsWith("/api/auth")) {
            return req.url;
          }
        },
      },
      "/static": {
        target: `http://${process.env.VITE_BACKEND_URL || "0.0.0.0"}:8000`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/static/, ""),
      },
    },
  },
});
