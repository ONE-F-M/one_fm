const plugin = require("tailwindcss/plugin");

module.exports = {
	presets: [require("frappe-ui/src/utils/tailwind.config")],
	content: [
		"./index.html",
		"./src/**/*.{vue,js,ts,jsx,tsx}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts}",
	],
	darkMode: "class",
	theme: {
		extend: {},
	},
	plugins: [],
};
