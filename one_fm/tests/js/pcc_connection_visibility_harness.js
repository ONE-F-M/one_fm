// Runs the SHIPPED set_pcc_connection_visibility from preparation.js against a fake form.
// The function is read out of the file rather than copied here: which badge survives the
// filter, and whether the shared meta is left alone, are exactly the things a copy drifts
// away from.

const fs = require("fs");
const path = require("path");

const source = fs.readFileSync(
	path.join(__dirname, "..", "..", "grd", "doctype", "preparation", "preparation.js"),
	"utf8"
);

const start = source.indexOf("function set_pcc_connection_visibility(frm) {");
if (start === -1) {
	throw new Error("set_pcc_connection_visibility is not in preparation.js");
}
const set_pcc_connection_visibility = eval(`(${source.slice(start)})`);

const DASHBOARD = {
	transactions: [
		{ items: ["Work Permit"] },
		{ items: ["Medical Insurance"] },
		{ items: ["Residency"] },
		{ items: ["PACI"] },
		{ items: ["Fingerprint Appointment"] },
		{ items: ["Medical Appointment"] },
		{ items: ["PCC Attestation"] },
	],
};

function run(category) {
	const meta = { __dashboard: JSON.parse(JSON.stringify(DASHBOARD)) };
	const calls = [];
	const frm = {
		doc: { category: category },
		meta: meta,
		dashboard: {
			transactions_area: {
				empty: () => calls.push("empty"),
			},
			data_rendered: true,
			refresh: function () {
				calls.push("refresh");
			},
		},
	};

	set_pcc_connection_visibility(frm);

	const items = (frm.dashboard.data.transactions || []).reduce(
		(all, group) => all.concat(group.items),
		[]
	);
	return {
		items: items,
		calls: calls,
		data_rendered: frm.dashboard.data_rendered,
		// The shared meta must come back untouched, or the badge stays hidden on the next
		// Onboarding record opened in the same session.
		meta_items: meta.__dashboard.transactions.reduce(
			(all, group) => all.concat(group.items),
			[]
		),
	};
}

process.stdout.write(JSON.stringify(run(JSON.parse(process.argv[2]).category)));
