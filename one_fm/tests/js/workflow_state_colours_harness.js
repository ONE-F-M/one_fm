// Loads the shipped script against a stub desk and reports the colours it gives.
const fs = require("fs");
const vm = require("vm");
const [, , scriptPath, payload] = process.argv;
const { styles, values, active_workflow } = JSON.parse(payload);

const frappe = {
	boot: { workflow_state_styles: styles },
	utils: { guess_colour: () => "gray" },
	get_indicator: () => ["status", "gray", "status,=,x"],
	workflow: { get_state_fieldname: () => (active_workflow ? "workflow_state" : null) },
};
vm.runInNewContext(fs.readFileSync(scriptPath, "utf8"), { frappe, __: (s) => s });

const out = { pills: {}, indicator: frappe.get_indicator({ doctype: "Probe", workflow_state: values[0] }, "Probe", true) };
for (const value of values) out.pills[value] = frappe.utils.guess_colour(value);
process.stdout.write(JSON.stringify(out));
