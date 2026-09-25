// Runs the SHIPPED set_pcc_connection_visibility from preparation.js against a fake
// dashboard. The function is read out of the file rather than copied here: which badge it
// touches, and whether it touches anything else, are exactly what a copy drifts away from.
//
// The stub is deliberately hostile in one specific way: `frm` is circular, exactly as it is
// on a real form. render_links() does `this.data.frm = this.frm` and dashboard.data IS
// frm.meta.__dashboard, so anything that tries to deep-copy the dashboard data throws
// "Converting circular structure to JSON" - which is how the first version of this function
// died, taking the rest of the refresh handler with it.

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

const args = JSON.parse(process.argv[2]);

// Minimal jQuery stand-in: records what was selected and how it was toggled.
const calls = [];
const transactions_area = {
	find(selector) {
		return {
			toggleClass(className, state) {
				calls.push({ selector, className, state });
				return this;
			},
			addClass(className) {
				calls.push({ selector, className, state: true });
				return this;
			},
			removeClass(className) {
				calls.push({ selector, className, state: false });
				return this;
			},
		};
	},
};

const frm = {
	doc: { category: args.category },
	dashboard: { transactions_area },
};
// The cycle a real form has, on the object the dashboard data hangs off.
frm.meta = { __dashboard: { transactions: [{ items: ["PCC Attestation"] }] } };
frm.meta.__dashboard.frm = frm;
frm.dashboard.data = frm.meta.__dashboard;

let threw = null;
try {
	set_pcc_connection_visibility(frm);
} catch (error) {
	threw = String(error && error.message);
}

process.stdout.write(JSON.stringify({ calls, threw }));
