// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Port of the BA Client Script "Testing new details fetech" (WI-004420).
// Note: "Day Off Category" points at a DocType that does not exist and
// "Number of Days Off" has no mapping. Shipped as on BA, pending a BA decision.
const NEW_VALUE_DOCTYPE_MAP = {
	"Designation": "Designation",
	"Department": "Department",
	"Reports to": "Employee",
	"Day Off Category": "Day Off Category",
	"Employment Type": "Employment Type",
};

frappe.ui.form.on("Employee Record Update Request Properties Item", {
	property: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const new_value_doctype = NEW_VALUE_DOCTYPE_MAP[row.property];
		if (new_value_doctype) {
			frappe.model.set_value(cdt, cdn, "new_value_doctype", new_value_doctype);
		}
		frappe.model.set_value(cdt, cdn, "new_value", "");
		frm.refresh_field("properties");
	},
});
