// Copyright (c) 2026, ONE FM and contributors
// For license information, please see license.txt

// Port of the BA Client Script "Testing new details fetech".
// "Day Off Category" points at a DocType that does not exist and "Number of Days Off"
// has no mapping. Shipped as on BA, pending a BA decision.
frappe.ui.form.on("Employee Record Update Request Properties Item", {
	property(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const doctype_map = {
			"Designation": "Designation",
			"Department": "Department",
			"Reports to": "Employee",
			"Day Off Category": "Day Off Category",
			"Employment Type": "Employment Type",
		};
		const target = doctype_map[row.property] || "";

		frappe.model.set_value(cdt, cdn, "new_value", "");
		frappe.model.set_value(cdt, cdn, "new_value_doctype", target).then(() => {
			frm.refresh_field("properties");
		});
	},
});
