// Runs the SHIPPED camp filter, counters and slot/direction labels from
// transportation_manifest_page.js on a fixture passed as argv[2].

const fs = require("fs");
const path = require("path");

const source = fs.readFileSync(
	path.join(__dirname, "..", "..", "one_fm", "page", "transportation_manifest_page",
		"transportation_manifest_page.js"),
	"utf8"
);

function extract(name) {
	const start = source.indexOf(`function ${name}(`);
	if (start === -1) throw new Error(`${name} is not in transportation_manifest_page.js`);
	const rest = source.slice(start);
	return rest.slice(0, rest.indexOf("\n\t}\n") + "\n\t}\n".length);
}

const args = JSON.parse(process.argv[2]);
const __ = (text, values) => (values || []).reduce((t, v, i) => t.replace(`{${i}}`, v), text);
const window = { checkerState: args.checkerState || {} };
const MFST_STATE = { accommodation: args.accommodation || "", accommodations: [] };
const shipmentEmployees = args.shipmentEmployees || {};
const shipmentOwnDirections = args.shipmentOwnDirections || {};
const parsed = args.parsed || [];
let counters = "";
const $container = { find: () => ({ html: (h) => { counters = h; } }) };

["buildTrips", "tripHasCamp", "campTrips", "renderCounters", "tripDirection", "slotVehicleLine"]
	.forEach((name) => eval(extract(name).replace(`function ${name}(`, `globalThis.${name} = function (`)));

renderCounters();
const values = [...counters.matchAll(/mfst-counter-val">(\d+)</g)].map((m) => Number(m[1]));
process.stdout.write(JSON.stringify({
	vehicles: parsed.map((pr) => ({ label: pr.label, trips: campTrips(pr).map((t) => t.label) })),
	counters: { trips: values[0], boarding: values[1], checked: values[2], failed: values[3] },
	directions: parsed.flatMap((pr) => buildTrips(pr).map((t) => tripDirection(t).text)),
	slotLines: (args.slots || []).map(slotVehicleLine),
}));
