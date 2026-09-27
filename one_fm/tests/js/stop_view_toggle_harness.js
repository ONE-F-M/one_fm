// Evaluates the SHIPPED v-if on the Compact/Detailed toggle for a given stop count,
// so any correct formulation passes and a regression to "> 1" fails.
const fs = require("fs");
const [, , canvasPath, payload] = process.argv;
const { stopCount } = JSON.parse(payload);

const src = fs.readFileSync(canvasPath, "utf8");
const match = src.match(/<div class="rp-view-toggle" v-if="([^"]+)">/);
if (!match) {
	process.stdout.write(JSON.stringify({ error: "toggle v-if not found" }));
	process.exit(0);
}

const selectedTripStops = new Array(stopCount).fill({});
const shown = new Function("selectedTripStops", `return (${match[1]});`)(selectedTripStops);
process.stdout.write(JSON.stringify({ expression: match[1], shown: !!shown }));
