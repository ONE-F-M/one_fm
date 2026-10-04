// Loads the SHIPPED hr_settings.js and runs its real GRD Renewal Extension Cost
// handlers, so this tests the file that is served rather than a copy of its logic.
const fs = require("fs");
const [, , scriptPath, payload] = process.argv;
const args = JSON.parse(payload);

const handlers = {};
global.locals = {};
global.frappe = {
	ui: { form: { on: (doctype, h) => { handlers[doctype] = h; } } },
	model: {
		// Frappe fires the field's own handler after a set_value, and the total depends on
		// that happening - so the stub does it too, or the harness would pass while the
		// shipped chain was broken.
		set_value: (cdt, cdn, field, value) => {
			global.locals[cdt][cdn][field] = value;
			const h = handlers[cdt] && handlers[cdt][field];
			if (h) h({ refresh_field: () => {} }, cdt, cdn);
		},
	},
};

new Function(fs.readFileSync(scriptPath, "utf8"))();

const DT = "GRD Renewal Extension Cost";
const row = Object.assign({ doctype: DT, name: "row1" }, args.row);
global.locals[DT] = { row1: row };

handlers[DT][args.event]({ refresh_field: () => {} }, DT, "row1");
process.stdout.write(JSON.stringify(row));
