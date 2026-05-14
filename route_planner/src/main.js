import { createApp } from "vue";
import {
	Button,
	Badge,
	Dialog,
	ErrorMessage,
	FormControl,
	FrappeUI,
	TextInput,
	Tooltip,
} from "frappe-ui";
import { createPinia } from "pinia";
import App from "./App.vue";
import "./index.css";

/**
 * Mount the Route Planner Vue app into a given DOM element.
 * Called by the Frappe Page loader (route_planner.js).
 */
function mount(el) {
	const app = createApp(App);
	const pinia = createPinia();

	app.use(FrappeUI);
	app.use(pinia);

	// Register global components
	const globals = { Button, Badge, Dialog, ErrorMessage, FormControl, TextInput, Tooltip };
	for (const name in globals) {
		app.component(name, globals[name]);
	}

	app.mount(el);
	return app;
}

// Auto-mount if running standalone in dev mode
if (import.meta.env.DEV) {
	const el = document.getElementById("app");
	if (el) mount(el);
}

// Expose mount function for the Frappe Page loader
window.RoutePlanner = { mount };
