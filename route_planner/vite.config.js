import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [
		frappeui({
			lucideIcons: true,
		}),
		vue(),
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	define: {
		"process.env.NODE_ENV": JSON.stringify("production"),
	},
	build: {
		outDir: "../one_fm/public/dist/route_planner",
		emptyOutDir: true,
		lib: {
			entry: path.resolve(__dirname, "src/main.js"),
			formats: ["iife"],
			name: "RoutePlanner",
			fileName: () => "index.js",
		},
		rollupOptions: {
			output: {
				assetFileNames: "[name].[ext]",
			},
		},
	},
});
